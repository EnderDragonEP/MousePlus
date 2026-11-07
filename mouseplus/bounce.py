"""Overscroll bounce (experimental): when scrolling hits the end of a page, the window
springs a few pixels past the edge and back.

Pure Python so it can be unit-tested. Windows has no general way to tell another
program that an app's content hit its edge, so this only works where the window
under the cursor uses classic Windows scrollbars (GetScrollInfo); the hook decides
that and moves the window.
"""
import math
from dataclasses import dataclass

AMPLITUDE = 12    # pixels at 100% scaling
DURATION = 0.25   # seconds out and back


def at_edge(direction: int, pos: int, minimum: int, maximum: int, page: int) -> bool:
    """Whether a classic scrollbar can't move further. `direction` < 0 scrolls down
    (wheel toward you), > 0 scrolls up. A bar with nothing to scroll is never at an edge."""
    last = maximum - max(page, 1) + 1  # the highest position the bar can reach
    if last <= minimum:
        return False
    return pos >= last if direction < 0 else pos <= minimum


def offset(elapsed: float, amplitude: float = AMPLITUDE, duration: float = DURATION) -> int:
    """Window offset in pixels: out fast (peak at a quarter of the time), back softly, 0 at both ends."""
    if elapsed <= 0 or elapsed >= duration:
        return 0
    return round(amplitude * math.sin(math.pi * math.sqrt(elapsed / duration)))


@dataclass
class Bounce:
    """One bounce of a window: where it was, which way it goes and when it started."""
    window: int
    x: int
    y: int
    direction: int     # -1 moves the window up (scrolled down at the bottom), +1 moves it down
    amplitude: float
    start: float

    def position(self, now: float):
        """The window's top-left for this frame, or None when the bounce is over."""
        elapsed = now - self.start
        if elapsed >= DURATION:
            return None
        return self.x, self.y + self.direction * offset(elapsed, self.amplitude)
