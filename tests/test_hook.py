"""The output thread's decision to keep a glide going when the cursor moves to another window.

Win32 is faked: two top-level windows, A where the flick started and B, with whatever program,
class and state each test gives B. No hook is installed and no input is sent.
"""
import unittest
from unittest import mock

from PyQt6.QtCore import QCoreApplication

from mouseplus import winapi as w
from mouseplus.hook import HookSettings, MouseHook
from mouseplus.smooth import FRAME, SmoothSettings

app = QCoreApplication.instance() or QCoreApplication([])
A, B = 1001, 2002
NONE = frozenset()


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
                remaining = abs(self.hook._scroller.remaining)
                self.assertEqual(remaining > 120, carry)  # without carry, only the new notch is left


if __name__ == "__main__":
    unittest.main()
