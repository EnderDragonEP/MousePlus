import unittest

from mouseplus.cursor import Rect, map_crossing, monitor_at

# The development machine: a 2560x1600 laptop panel with a 2560x1440 monitor to its right, 155 px lower.
LAPTOP = Rect(0, 0, 2560, 1600)
SIDE = Rect(2560, 155, 5120, 1595)


class MonitorAtTest(unittest.TestCase):
    def test_finds_the_monitor(self):
        self.assertEqual(monitor_at([LAPTOP, SIDE], 10, 10), 0)
        self.assertEqual(monitor_at([LAPTOP, SIDE], 2560, 155), 1)
        self.assertIsNone(monitor_at([LAPTOP, SIDE], 2600, 50))  # dead zone


class SideBySideTest(unittest.TestCase):
    monitors = [LAPTOP, SIDE]

    def test_still_inside_is_left_alone(self):
        self.assertIsNone(map_crossing(self.monitors, 0, 2559, 800))

    def test_halfway_lands_halfway(self):
        self.assertEqual(map_crossing(self.monitors, 0, 2560, 800), (2560, 155 + 720, 1))

    def test_dead_zone_rows_cross_too(self):
        x, y, target = map_crossing(self.monitors, 0, 2562, 50)
        self.assertEqual((x, y, target), (2562, 155 + 45, 1))  # 50/1600 of 1440 rows below the top
        x, y, target = map_crossing(self.monitors, 0, 2560, 1599)
        self.assertEqual((target, y), (1, 1594))  # the last row maps to the last row

    def test_round_trip_lands_where_it_started(self):
        x, y, _ = map_crossing(self.monitors, 0, 2560, 1000)
        back_x, back_y, target = map_crossing(self.monitors, 1, 2559, y)
        self.assertEqual(target, 0)
        self.assertEqual(back_x, 2559)
        self.assertLessEqual(abs(back_y - 1000), 1)

    def test_edges_without_a_neighbour_are_left_to_windows(self):
        self.assertIsNone(map_crossing(self.monitors, 0, -1, 800))   # left of the laptop
        self.assertIsNone(map_crossing(self.monitors, 0, 100, -1))   # above it
        self.assertIsNone(map_crossing(self.monitors, 1, 3000, 1595))  # below the side monitor

    def test_overshoot_keeps_the_motion(self):
        x, y, _ = map_crossing(self.monitors, 0, 2575, 800)
        self.assertEqual(x, 2575)


class OtherLayoutsTest(unittest.TestCase):
    def test_stacked_with_different_widths(self):
        top = Rect(320, 0, 2240, 1080)       # 1920 wide, centred above
        bottom = Rect(0, 1080, 2560, 2520)   # 2560 wide
        x, y, target = map_crossing([top, bottom], 0, 320 + 960, 1080)
        self.assertEqual((x, y, target), (1280, 1080, 1))  # halfway across stays halfway across
        x, y, target = map_crossing([top, bottom], 1, 2500, 1079)  # far right of the bottom one
        self.assertEqual(target, 0)
        self.assertEqual(x, 320 + int((2500 / 2560) * 1920))

    def test_one_monitor_next_to_two(self):
        tall = Rect(0, 0, 2560, 1440)
        upper = Rect(2560, 0, 4480, 1080)
        lower = Rect(2560, 1080, 4480, 2160)
        monitors = [tall, upper, lower]
        x, y, target = map_crossing(monitors, 0, 2560, 720)  # halfway down the tall one
        self.assertEqual((y, target), (1080, 2))           # halfway down the pair: top of the lower one
        x, y, target = map_crossing(monitors, 1, 2559, 540)  # a quarter down the pair
        self.assertEqual((x, y, target), (2559, 360, 0))

    def test_negative_coordinates(self):
        left = Rect(-1920, 200, 0, 1280)
        primary = Rect(0, 0, 2560, 1440)
        x, y, target = map_crossing([left, primary], 1, -1, 720)
        self.assertEqual((x, y, target), (-1, 200 + 540, 0))

    def test_mixed_resolutions(self):
        uhd = Rect(0, 0, 3840, 2160)
        fhd = Rect(3840, 0, 5760, 1080)  # only covers the top half of the 4K edge
        x, y, target = map_crossing([uhd, fhd], 0, 3840, 1620)  # three quarters down
        self.assertEqual((y, target), (810, 1))

    def test_corner_contact_is_not_a_shared_edge(self):
        a = Rect(0, 0, 1920, 1080)
        b = Rect(1920, 1080, 3840, 2160)  # touches only at a corner
        self.assertIsNone(map_crossing([a, b], 0, 1920, 500))

    def test_gap_between_neighbours_picks_the_nearest(self):
        tall = Rect(0, 0, 1000, 3000)
        upper = Rect(1000, 0, 2000, 1000)
        lower = Rect(1000, 2100, 2000, 3000)
        x, y, target = map_crossing([tall, upper, lower], 0, 1000, 1200)  # 40% of the pair span
        self.assertEqual((target, y), (1, 999))  # 1200 falls in the gap; the upper one is nearer


if __name__ == "__main__":
    unittest.main()
