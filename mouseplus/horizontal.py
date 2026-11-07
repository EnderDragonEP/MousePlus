"""Decision logic for horizontal scrolling.

Pure Python (no Win32 or Qt) so it can be unit-tested. The mouse hook feeds it
X-button and wheel events; it answers whether to swallow the original event and
what to inject instead.
"""
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

BACK = 1     # XBUTTON1
FORWARD = 2  # XBUTTON2

Action = Optional[Tuple[str, int]]  # None | ("hwheel", delta) | ("click", button)
Result = Tuple[bool, Action]        # (swallow original event, action to perform)

PASS: Result = (False, None)
SWALLOW: Result = (True, None)


@dataclass(frozen=True)
class Settings:
    buttons: frozenset = frozenset({BACK, FORWARD})
    toggle_mode: bool = False
    skip_fullscreen: bool = True
    reverse: bool = False
    speed: float = 1.0


class Engine:
    """Hold mode: rolling the wheel while a trigger is held scrolls horizontally;
    a click without scrolling is replayed so Back/Forward keep working.

    Toggle mode: a click latches horizontal scrolling on/off; hold + scroll still
    works for one-off use and leaves the latch alone.
    """

    def __init__(self, is_fullscreen: Callable[[], bool] = lambda: False,
                 on_latched: Callable[[bool], None] = lambda on: None):
        self.is_fullscreen = is_fullscreen
        self.on_latched = on_latched
        self.settings = Settings()
        self.held = 0          # trigger button currently held, 0 = none
        self.scrolled = False  # wheel was used during the current hold
        self.latched = False   # toggle mode: horizontal scrolling is latched on

    def apply(self, settings: Settings):
        self.settings = settings
        if not settings.toggle_mode:
            self.set_latched(False)

    def reset(self):
        self.held = 0
        self.scrolled = False
        self.set_latched(False)

    def set_latched(self, on: bool):
        if self.latched != on:
            self.latched = on
            self.on_latched(on)

    def x_down(self, button: int) -> Result:
        if button not in self.settings.buttons:
            return PASS
        if self.held and self.held != button:  # the other X button while one is held
            return PASS
        if self._fullscreen_blocked():
            return PASS
        # Pressing the held button again means its "up" was lost; start a new hold.
        self.held, self.scrolled = button, False
        return SWALLOW

    def x_up(self, button: int) -> Result:
        if button != self.held:
            return PASS
        self.held = 0
        if self.scrolled:
            return SWALLOW
        if self.settings.toggle_mode:
            self.set_latched(not self.latched)
            return SWALLOW
        return True, ("click", button)

    def wheel(self, delta: int) -> Result:
        if not delta:
            return PASS
        if self.held:
            self.scrolled = True
        elif self.latched and self.settings.toggle_mode:
            if self._fullscreen_blocked():
                return PASS
        else:
            return PASS
        return True, ("hwheel", self.horizontal(delta))

    def horizontal(self, delta: int) -> int:
        """Map a vertical wheel delta to a horizontal one.

        Wheel down (negative delta) scrolls right (positive), like Shift+wheel.
        """
        s = self.settings
        h = delta * s.speed
        if not s.reverse:
            h = -h
        out = int(round(h))
        return out if out else (1 if h > 0 else -1)

    def _fullscreen_blocked(self) -> bool:
        if self.settings.skip_fullscreen and self.is_fullscreen():
            self.set_latched(False)
            return True
        return False
