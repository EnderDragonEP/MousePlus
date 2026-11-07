"""Global low-level mouse hook (WH_MOUSE_LL) running on its own thread, shared by every feature."""
import ctypes
import logging
import queue
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass, field, replace
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from . import bounce, winapi as w
from .cursor import Rect, map_crossing, monitor_at
from .horizontal import Engine, Settings
from .router import HORIZONTAL, SMOOTH, WheelEvent, route_wheel
from .smooth import FRAME, SmoothScroller, SmoothSettings

log = logging.getLogger("mouseplus")

_WM_APPLY = w.WM_APP + 1   # thread message: pick up new settings or monitors
_WATCHDOG_MS = 30_000      # periodic hook re-install
_FULLSCREEN_TTL = 0.25     # seconds to cache the full-screen check
_MASK_INTERVAL = 0.5       # seconds between mask-key taps while a bypass key is held
_NOWHERE = Rect(0, 0, 0, 0)
_EDGE_EVERY = 4            # frames between overscroll edge checks while a motion runs
_EDGE_MIN = 30             # units of motion left that still make a bounce
_BUTTON_DOWNS = {0x0201, 0x0204, 0x0207}  # left, right, middle: a click stops inertia
_TASKBAR = "<taskbar>"     # the "program" of taskbar windows in the program cache


def _program_of(hwnd) -> str:
    """The program file of a window, or _TASKBAR for the taskbar: Scroll Inertia stays out of it like
    an app on the list, since nothing there scrolls and a glide over the volume icon would keep changing the volume."""
    if not hwnd:
        return ""
    root = w.GetAncestor(hwnd, w.GA_ROOT)
    if root and w.window_class(root) in w.TASKBAR_CLASSES:
        return _TASKBAR
    return w.program_name(hwnd)


@dataclass(frozen=True)
class HookSettings:
    horizontal: Settings = field(default_factory=Settings)
    cursor: bool = False                     # Monitor Cursor: proportional moves between monitors
    smooth: Optional[SmoothSettings] = None  # Scroll Inertia; None when off
    smooth_sideways: bool = False            # Back/Forward + wheel gets inertia too
    bypass: frozenset = frozenset({"alt"})   # keys that make the wheel pass through untouched
    excluded: frozenset = frozenset()        # programs Scroll Inertia stays out of ("xnviewmp.exe")
    skip_fullscreen: bool = True             # every feature stays out of full-screen apps


