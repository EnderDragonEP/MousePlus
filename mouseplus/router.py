"""Which feature handles a wheel event: Horizontal Scroll, Smooth Scroll or neither (pass through).

Pure Python so the precedence can be unit-tested. Checks that need Win32 (full-screen
app in front, the app or elevated window under the cursor) are passed in as callables
and only called when they matter, cheapest checks first.
"""
from dataclasses import dataclass
from typing import Callable

PASS, HORIZONTAL, SMOOTH = "pass", "horizontal", "smooth"
NOTCH = 120
MASKED = frozenset({"alt", "win"})  # releasing these after a wheel opens a menu bar or Start


@dataclass(frozen=True)
class Decision:
    route: str            # PASS, HORIZONTAL or SMOOTH
    stop: bool = False    # stop any inertia that's running
    mask: bool = False    # tap the mask key so releasing Alt/Win doesn't open a menu


@dataclass(frozen=True)
class WheelEvent:
    delta: int
    horizontal: bool       # Back/Forward held, or toggle mode latched on
    modifiers: frozenset   # held keys: "alt", "ctrl", "shift", "win"
    smooth: bool           # Smooth Scroll is on (and has something to do)
    bypass: frozenset      # keys that make the wheel pass through; empty for none


def route_wheel(event: WheelEvent, fullscreen: Callable[[], bool], elevated: Callable[[], bool],
                excluded: Callable[[], bool] = lambda: False) -> Decision:
    """First match wins:

    0. No delta at all (some drivers send these): pass untouched, without stopping anything.
    1. Back/Forward + wheel, or a latched toggle: Horizontal Scroll, unchanged.
    2. Full-screen app in front: pass.
    3. Bypass keys held: pass untouched (normal notches, the app's own Alt+wheel and so on).
    4. Ctrl held: pass. Zoom is step-based; smoothing or inertia would overshoot.
    5. Smooth Scroll off, a finer-than-notch delta (hi-res wheel, touchpad), an app on the
       list or the taskbar under the cursor (e.g. an image viewer that flips an image per
       wheel message) or an elevated window there (Windows blocks injected input): pass,
       and stop any glide, since the user now scrolls some other way.
    6. Otherwise Smooth Scroll.
    """
    if not event.delta:
        return Decision(PASS)
    if event.horizontal:
        return Decision(HORIZONTAL, stop=True)
    if fullscreen():
        return Decision(PASS, stop=True)
    if event.bypass and event.bypass <= event.modifiers:
        return Decision(PASS, stop=True, mask=bool(event.bypass & MASKED))
    if "ctrl" in event.modifiers:
        return Decision(PASS, stop=True)
    if not event.smooth or event.delta % NOTCH or excluded() or elevated():
        return Decision(PASS, stop=True)
    return Decision(SMOOTH)
