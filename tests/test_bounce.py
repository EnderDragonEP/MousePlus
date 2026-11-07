import unittest

from mouseplus.bounce import AMPLITUDE, DURATION, Bounce, at_edge, offset


class AtEdgeTest(unittest.TestCase):
    # A bar from 0 to 99 showing 20 at a time can reach positions 0..80.
    def test_bottom(self):
        self.assertTrue(at_edge(-1, 80, 0, 99, 20))
        self.assertFalse(at_edge(-1, 79, 0, 99, 20))
        self.assertFalse(at_edge(+1, 80, 0, 99, 20))  # scrolling back up is fine

    def test_top(self):
        self.assertTrue(at_edge(+1, 0, 0, 99, 20))
        self.assertFalse(at_edge(+1, 1, 0, 99, 20))
        self.assertFalse(at_edge(-1, 0, 0, 99, 20))

    def test_nothing_to_scroll(self):
        self.assertFalse(at_edge(-1, 0, 0, 99, 100))
        self.assertFalse(at_edge(+1, 0, 0, 0, 0))

    def test_page_of_zero_counts_as_one(self):
        self.assertTrue(at_edge(-1, 99, 0, 99, 0))


class OffsetTest(unittest.TestCase):
    def test_starts_and_ends_at_rest(self):
        self.assertEqual(offset(0), 0)
        self.assertEqual(offset(DURATION), 0)
        self.assertEqual(offset(DURATION + 1), 0)

    def test_quick_out_soft_back(self):
        samples = [offset(DURATION * i / 100) for i in range(101)]
        peak = samples.index(max(samples))
        self.assertEqual(max(samples), AMPLITUDE)
        self.assertLess(peak, 50)  # peaks in the first half
        self.assertEqual(samples[peak:], sorted(samples[peak:], reverse=True))

    def test_amplitude_scales(self):
        self.assertEqual(max(offset(DURATION * i / 100, amplitude=24) for i in range(101)), 24)


class BounceTest(unittest.TestCase):
    def test_moves_up_and_comes_back(self):
        bounce = Bounce(window=1, x=100, y=200, direction=-1, amplitude=AMPLITUDE, start=10.0)
        ys = [bounce.position(10.0 + DURATION * i / 50)[1] for i in range(50)]
        self.assertEqual(min(ys), 200 - AMPLITUDE)
        self.assertTrue(all(y <= 200 for y in ys))
        self.assertIsNone(bounce.position(10.0 + DURATION))


if __name__ == "__main__":
    unittest.main()
