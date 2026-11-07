import unittest

from mouseplus.router import HORIZONTAL, PASS, SMOOTH, Decision, WheelEvent, route_wheel

ALT = frozenset({"alt"})
NONE = frozenset()


def route(delta=-120, horizontal=False, modifiers=NONE, smooth=True, bypass=ALT,
          fullscreen=False, elevated=False, excluded=False):
    def must_not_be_called():
        raise AssertionError("checked although an earlier rule already decided")

    def check(value):
        return (lambda: value) if value is not None else must_not_be_called

    return route_wheel(WheelEvent(delta, horizontal, frozenset(modifiers), smooth, bypass),
                       check(fullscreen), check(elevated), check(excluded))


class RouteWheelTest(unittest.TestCase):
    def test_plain_notch_is_smoothed(self):
        self.assertEqual(route(), Decision(SMOOTH))

    def test_back_forward_wins_over_everything(self):
        for mods in (NONE, ALT, {"ctrl"}, {"alt", "ctrl", "shift", "win"}):
            self.assertEqual(route(horizontal=True, modifiers=mods, fullscreen=None, elevated=None),
                             Decision(HORIZONTAL, stop=True))

    def test_fullscreen_passes(self):
        self.assertEqual(route(fullscreen=True), Decision(PASS, stop=True))

    def test_bypass_key_passes_untouched_and_stops_inertia(self):
        self.assertEqual(route(modifiers=ALT, elevated=None), Decision(PASS, stop=True, mask=True))
        self.assertEqual(route(modifiers={"alt", "shift"}, elevated=None), Decision(PASS, stop=True, mask=True))

    def test_combination_needs_every_key(self):
        ctrl_alt = frozenset({"ctrl", "alt"})
        self.assertEqual(route(modifiers=ctrl_alt, bypass=ctrl_alt, elevated=None),
                         Decision(PASS, stop=True, mask=True))
        self.assertEqual(route(modifiers=ALT, bypass=ctrl_alt), Decision(SMOOTH))  # Alt alone isn't the combo

    def test_mask_only_for_alt_and_win(self):
        shift = frozenset({"shift"})
        self.assertEqual(route(modifiers=shift, bypass=shift, elevated=None), Decision(PASS, stop=True))
        win = frozenset({"win"})
        self.assertEqual(route(modifiers=win, bypass=win, elevated=None), Decision(PASS, stop=True, mask=True))

    def test_ctrl_wheel_always_passes(self):
        self.assertEqual(route(modifiers={"ctrl"}, elevated=None), Decision(PASS, stop=True))
        self.assertEqual(route(modifiers={"ctrl"}, bypass=NONE, elevated=None), Decision(PASS, stop=True))

    def test_no_bypass_key_means_alt_is_smoothed(self):
        self.assertEqual(route(modifiers=ALT, bypass=NONE), Decision(SMOOTH))

    def test_shift_wheel_is_smoothed(self):
        self.assertEqual(route(modifiers={"shift"}), Decision(SMOOTH))

    def test_smooth_scroll_off_passes(self):
        self.assertEqual(route(smooth=False, elevated=None), Decision(PASS))

    def test_fine_deltas_pass(self):
        for delta in (15, -40, 119, 121):
            self.assertEqual(route(delta=delta, elevated=None), Decision(PASS))
        self.assertEqual(route(delta=240), Decision(SMOOTH))  # two notches at once

    def test_elevated_window_passes(self):
        self.assertEqual(route(elevated=True), Decision(PASS))

    def test_app_on_the_list_passes(self):
        self.assertEqual(route(excluded=True, elevated=None), Decision(PASS))  # no need to look further

    def test_app_list_is_only_checked_for_plain_notches(self):
        for rule in (dict(horizontal=True, fullscreen=None), dict(fullscreen=True), dict(modifiers=ALT),
                     dict(modifiers={"ctrl"}), dict(smooth=False), dict(delta=40)):
            route(**rule, elevated=None, excluded=None)  # raises if the list is looked up

    def test_the_list_doesnt_touch_horizontal_scroll(self):
        self.assertEqual(route(horizontal=True, fullscreen=None, elevated=None, excluded=None),
                         Decision(HORIZONTAL, stop=True))


if __name__ == "__main__":
    unittest.main()
