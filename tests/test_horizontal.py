import unittest

from mouseplus.horizontal import BACK, FORWARD, PASS, SWALLOW, Engine, Settings


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.fullscreen = False
        self.latch_events = []
        self.engine = Engine(lambda: self.fullscreen, self.latch_events.append)

    def use(self, **kwargs):
        self.engine.apply(Settings(**kwargs))

    # -- hold mode --

    def test_hold_and_scroll_converts_to_horizontal(self):
        self.assertEqual(self.engine.x_down(BACK), SWALLOW)
        self.assertEqual(self.engine.wheel(-120), (True, ("hwheel", 120)))  # wheel down -> right
        self.assertEqual(self.engine.wheel(120), (True, ("hwheel", -120)))
        self.assertEqual(self.engine.x_up(BACK), SWALLOW)  # no click replay after scrolling

    def test_quick_click_is_replayed(self):
        self.assertEqual(self.engine.x_down(FORWARD), SWALLOW)
        self.assertEqual(self.engine.x_up(FORWARD), (True, ("click", FORWARD)))

    def test_wheel_without_trigger_passes(self):
        self.assertEqual(self.engine.wheel(-120), PASS)

    def test_only_selected_trigger_reacts(self):
        self.use(buttons=frozenset({BACK}))
        self.assertEqual(self.engine.x_down(FORWARD), PASS)
        self.assertEqual(self.engine.wheel(-120), PASS)
        self.assertEqual(self.engine.x_up(FORWARD), PASS)

    def test_second_x_button_while_holding_passes(self):
        self.engine.x_down(BACK)
        self.assertEqual(self.engine.x_down(FORWARD), PASS)
        self.assertEqual(self.engine.x_up(FORWARD), PASS)
        self.assertEqual(self.engine.wheel(-120), (True, ("hwheel", 120)))

    def test_lost_button_up_recovers(self):
        self.engine.x_down(BACK)
        self.engine.wheel(-120)
        # the "up" never arrived; a new press starts a fresh hold
        self.assertEqual(self.engine.x_down(BACK), SWALLOW)
        self.assertEqual(self.engine.x_up(BACK), (True, ("click", BACK)))
        self.assertEqual(self.engine.wheel(-120), PASS)

    # -- toggle mode --

    def test_click_latches_and_unlatches(self):
        self.use(toggle_mode=True)
        self.engine.x_down(BACK)
        self.assertEqual(self.engine.x_up(BACK), SWALLOW)
        self.assertTrue(self.engine.latched)
        self.assertEqual(self.engine.wheel(-120), (True, ("hwheel", 120)))
        self.engine.x_down(FORWARD)
        self.engine.x_up(FORWARD)
        self.assertFalse(self.engine.latched)
        self.assertEqual(self.engine.wheel(-120), PASS)
        self.assertEqual(self.latch_events, [True, False])

    def test_hold_and_scroll_in_toggle_mode_does_not_latch(self):
        self.use(toggle_mode=True)
        self.engine.x_down(BACK)
        self.assertEqual(self.engine.wheel(-120), (True, ("hwheel", 120)))
        self.assertEqual(self.engine.x_up(BACK), SWALLOW)
        self.assertFalse(self.engine.latched)

    def test_leaving_toggle_mode_unlatches(self):
        self.use(toggle_mode=True)
        self.engine.x_down(BACK)
        self.engine.x_up(BACK)
        self.use(toggle_mode=False)
        self.assertFalse(self.engine.latched)
        self.assertEqual(self.latch_events, [True, False])

    def test_reset_unlatches(self):
        self.use(toggle_mode=True)
        self.engine.x_down(BACK)
        self.engine.x_up(BACK)
        self.engine.reset()
        self.assertFalse(self.engine.latched)

    # -- full screen --

    def test_fullscreen_passes_everything(self):
        self.fullscreen = True
        self.assertEqual(self.engine.x_down(BACK), PASS)
        self.assertEqual(self.engine.wheel(-120), PASS)
        self.assertEqual(self.engine.x_up(BACK), PASS)

    def test_fullscreen_check_can_be_disabled(self):
        self.use(skip_fullscreen=False)
        self.fullscreen = True
        self.assertEqual(self.engine.x_down(BACK), SWALLOW)
        self.assertEqual(self.engine.wheel(-120), (True, ("hwheel", 120)))

    def test_fullscreen_turns_latch_off(self):
        self.use(toggle_mode=True)
        self.engine.x_down(BACK)
        self.engine.x_up(BACK)
        self.fullscreen = True
        self.assertEqual(self.engine.wheel(-120), PASS)
        self.assertFalse(self.engine.latched)
        self.fullscreen = False
        self.assertEqual(self.engine.wheel(-120), PASS)  # stays off after leaving full screen

    def test_fullscreen_trigger_press_turns_latch_off(self):
        self.use(toggle_mode=True)
        self.engine.x_down(BACK)
        self.engine.x_up(BACK)
        self.fullscreen = True
        self.assertEqual(self.engine.x_down(BACK), PASS)
        self.assertFalse(self.engine.latched)

    # -- direction and speed --

    def test_reverse(self):
        self.use(reverse=True)
        self.engine.x_down(BACK)
        self.assertEqual(self.engine.wheel(-120), (True, ("hwheel", -120)))

    def test_speed(self):
        self.use(speed=2.5)
        self.engine.x_down(BACK)
        self.assertEqual(self.engine.wheel(-120), (True, ("hwheel", 300)))
        self.use(speed=0.5)
        self.assertEqual(self.engine.wheel(120), (True, ("hwheel", -60)))

    def test_tiny_delta_never_becomes_zero(self):
        self.use(speed=0.5)
        self.engine.x_down(BACK)
        self.assertEqual(self.engine.wheel(-1), (True, ("hwheel", 1)))
        self.assertEqual(self.engine.wheel(1), (True, ("hwheel", -1)))

    def test_zero_delta_passes(self):
        self.engine.x_down(BACK)
        self.assertEqual(self.engine.wheel(0), PASS)


if __name__ == "__main__":
    unittest.main()
