"""Proportional cursor movement between monitors.

Pure Python (rectangles in, points out) so it can be unit-tested. When the cursor
leaves a monitor, it lands on the neighbouring monitor at the same fraction of the
shared edge instead of at the same pixel row: leaving a monitor halfway down puts it
halfway down the next one, and there are no dead zones where monitors only partly
overlap. Coordinates are physical pixels; right and bottom are exclusive, like RECT.
"""
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

_TOUCH = 2  # px: edges this close count as touching


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom


def monitor_at(monitors: Sequence[Rect], x: int, y: int) -> Optional[int]:
    for i, m in enumerate(monitors):
        if m.contains(x, y):
            return i
    return None


# For each edge: (along-axis span, position on the boundary line for the source side and target side)
_EDGES = {
    "right": (lambda m: (m.top, m.bottom), lambda m: m.right, lambda m: m.left),
    "left": (lambda m: (m.top, m.bottom), lambda m: m.left, lambda m: m.right),
    "bottom": (lambda m: (m.left, m.right), lambda m: m.bottom, lambda m: m.top),
    "top": (lambda m: (m.left, m.right), lambda m: m.top, lambda m: m.bottom),
}


def crossed_edge(m: Rect, x: int, y: int) -> Optional[str]:
    if x >= m.right:
        return "right"
    if x < m.left:
        return "left"
    if y >= m.bottom:
        return "bottom"
    if y < m.top:
        return "top"
    return None


def _overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _union(spans) -> Tuple[int, int]:
    spans = list(spans)
    return min(s[0] for s in spans), max(s[1] for s in spans)


def edge_groups(monitors: Sequence[Rect], source: int, edge: str):
    """The monitors on each side of the boundary the cursor crosses, linked by overlap.

    Starting from the source monitor, collect the monitors across the line that overlap
    it, then the monitors on the source side that overlap those, and so on. Mapping the
    whole group spans onto each other keeps a round trip landing where it started.
    """
    span, src_line, dst_line = _EDGES[edge]
    line = src_line(monitors[source])
    same_side = [i for i, m in enumerate(monitors) if abs(src_line(m) - line) <= _TOUCH]
    other_side = [i for i, m in enumerate(monitors) if abs(dst_line(m) - line) <= _TOUCH]
    src, dst = {source}, set()
    while True:
        src_span = _union(span(monitors[i]) for i in src)
        new_dst = {i for i in other_side if _overlaps(span(monitors[i]), src_span)}
        if not new_dst:
            return src, set()
        dst_span = _union(span(monitors[i]) for i in new_dst)
        new_src = {i for i in same_side if _overlaps(span(monitors[i]), dst_span)} | src
        if new_src == src and new_dst == dst:
            return src, dst
        src, dst = new_src, new_dst


def map_crossing(monitors: Sequence[Rect], source: int, x: int, y: int) -> Optional[Tuple[int, int, int]]:
    """Where the cursor should land when a move to (x, y) leaves monitor `source`.

    Returns (x, y, target monitor index), or None to let Windows handle the move
    (the point is still inside, or nothing borders that edge).
    """
    edge = crossed_edge(monitors[source], x, y)
    if edge is None:
        return None
    src, dst = edge_groups(monitors, source, edge)
    if not dst:
        return None
    span = _EDGES[edge][0]
    vertical = edge in ("left", "right")
    along = y if vertical else x

    lo, hi = _union(span(monitors[i]) for i in src)
    fraction = min(max((along - lo) / (hi - lo), 0.0), 1.0)
    t_lo, t_hi = _union(span(monitors[i]) for i in dst)
    target_along = t_lo + fraction * (t_hi - t_lo)

    def distance(i):
        a, b = span(monitors[i])
        return 0 if a <= target_along < b else min(abs(target_along - a), abs(target_along - (b - 1)))

    target = min(sorted(dst), key=distance)
    m = monitors[target]
    a, b = span(m)
    target_along = min(max(int(target_along), a), b - 1)

    # Keep how far the move went past the edge, so motion stays continuous.
    if edge == "right":
        cross = m.left + min(x - monitors[source].right, m.right - m.left - 1)
    elif edge == "left":
        cross = m.right - 1 - min(monitors[source].left - 1 - x, m.right - m.left - 1)
    elif edge == "bottom":
        cross = m.top + min(y - monitors[source].bottom, m.bottom - m.top - 1)
    else:
        cross = m.bottom - 1 - min(monitors[source].top - 1 - y, m.bottom - m.top - 1)
    return (target_along, cross, target) if not vertical else (cross, target_along, target)
