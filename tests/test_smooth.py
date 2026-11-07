import unittest

from mouseplus.smooth import FRAME, GLIDES, SmoothScroller, SmoothSettings


def play(scroller, start, until=10.0):
    """Run frames until the motion stops; return (steps, time of the last step)."""
    steps, t = [], start
    while scroller.active and t < until:
        t += FRAME
        steps.append(scroller.frame(t))
    return steps, t


class EasingTest(unittest.TestCase):
    def test_one_notch_plays_out_exactly(self):
        s = SmoothScroller()
        s.add(-120, 0.0)
        steps, end = play(s, 0.0)
        self.assertEqual(sum(steps), -120)
        self.assertTrue(all(step <= 0 for step in steps))
        self.assertGreater(len([x for x in steps if x]), 10)  # many small steps, not one jump
        self.assertLess(end, 0.5)

    def test_first_step_is_immediate_and_largest(self):
        s = SmoothScroller()
        s.add(120, 0.0)
        steps, _ = play(s, 0.0)
        self.assertGreater(steps[0], 0)
        self.assertEqual(max(steps), steps[0])

    def test_distance_multiplier(self):
        for distance, total in ((2.0, 240), (0.5, 60), (1.5, 180)):
            s = SmoothScroller(SmoothSettings(distance=distance))
            s.add(120, 0.0)
            self.assertEqual(sum(play(s, 0.0)[0]), total)

    def test_slower_animation_takes_longer(self):
        times = []
        for duration in (0.12, 0.32):
            s = SmoothScroller(SmoothSettings(duration=duration))
            s.add(120, 0.0)
            times.append(play(s, 0.0)[1])
        self.assertLess(times[0], times[1])

    def test_without_animation_a_notch_goes_out_at_once(self):
        s = SmoothScroller(SmoothSettings(animate=False, distance=2.0))
        s.add(-120, 0.0)
        self.assertEqual(s.frame(FRAME), -240)
        self.assertFalse(s.active)

    def test_slow_notches_add_up_without_inertia(self):
        s = SmoothScroller()
        t = 0.0
        total = []
        for _ in range(3):  # 3 notches, 0.3 s apart: not a flick
            s.add(-120, t)
            steps, t = play(s, t)
            total += steps
            t += 0.3
        self.assertEqual(sum(total), -360)


class InertiaTest(unittest.TestCase):
    def flick(self, settings=SmoothSettings(), notches=5, gap=0.02):
        s = SmoothScroller(settings)
        t, steps = 0.0, []
        for _ in range(notches):
            s.add(-120, t)
            for _ in range(round(gap / FRAME)):
                t += FRAME
                steps.append(s.frame(t))
        more, end = play(s, t)
        return steps + more, end, s

    def test_flick_glides_past_the_notches(self):
        steps, end, s = self.flick()
        self.assertLess(sum(steps), -5 * 120)  # further than the five notches alone
        self.assertGreater(end, 0.5)            # keeps moving well after the last notch
        self.assertFalse(s.active)              # and stops by itself

    def test_glide_slows_down_steadily(self):
        s = SmoothScroller()
        t = 0.0
        for _ in range(5):
            s.add(-120, t)
            t += 0.02
            s.frame(t)
        speeds = []
        while s.active:
            t += FRAME
            s.frame(t)
            if s.gliding:
                speeds.append(abs(s.velocity))
        self.assertGreater(len(speeds), 20)
        self.assertEqual(speeds, sorted(speeds, reverse=True))

    def test_harder_flick_glides_further(self):
        soft, _, _ = self.flick(notches=3)
        hard, _, _ = self.flick(notches=8)
        glide_soft = abs(sum(soft)) - 3 * 120  # distance beyond the notches themselves
        glide_hard = abs(sum(hard)) - 8 * 120
        self.assertGreater(glide_hard, glide_soft)

    def test_longer_glide_setting_goes_further(self):
        short, _, _ = self.flick(SmoothSettings(glide=GLIDES["short"]))
        long_, _, _ = self.flick(SmoothSettings(glide=GLIDES["long"]))
        self.assertGreater(abs(sum(long_)), abs(sum(short)))

    def test_inertia_off_means_no_glide(self):
        steps, _, _ = self.flick(SmoothSettings(inertia=False))
        self.assertEqual(sum(steps), -5 * 120)

    def test_reverse_wheel_stops_at_once(self):
        s = SmoothScroller()
        t = 0.0
        for _ in range(5):
            s.add(-120, t)
            t += 0.02
            s.frame(t)
        s.add(120, t)                  # the other way
        self.assertEqual(s.direction, 1)
        steps, _ = play(s, t)
        self.assertEqual(sum(steps), 120)  # only the new notch plays out
        self.assertTrue(all(x >= 0 for x in steps))

    def test_stop(self):
        s = SmoothScroller()
        s.add(-120, 0.0)
        s.frame(FRAME)
        s.stop()
        self.assertFalse(s.active)
        self.assertEqual(s.frame(2 * FRAME), 0)


if __name__ == "__main__":
    unittest.main()
