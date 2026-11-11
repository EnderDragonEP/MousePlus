"""Decisions the hook makes with Win32's answers: carrying a glide into another window, crossing
monitors, the overscroll bounce and the taskbar.

Win32 is faked in every test: no hook is installed, no input is sent and no window moves.
"""
import ctypes
import unittest
from unittest import mock

from PyQt6.QtCore import QCoreApplication

from mouseplus import bounce, winapi as w
from mouseplus.cursor import Rect
from mouseplus.hook import HookSettings, MouseHook
from mouseplus.smooth import FRAME, SmoothSettings

app = QCoreApplication.instance() or QCoreApplication([])
A, B = 1001, 2002
NONE = frozenset()
LAPTOP, SIDE = Rect(0, 0, 2560, 1600), Rect(2560, 155, 5120, 1595)


def fake(test, **fakes):
    """Replace winapi functions for the length of a test."""
    for name, function in fakes.items():
        patcher = mock.patch.object(w, name, side_effect=function)
        patcher.start()
        test.addCleanup(patcher.stop)


class CarryTest(unittest.TestCase):
    def setUp(self):
        self.under = A  # top-level window under the cursor
        self.keys = NONE
        self.windows = {A: dict(program="code.exe", cls="Chrome_WidgetWin_1", elevated=False, fullscreen=False),
                        B: dict(program="firefox.exe", cls="MozillaWindowClass", elevated=False, fullscreen=False)}
        fakes = dict(held_modifiers=lambda: self.keys, cursor_pos=lambda: (10, 10),
                     root_window_at=lambda x, y: self.under, window_at=lambda x, y: self.under,
                     program_name=lambda h: self.windows[h]["program"], window_class=lambda h: self.windows[h]["cls"],
                     window_is_elevated=lambda h: self.windows[h]["elevated"],
                     is_fullscreen=lambda h: self.windows[h]["fullscreen"], send_wheel=lambda delta: None)
        for name, fake in fakes.items():
            patcher = mock.patch.object(w, name, side_effect=fake)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.now = 0.0  # the output thread's clock
        clock = mock.patch("mouseplus.hook.time", **{"perf_counter.side_effect": lambda: self.now})
        clock.start()
        self.addCleanup(clock.stop)
        self.hook = MouseHook()

    def frame(self):
        self.now += FRAME
        self.hook._frame()

    def glide(self, carry=True, skip_fullscreen=True, move=True, **b):
        """Flick in window A until it glides; then move the cursor onto B and run one output frame."""
        self.windows[B].update(b)
        smooth = SmoothSettings(carry=carry)
        hook = self.hook
        hook._settings = HookSettings(smooth=smooth, excluded=frozenset({"xnviewmp.exe"}),
                                      skip_fullscreen=skip_fullscreen)
        hook._perform(("settings", smooth))
        self.under, self.now = A, 0.0
        for _ in range(5):
            hook._perform(("smooth", -120, self.now, A, NONE))
            for _ in range(2):
                self.frame()
        while not hook._scroller.gliding:
            self.frame()
        if move:
            self.under = B
            self.frame()
        return hook._scroller.active

    def test_off_another_window_stops_the_glide(self):
        self.assertFalse(self.glide(carry=False))

    def test_on_the_glide_goes_on_in_the_other_app(self):
        self.assertTrue(self.glide())
        self.assertEqual(self.hook._gesture, (B, NONE))  # and B is now the window it scrolls

    def test_on_it_still_stops_where_it_shouldnt_scroll(self):
        cases = {"an app on the list": dict(program="xnviewmp.exe"), "the taskbar": dict(cls="Shell_TrayWnd"),
                 "an admin window": dict(elevated=True), "a full-screen app": dict(fullscreen=True)}
        for name, window in cases.items():
            with self.subTest(name):
                self.windows[B] = dict(program="firefox.exe", cls="MozillaWindowClass", elevated=False,
                                       fullscreen=False)
                self.assertFalse(self.glide(**window))

    def test_full_screen_apps_only_count_when_that_setting_is_on(self):
        self.assertTrue(self.glide(skip_fullscreen=False, fullscreen=True))

    def test_ctrl_still_stops_a_carried_glide(self):
        self.assertTrue(self.glide())
        self.keys = frozenset({"ctrl"})
        self.frame()
        self.assertFalse(self.hook._scroller.active)

    def test_a_notch_over_the_new_window_adds_to_the_glide(self):
        for carry in (True, False):
            with self.subTest(carry=carry):
                self.glide(carry=carry, move=False)  # the notch arrives before a frame noticed the move
                self.hook._perform(("smooth", -120, self.now, B, NONE))
                # With carry the notch spins the glide faster; without, the glide stops and the notch starts anew.
                self.assertEqual(self.hook._scroller.gliding, carry)
                self.assertEqual(self.hook._scroller.remaining, 0 if carry else -120)


