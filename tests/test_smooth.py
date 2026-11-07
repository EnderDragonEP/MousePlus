import unittest

from mouseplus.smooth import FRAME, GLIDES, SmoothScroller, SmoothSettings


def run(settings, notches, gap, until=30.0):
    """Send `notches` notches `gap` seconds apart and play frames until the motion ends.
    Returns (every step sent, the time of each, whether it glided, the scroller)."""
    s = SmoothScroller(settings)
    t, steps, times, glided = 0.0, [], [], False

    def tick():
        nonlocal t, glided
        t += FRAME
        step = s.frame(t)
        glided = glided or s.gliding
        if step:
            steps.append(step)
            times.append(t)

    for _ in range(notches):
        s.add(-120, t)
        for _ in range(max(1, round(gap / FRAME))):
            tick()
    while s.active and t < until:
        tick()
    return steps, times, glided, s


def notches_scrolled(settings, notches, gap):
    return abs(sum(run(settings, notches, gap)[0])) / 120


HARD, GENTLE = (8, 0.02), (3, 0.05)  # notches and seconds between them
FREE = SmoothSettings(free_spin=True)
LONG = SmoothSettings(glide=GLIDES["long"])


def gliding(settings=SmoothSettings()):
    """A scroller in the middle of a glide after a hard flick, and the current time."""
    s = SmoothScroller(settings)
    t = 0.0
    for _ in range(8):
        s.add(-120, t)
        t += 0.02
        s.frame(t)
    while not s.gliding:
        t += FRAME
        s.frame(t)
    for _ in range(5):
        t += FRAME
        s.frame(t)
    return s, t


class NotchTest(unittest.TestCase):
    def test_a_notch_goes_out_whole_and_at_once(self):
        steps, times, glided, s = run(SmoothSettings(), 1, FRAME)
        self.assertEqual(steps, [-120])
        self.assertLess(times[0], 2 * FRAME)
        self.assertFalse(glided)
        self.assertFalse(s.active)

    def test_slow_notches_dont_glide(self):
        steps, _, glided, _ = run(SmoothSettings(), 3, 0.3)
        self.assertEqual((steps, glided), ([-120] * 3, False))

    def test_stop(self):
        s, t = gliding()
        s.stop()
        self.assertFalse(s.active)
        self.assertEqual(s.frame(t + FRAME), 0)