class MouseHook(QObject):
    """Routes mouse events to the features and performs what they decide.

    Two threads:
    - the hook thread runs a plain Win32 message loop and answers hook calls;
      the features' decision state is only touched there, settings are posted to it.
    - the output thread calls SendInput and plays out Scroll Inertia's notches and glides.
      SendInput waits until every low-level hook (ours included) has seen the injected event,
      so calling it on the hook thread would stall input until Windows times us out.
      It sleeps on an event when idle and wakes on a high-resolution timer while scrolling.
    """

    latchedChanged = pyqtSignal(bool)
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = HookSettings()
        self._pending_monitors = ()
        self._engine = Engine(self._cached_fullscreen, self.latchedChanged.emit)
        self._proc = w.HOOKPROC(self._callback)  # must stay referenced while hooked
        self._actions = queue.SimpleQueue()
        self._wake = w.CreateEventW(None, False, False, None)  # tells the output thread to look at the queue
        self._hhook = None
        self._thread = None
        self._output = None
        self._tid = 0
        self._error = 0
        self._fs_value = False
        self._fs_time = 0.0
        # Monitor Cursor state, hook thread only
        self._monitors = ()
        self._current = _NOWHERE      # monitor the cursor is on: moves inside it return at once
        self._current_index = None
        self._cursor_active = False   # feature on and more than one monitor
        self._pos = wintypes.POINT()  # reused for GetCursorPos on every move
        self._pos_ref = ctypes.byref(self._pos)
        # Scroll Inertia state
        self._smoothing = False       # set by the output thread while Scroll Inertia is in motion
        self._elevation = {}          # root window -> elevated, hook thread only
        self._programs = {}           # window -> program file name, hook thread only
        self._mask_time = 0.0
        self._scroller = SmoothScroller()  # output thread only
        self._gesture = None          # (root window, modifiers) the motion started with
        self._hscroller = SmoothScroller()  # the same for sideways scrolling (Back/Forward + wheel)
        self._hgesture = None
        self._bounce = None           # the overscroll bounce playing, output thread only
        self._bounce_at = None        # where the bounce last put the window
        self._bounce_trail = set()    # every spot the bounce asked for; moves land asynchronously
        self._frames = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, settings: HookSettings) -> bool:
        if self.running:
            self.update(settings)
            return True
        self._settings = settings
        self._output = threading.Thread(target=self._output_loop, name="MouseOutput", daemon=True)
        self._output.start()
        ready = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(ready,), name="MouseHook", daemon=True)
        self._thread.start()
        ready.wait(2)
        if not self._hhook:
            self.stop()
            self.failed.emit(f"Could not install the mouse hook (error {self._error}).")
            return False
        return True

    def update(self, settings: HookSettings):
        self._settings = settings
        self._post_apply()

    def set_monitors(self, monitors):
        self._pending_monitors = tuple(monitors)
        self._post_apply()

    def stop(self):
        if self.running:
            w.PostThreadMessageW(self._tid, w.WM_QUIT, 0, 0)
            self._thread.join(2)
        self._thread = None
        if self._output is not None:
            self._send(None)
            self._output.join(2)
            self._output = None

    def _post_apply(self):
        if self.running:
            w.PostThreadMessageW(self._tid, _WM_APPLY, 0, 0)

    def _send(self, action):
        """Hand an action to the output thread."""
        self._actions.put(action)
        w.SetEvent(self._wake)

    # -- output thread ---------------------------------------------------

    def _output_loop(self):
        timer = w.CreateWaitableTimerExW(None, None, w.CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, w.TIMER_ALL_ACCESS)
        handles = (wintypes.HANDLE * 2)(self._wake, timer)
        due = ctypes.c_longlong(-round(FRAME * 10_000_000))  # relative, in 100 ns units
        scrollers = (self._scroller, self._hscroller)
        for scroller in scrollers:
            scroller.stop()
        try:
            while True:
                w.WaitForMultipleObjects(2, handles, False, w.INFINITE)
                while True:
                    try:
                        action = self._actions.get_nowait()
                    except queue.Empty:
                        break
                    if action is None:
                        return
                    try:
                        self._perform(action)
                    except Exception:
                        log.exception("Output action failed")
                moving = any(scroller.active for scroller in scrollers)
                if moving:
                    self._frame()
                if self._bounce:
                    self._bounce_frame()
                self._smoothing = moving = any(scroller.active for scroller in scrollers)
                if moving or self._bounce:
                    w.SetWaitableTimer(timer, ctypes.byref(due), 0, None, None, False)
        finally:
            for scroller in scrollers:
                scroller.stop()
            self._smoothing = False
            if self._bounce:  # never leave a window offset
                w.move_window(self._bounce.window, self._bounce.x, self._bounce.y)
                self._bounce = None
            w.CloseHandle(timer)

    def _perform(self, action):
        kind = action[0]
        if kind == "hwheel":  # a sideways step as it is: any smooth motion gives way
            self._scroller.stop()
            self._hscroller.stop()
            w.send_hwheel(action[1])
        elif kind == "click":
            w.send_xclick(action[1])
        elif kind == "mask":
            w.send_mask_key()
        elif kind == "smooth":
            self._hscroller.stop()  # scrolling the other way round is a new motion
            self._gesture = self._add(self._scroller, self._gesture, action)
            if self._scroller.settings.bounce:
                self._check_edge()
        elif kind == "hsmooth":
            self._scroller.stop()
            self._hgesture = self._add(self._hscroller, self._hgesture, action)
        elif kind == "stop":
            self._scroller.stop()
            self._hscroller.stop()
        elif kind == "settings":
            self._scroller.settings = action[1]
            self._hscroller.settings = replace(action[1], bounce=False)  # the bounce is vertical only

    def _add(self, scroller: SmoothScroller, gesture, action):
        """Give one direction's scroller a notch; returns that direction's new gesture."""
        _, delta, now, root, modifiers = action
        carry = scroller.settings.carry
        if scroller.active and gesture != (root, modifiers) and not (carry and gesture[1] == modifiers):
            scroller.stop()  # other keys, or another window the glide may not carry into: a new motion
        scroller.add(delta, now)
        return root, modifiers

    def _frame(self):
        scroller = self._scroller
        if scroller.active:
            self._gesture = self._frame_axis(scroller, self._gesture, w.send_wheel)
            self._frames += 1
            if (scroller.settings.bounce and scroller.active and self._frames % _EDGE_EVERY == 0
                    and (scroller.gliding or abs(scroller.remaining) >= _EDGE_MIN)):
                self._check_edge()
        if self._hscroller.active:
            self._hgesture = self._frame_axis(self._hscroller, self._hgesture, w.send_hwheel)

    def _frame_axis(self, scroller: SmoothScroller, gesture, send):
        """One frame of one direction's motion; returns its gesture (the window it now scrolls)."""
        root, modifiers = gesture
        x, y = w.cursor_pos()
        here = w.root_window_at(x, y)
        # Injected wheel events go to the window under the cursor and carry the keys held now:
        # stop rather than zoom once Ctrl is down, or scroll another window the glide may not carry into.
        if w.held_modifiers() != modifiers or (here != root and not self._carry_to(here, x, y)):
            scroller.stop()
            return gesture
        step = scroller.frame(time.perf_counter())
        if step:
            send(step)
        return here, modifiers

    def _carry_to(self, root, x: int, y: int) -> bool:
        """With "carry the glide to other apps" on, may the glide go on in the window the cursor just
        moved to? Not into apps on the list, the taskbar, full-screen apps or admin windows."""
        settings = self._settings
        return bool(root) and self._scroller.settings.carry and not (
            w.window_class(root) in w.TASKBAR_CLASSES
            or w.program_name(w.window_at(x, y)) in settings.excluded
            or (settings.skip_fullscreen and w.is_fullscreen(root))
            or w.window_is_elevated(root))

    def _check_edge(self):
        """Overscroll bounce: if the page under the cursor can't scroll further in the
        motion's direction, stop the motion and spring the window instead."""
        direction = self._scroller.direction
        target = w.classic_scrollbar_at(*w.cursor_pos())
        if not direction or target is None or not bounce.at_edge(direction, *target[1:]):
            return
        self._scroller.stop()
        if self._bounce:
            return  # already bouncing
        root = w.GetAncestor(target[0], w.GA_ROOT)
        place = w.bounceable(root)
        if place:
            x, y, scale = place
            self._bounce = bounce.Bounce(root, x, y, direction, bounce.AMPLITUDE * scale, time.perf_counter())
            self._bounce_at = (x, y)
            self._bounce_trail = {(x, y)}

    def _bounce_frame(self):
        b = self._bounce
        # A move is only queued to the window's own thread, so it may still be at an earlier spot
        # we asked for. Anywhere else means someone else moved it: leave it there.
        if w.window_position(b.window) not in self._bounce_trail:
            self._bounce = None
            return
        position = b.position(time.perf_counter())
        if position is None:
            w.move_window(b.window, b.x, b.y)  # exactly where it was
            self._bounce = None
            return
        if position != self._bounce_at:
            w.move_window(b.window, *position)
            self._bounce_at = position
            self._bounce_trail.add(position)

    # -- hook thread -----------------------------------------------------

    def _run(self, ready: threading.Event):
        self._tid = w.GetCurrentThreadId()
        msg = wintypes.MSG()
        w.PeekMessageW(ctypes.byref(msg), None, 0, 0, w.PM_NOREMOVE)  # create the message queue
        self._apply()
        self._hhook = self._install()
        ready.set()
        if not self._hhook:
            return
        timer = w.SetTimer(None, 0, _WATCHDOG_MS, None)
        try:
            while w.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == _WM_APPLY:
                    self._apply()
                elif msg.message == w.WM_TIMER and not self._engine.held:
                    # Windows can silently remove a low-level hook that answered
                    # too slowly, without telling us; re-installing keeps it alive.
                    hook = self._install()
                    if hook:
                        w.UnhookWindowsHookEx(self._hhook)
                        self._hhook = hook
        finally:
            w.KillTimer(None, timer)
            w.UnhookWindowsHookEx(self._hhook)
            self._hhook = None
            self._engine.reset()

    def _apply(self):
        settings = self._settings
        self._engine.apply(settings.horizontal)
        self._monitors = self._pending_monitors
        self._cursor_active = settings.cursor and len(self._monitors) > 1
        self._current, self._current_index = _NOWHERE, None
        self._send(("settings", settings.smooth) if settings.smooth else ("stop",))

    def _install(self):
        hook = w.SetWindowsHookExW(w.WH_MOUSE_LL, self._proc, w.GetModuleHandleW(None), 0)
        if not hook:
            self._error = ctypes.get_last_error()
            log.error("SetWindowsHookExW failed: %s", self._error)
        return hook

    def _callback(self, code, wparam, lparam):
        if code == w.HC_ACTION:
            try:
                if wparam == w.WM_MOUSEMOVE:
                    if self._cursor_active and self._move(lparam):
                        return 1
                elif self._handle(wparam, lparam):
                    return 1
            except Exception:
                log.exception("Mouse hook callback failed")
        return w.CallNextHookEx(None, code, wparam, lparam)

    def _move(self, lparam) -> bool:
        """Return True to swallow the move. Moves within a monitor cost two bounds checks."""
        # Where the cursor is before this move. Asked every time, because other apps can
        # move the cursor with SetCursorPos, which never reaches the hook.
        w.GetCursorPos(self._pos_ref)
        current = self._current
        if not (current.left <= self._pos.x < current.right and current.top <= self._pos.y < current.bottom):
            if not self._locate(self._pos.x, self._pos.y):
                return False
            current = self._current
        info = w.MSLLHOOKSTRUCT.from_address(lparam)
        x, y = info.pt.x, info.pt.y
        if current.left <= x < current.right and current.top <= y < current.bottom:
            return False
        # Pen and touch, and software that moves the cursor (remote-control tools, AutoHotkey), put it
        # exactly where they mean to: only the mouse's own relative moves cross proportionally.
        if info.flags & w.LLMHF_INJECTED or (info.dwExtraInfo & w.PEN_SIGNATURE_MASK) == w.PEN_SIGNATURE:
            return False
        return self._cross(x, y)

    def _locate(self, cx: int, cy: int) -> bool:
        """Find the monitor the cursor is on, re-reading the layout if it changed."""
        index = monitor_at(self._monitors, cx, cy)
        if index is None:  # monitors changed and the refresh hasn't arrived yet
            self._monitors = tuple(w.monitor_rects())
            index = monitor_at(self._monitors, cx, cy)
            if index is None:
                return False
        self._current, self._current_index = self._monitors[index], index
        return True

    def _cross(self, x: int, y: int) -> bool:
        """The move leaves the current monitor: land proportionally on the next one."""
        if self._settings.skip_fullscreen and self._cached_fullscreen():
            return False  # Windows moves it as usual
        target = map_crossing(self._monitors, self._current_index, x, y)
        if target is None:  # nothing borders that edge: Windows clips the move
            return False
        tx, ty, index = target
        clip = w.cursor_clip()
        if clip is not None and not clip.contains(tx, ty):
            return False  # an app (a game, say) confines the cursor: leave the move to Windows
        w.SetCursorPos(tx, ty)
        self._current, self._current_index = self._monitors[index], index
        return True

    def _handle(self, wparam, lparam) -> bool:
        """Buttons and wheel. Return True to swallow the event. Must return quickly."""
        info = w.MSLLHOOKSTRUCT.from_address(lparam)
        if info.dwExtraInfo == w.MAGIC:  # injected by us
            return False
        if wparam in _BUTTON_DOWNS:
            if self._smoothing:
                self._send(("stop",))
            return False
        hi = info.mouseData >> 16
        if wparam == w.WM_MOUSEWHEEL:
            return self._wheel(hi - 0x10000 if hi & 0x8000 else hi, info.pt.x, info.pt.y)
        if wparam == w.WM_XBUTTONDOWN:
            if self._smoothing:
                self._send(("stop",))
            swallow, action = self._engine.x_down(hi)
        elif wparam == w.WM_XBUTTONUP:
            swallow, action = self._engine.x_up(hi)
        else:
            return False
        if action:
            self._send(action)
        return swallow

    def _wheel(self, delta: int, x: int, y: int) -> bool:
        settings = self._settings
        modifiers = w.held_modifiers()
        root = None

        def elevated():
            nonlocal root
            root = w.root_window_at(x, y)
            if root not in self._elevation:
                if len(self._elevation) > 64:
                    self._elevation.clear()
                self._elevation[root] = bool(root) and w.window_is_elevated(root)
            return self._elevation[root]

        def excluded():
            hwnd = w.window_at(x, y)
            if hwnd not in self._programs:
                if len(self._programs) > 64:
                    self._programs.clear()
                self._programs[hwnd] = _program_of(hwnd)
            program = self._programs[hwnd]
            return program == _TASKBAR or program in settings.excluded

        decision = route_wheel(
            WheelEvent(delta, self._engine.claims_wheel(), modifiers, settings.smooth is not None, settings.bypass),
            fullscreen=lambda: settings.skip_fullscreen and self._cached_fullscreen(),
            elevated=elevated, excluded=excluded)
        if decision.stop and self._smoothing and decision.route != HORIZONTAL:
            self._send(("stop",))  # (a sideways step stops the vertical motion itself, keeping its own)
        if decision.mask:
            now = time.monotonic()
            if now - self._mask_time > _MASK_INTERVAL:
                self._mask_time = now
                self._send(("mask",))
        if decision.route == HORIZONTAL:
            swallow, action = self._engine.wheel(delta)
            if action and settings.smooth_sideways and not excluded():
                action = ("hsmooth", action[1], time.perf_counter(), w.root_window_at(x, y), modifiers)
            if action:
                self._send(action)
            return swallow
        if decision.route == SMOOTH:
            self._send(("smooth", delta, time.perf_counter(), root, modifiers))
            return True
        return False

    def _cached_fullscreen(self) -> bool:
        now = time.monotonic()
        if now - self._fs_time > _FULLSCREEN_TTL:
            self._fs_value = w.foreground_is_fullscreen()
            self._fs_time = now
        return self._fs_value