class MoveTest(unittest.TestCase):
    """Monitor Cursor: which moves across an edge land proportionally. The cursor starts on the
    laptop near its right edge; the side monitor is to its right, 155 px lower."""

    def setUp(self):
        self.clip = Rect(-10_000, -10_000, 10_000, 10_000)  # the cursor isn't confined
        self.landed = []

        def get_cursor_pos(ref):
            self.hook._pos.x, self.hook._pos.y = 2550, 800
            return True

        fake(self, GetCursorPos=get_cursor_pos, cursor_clip=lambda: self.clip,
             SetCursorPos=lambda x, y: self.landed.append((x, y)) or True)
        self.hook = MouseHook()
        self.hook._settings = HookSettings(cursor=True, skip_fullscreen=False)
        self.hook._monitors = (LAPTOP, SIDE)

    def move(self, x, y, flags=0, extra=0):
        info = w.MSLLHOOKSTRUCT()
        info.pt.x, info.pt.y, info.flags, info.dwExtraInfo = x, y, flags, extra
        return self.hook._move(ctypes.addressof(info))

    def test_the_mouse_crosses_proportionally(self):
        self.assertTrue(self.move(2565, 800))  # swallowed and placed instead
        self.assertEqual(self.landed, [(2565, 155 + 720)])  # halfway down, halfway down

    def test_pen_touch_and_software_moves_go_where_they_point(self):
        for kind, flags, extra in (("software", w.LLMHF_INJECTED, 0), ("pen", 0, 0xFF515700),
                                   ("touch", 0, 0xFF515780)):
            with self.subTest(kind):
                self.assertFalse(self.move(2565, 800, flags, extra))
        self.assertEqual(self.landed, [])

    def test_a_confined_cursor_is_left_to_windows(self):
        self.clip = LAPTOP  # a game keeps the cursor on the laptop
        self.assertFalse(self.move(2565, 800))
        self.assertEqual(self.landed, [])


class BounceTest(unittest.TestCase):
    """The overscroll bounce moves the window with queued (asynchronous) moves."""

    def setUp(self):
        self.at = (100, 100)  # where the window really is
        self.asked = []
        fake(self, window_position=lambda hwnd: self.at, move_window=lambda hwnd, x, y: self.asked.append((x, y)))
        self.now = 0.0
        clock = mock.patch("mouseplus.hook.time", **{"perf_counter.side_effect": lambda: self.now})
        clock.start()
        self.addCleanup(clock.stop)
        hook = self.hook = MouseHook()
        hook._bounce = bounce.Bounce(7, 100, 100, -1, 12, 0.0)
        hook._bounce_at, hook._bounce_trail = (100, 100), {(100, 100)}

    def test_a_move_still_on_its_way_doesnt_end_the_bounce(self):
        self.now = 0.03
        self.hook._bounce_frame()  # asks to move the window up
        self.assertEqual(len(self.asked), 1)
        self.now = 0.15  # the window's thread still hasn't moved it
        self.hook._bounce_frame()
        self.assertIsNotNone(self.hook._bounce)
        self.assertEqual(len(self.asked), 2)

    def test_it_ends_back_where_it_started(self):
        for self.now in (0.03, 0.1, 0.2, 0.3):
            self.hook._bounce_frame()
        self.assertIsNone(self.hook._bounce)
        self.assertEqual(self.asked[-1], (100, 100))

    def test_a_move_by_someone_else_ends_it_there(self):
        self.now = 0.03
        self.hook._bounce_frame()
        self.at = (300, 250)  # the user dragged the window away
        self.hook._bounce_frame()
        self.assertIsNone(self.hook._bounce)
        self.assertEqual(len(self.asked), 1)  # and it isn't moved back