class InertiaTest(unittest.TestCase):
    def test_a_flick_glides_on_in_whole_notches(self):
        steps, _, glided, s = run(SmoothSettings(), *HARD)
        self.assertTrue(glided)
        self.assertTrue(all(x % 120 == 0 and x < 0 for x in steps))
        self.assertGreater(len(steps), 8 + 5)  # the 8 notches, then the glide's
        self.assertFalse(s.active)              # and it stops by itself

    def test_the_glide_slows_down_steadily(self):
        s, t = gliding()
        speeds = []
        while s.gliding:
            t += FRAME
            s.frame(t)
            speeds.append(abs(s.velocity))
        self.assertGreater(len(speeds), 20)
        self.assertEqual(speeds, sorted(speeds, reverse=True))

    def test_it_ends_without_stuttering(self):
        """Slow, far-apart notches at the end of a glide read as a stutter: it ends before that."""
        for name, settings in (("medium", SmoothSettings()), ("long", LONG), ("free spin", FREE)):
            with self.subTest(name):
                times = run(settings, *HARD)[1]
                self.assertLessEqual(max(b - a for a, b in zip(times, times[1:])), 0.13)

    def test_a_harder_flick_glides_further(self):
        self.assertGreater(notches_scrolled(SmoothSettings(), *HARD) - 8,
                           notches_scrolled(SmoothSettings(), *GENTLE) - 3)

    def test_even_a_gentle_flick_glides_a_little(self):
        self.assertGreaterEqual(notches_scrolled(SmoothSettings(), *GENTLE), 3 + 2)

    def test_a_longer_glide_goes_further(self):
        self.assertGreater(notches_scrolled(LONG, *HARD),
                           notches_scrolled(SmoothSettings(glide=GLIDES["short"]), *HARD))

    def test_the_multiplier_scales_the_glide(self):
        normal = notches_scrolled(SmoothSettings(), *HARD) - 8
        self.assertGreater(notches_scrolled(SmoothSettings(momentum=2.0), *HARD) - 8, 1.5 * normal)
        self.assertLess(notches_scrolled(SmoothSettings(momentum=0.5), *HARD) - 8, normal)

    def test_the_multiplier_eases_in_without_a_jerk(self):
        s = SmoothScroller(SmoothSettings(momentum=3.0))
        t = 0.0
        for _ in range(8):
            s.add(-120, t)
            t += 0.02
            s.frame(t)
        while not s.gliding:
            t += FRAME
            s.frame(t)
        speeds = [abs(s.velocity)]
        self.assertEqual(speeds[0], abs(s.glide_base))  # starts at the speed set by the flick
        while s.gliding and len(speeds) < 20:
            t += FRAME
            s.frame(t)
            speeds.append(abs(s.velocity))
        changes = [b / a for a, b in zip(speeds, speeds[1:])]
        self.assertLess(max(changes), 1.5)              # speeds up smoothly, never jumps
        self.assertGreater(max(speeds), 2 * speeds[0])  # and does get the boost

    def test_another_notch_the_same_way_spins_it_faster(self):
        s, t = gliding()
        before = abs(s.velocity)
        s.add(-120, t)
        self.assertTrue(s.gliding)
        self.assertGreater(abs(s.velocity), before)

    def test_turning_the_wheel_back_during_a_glide_only_stops_it(self):
        s, t = gliding()
        s.add(120, t)
        self.assertFalse(s.active)
        self.assertEqual(s.frame(t + FRAME), 0)  # nothing scrolls back
        s.add(120, t + 0.1)                      # the next notch that way scrolls as usual
        self.assertEqual(s.frame(t + 0.1 + FRAME), 120)

    def test_turning_the_wheel_back_can_scroll_back(self):
        s, t = gliding(SmoothSettings(brake=False))
        s.add(120, t)
        self.assertEqual(s.frame(t + FRAME), 120)
        self.assertFalse(s.gliding)

    def test_turning_back_before_a_glide_is_just_a_notch_the_other_way(self):
        s = SmoothScroller()
        s.add(-120, 0.0)
        self.assertEqual(s.frame(FRAME), -120)
        s.add(120, 0.02)
        self.assertEqual(s.frame(0.02 + FRAME), 120)


class FreeSpinTest(unittest.TestCase):
    def test_coasts_much_farther_and_longer_than_the_long_glide(self):
        spin, spin_times, _, _ = run(FREE, *HARD)
        long_, long_times, _, _ = run(LONG, *HARD)
        self.assertGreater(abs(sum(spin)), 5 * abs(sum(long_)))
        self.assertGreater(spin_times[-1], 2 * long_times[-1])
        self.assertLess(spin_times[-1], 10.5)  # and stops by itself

    def test_a_hard_flick_goes_disproportionately_farther(self):
        def ratio(settings):
            return notches_scrolled(settings, *HARD) / notches_scrolled(settings, *GENTLE)
        self.assertGreater(ratio(FREE), 2 * ratio(LONG))

    def test_slows_down_steadily(self):
        s, t = gliding(FREE)
        speeds = []
        while s.gliding:
            t += FRAME
            s.frame(t)
            speeds.append(abs(s.velocity))
        self.assertGreater(len(speeds), 120 * 3)  # seconds of coasting
        self.assertEqual(speeds, sorted(speeds, reverse=True))

    def test_the_multiplier_scales_it(self):
        self.assertGreater(notches_scrolled(SmoothSettings(free_spin=True, momentum=2.0), *HARD),
                           1.5 * notches_scrolled(FREE, *HARD))


class FlickThresholdTest(unittest.TestCase):
    def test_fewer_notches_make_a_flick_when_set_lower(self):
        self.assertTrue(run(SmoothSettings(flick=2), 2, 0.05)[2])  # two quick notches glide
        self.assertFalse(run(SmoothSettings(), 2, 0.05)[2])        # not with the default 3

    def test_more_notches_are_needed_when_set_higher(self):
        self.assertTrue(run(SmoothSettings(), 3, 0.05)[2])
        self.assertFalse(run(SmoothSettings(flick=4), 3, 0.05)[2])
        self.assertTrue(run(SmoothSettings(flick=4), 4, 0.04)[2])


if __name__ == "__main__":
    unittest.main()
