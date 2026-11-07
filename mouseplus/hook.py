"""Global low-level mouse hook (WH_MOUSE_LL) running on its own thread, shared by every feature."""
import ctypes
import logging
import queue
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, pyqtSignal

from . import winapi as w
from .cursor import Rect, map_crossing, monitor_at
from .horizontal import Engine, Settings

log = logging.getLogger("mouseplus")

_WM_APPLY = w.WM_APP + 1   # thread message: pick up new settings or monitors
_WATCHDOG_MS = 30_000      # periodic hook re-install
_FULLSCREEN_TTL = 0.25     # seconds to cache the full-screen check
_NOWHERE = Rect(0, 0, 0, 0)


@dataclass(frozen=True)
class HookSettings:
    horizontal: Settings = field(default_factory=Settings)
    cursor: bool = False           # Monitor Cursor: proportional moves between monitors
    skip_fullscreen: bool = True   # every feature stays out of full-screen apps


class MouseHook(QObject):
    """Routes mouse events to the features and performs what they decide.

    Two threads:
    - the hook thread runs a plain Win32 message loop and answers hook calls;
      the features' state is only touched there, settings changes are posted to it.
    - the injector thread calls SendInput. SendInput waits until every
      low-level hook (ours included) has seen the injected event, so calling
      it on the hook thread would stall input until Windows times us out.
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
        self._hhook = None
        self._thread = None
        self._injector = None
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

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, settings: HookSettings) -> bool:
        if self.running:
            self.update(settings)
            return True
        self._settings = settings
        self._injector = threading.Thread(target=self._inject_loop, name="MouseInjector", daemon=True)
        self._injector.start()
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
        if self._injector is not None:
            self._actions.put(None)
            self._injector.join(2)
            self._injector = None

    def _post_apply(self):
        if self.running:
            w.PostThreadMessageW(self._tid, _WM_APPLY, 0, 0)

    # -- injector thread -------------------------------------------------

    def _inject_loop(self):
        while (action := self._actions.get()) is not None:
            kind, value = action
            try:
                if kind == "hwheel":
                    w.send_hwheel(value)
                else:
                    w.send_xclick(value)
            except Exception:
                log.exception("SendInput failed")

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
        pt = w.MSLLHOOKSTRUCT.from_address(lparam).pt
        x, y = pt.x, pt.y
        if current.left <= x < current.right and current.top <= y < current.bottom:
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
        w.SetCursorPos(tx, ty)
        self._current, self._current_index = self._monitors[index], index
        return True

    def _handle(self, wparam, lparam) -> bool:
        """Buttons and wheel. Return True to swallow the event. Must return quickly."""
        info = w.MSLLHOOKSTRUCT.from_address(lparam)
        if info.dwExtraInfo == w.MAGIC:  # injected by us
            return False
        hi = info.mouseData >> 16
        if wparam == w.WM_MOUSEWHEEL:
            swallow, action = self._engine.wheel(hi - 0x10000 if hi & 0x8000 else hi)
        elif wparam == w.WM_XBUTTONDOWN:
            swallow, action = self._engine.x_down(hi)
        elif wparam == w.WM_XBUTTONUP:
            swallow, action = self._engine.x_up(hi)
        else:
            return False
        if action:
            self._actions.put(action)
        return swallow

    def _cached_fullscreen(self) -> bool:
        now = time.monotonic()
        if now - self._fs_time > _FULLSCREEN_TTL:
            self._fs_value = w.foreground_is_fullscreen()
            self._fs_time = now
        return self._fs_value