class SidewaysTest(unittest.TestCase):
    """Back/Forward + wheel while Scroll Inertia is on."""

    def setUp(self):
        self.program = "code.exe"
        self.sideways, self.vertical, self.sent = [], [], []
        fake(self, window_at=lambda x, y: 5, GetAncestor=lambda hwnd, flag: 6, root_window_at=lambda x, y: 6,
             window_class=lambda hwnd: "Chrome_WidgetWin_1", program_name=lambda hwnd: self.program,
             window_is_elevated=lambda hwnd: False, held_modifiers=lambda: NONE, cursor_pos=lambda: (10, 10),
             send_hwheel=self.sideways.append, send_wheel=self.vertical.append)
        self.now = 0.0
        clock = mock.patch("mouseplus.hook.time", **{"perf_counter.side_effect": lambda: self.now})
        clock.start()
        self.addCleanup(clock.stop)
        hook = self.hook = MouseHook()
        hook._settings = HookSettings(smooth=SmoothSettings(), excluded=frozenset({"xnviewmp.exe"}),
                                      skip_fullscreen=False)
        hook._send = self.sent.append
        hook._perform(("settings", SmoothSettings()))

    def scroll_sideways(self):
        self.hook._engine.held = 1  # Back is held
        return self.hook._wheel(-120, 10, 10)

    def play(self):
        while self.hook._scroller.active or self.hook._hscroller.active:
            self.now += FRAME
            self.hook._frame()

    def test_back_forward_and_wheel_scrolls_smoothly(self):
        self.hook._smoothing = True  # a vertical glide is running
        self.assertTrue(self.scroll_sideways())
        self.assertEqual(self.sent[-1][:2], ("hsmooth", 120))  # wheel down scrolls right
        self.assertNotIn(("stop",), self.sent)  # the output thread stops the vertical motion itself

    def test_plain_steps_in_apps_on_the_list_or_with_scroll_inertia_off(self):
        self.program = "xnviewmp.exe"
        self.scroll_sideways()
        self.assertEqual(self.sent[-1], ("hwheel", 120))
        self.program, self.hook._programs = "code.exe", {}
        self.hook._settings = HookSettings(smooth=None, skip_fullscreen=False)
        self.scroll_sideways()
        self.assertEqual(self.sent[-1], ("hwheel", 120))
        self.hook._settings = HookSettings(smooth=SmoothSettings(inertia=False, bounce=True), skip_fullscreen=False)
        self.scroll_sideways()  # just the bounce on: nothing to do sideways
        self.assertEqual(self.sent[-1], ("hwheel", 120))

    def test_a_sideways_notch_goes_out_whole(self):
        self.hook._perform(("hsmooth", 120, self.now, 6, NONE))
        self.play()
        self.assertEqual(self.sideways, [120])
        self.assertEqual(self.vertical, [])

    def test_a_sideways_flick_glides_on_in_whole_notches(self):
        for _ in range(8):
            self.hook._perform(("hsmooth", 120, self.now, 6, NONE))
            for _ in range(2):
                self.now += FRAME
                self.hook._frame()
        self.play()
        self.assertTrue(all(step == 120 for step in self.sideways))
        self.assertGreater(len(self.sideways), 8 + 3)  # the notches, then the glide's
        self.assertEqual(self.vertical, [])

    def test_each_direction_stops_the_other(self):
        self.hook._perform(("hsmooth", 120, self.now, 6, NONE))
        self.hook._perform(("smooth", -120, self.now, 6, NONE))
        self.assertFalse(self.hook._hscroller.active)
        self.assertTrue(self.hook._scroller.active)
        self.hook._perform(("hwheel", 120))  # a plain sideways step: both give way
        self.assertFalse(self.hook._scroller.active)
        self.assertEqual(self.sideways, [120])

    def test_sideways_skips_the_bounce(self):
        self.hook._perform(("settings", SmoothSettings(bounce=True, free_spin=True)))
        self.assertTrue(self.hook._scroller.settings.bounce)
        sideways = self.hook._hscroller.settings
        self.assertEqual((sideways.bounce, sideways.free_spin), (False, True))


class TaskbarTest(unittest.TestCase):
    def setUp(self):
        self.root_class = "Shell_TrayWnd"
        fake(self, window_at=lambda x, y: 5, GetAncestor=lambda hwnd, flag: 6, root_window_at=lambda x, y: 6,
             window_class=lambda hwnd: self.root_class, program_name=lambda hwnd: "explorer.exe",
             window_is_elevated=lambda hwnd: False, held_modifiers=lambda: NONE)
        self.hook = MouseHook()
        self.hook._settings = HookSettings(smooth=SmoothSettings(), skip_fullscreen=False)
        self.hook._send = lambda action: None

    def test_the_taskbar_scrolls_normally(self):
        self.assertFalse(self.hook._wheel(-120, 10, 10))  # passed on as one notch
        self.root_class, self.hook._programs = "CabinetWClass", {}  # a File Explorer window instead
        self.assertTrue(self.hook._wheel(-120, 10, 10))  # smoothed


if __name__ == "__main__":
    unittest.main()
