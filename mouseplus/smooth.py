"""Smooth scrolling and inertia for wheel notches.

Pure Python with the clock passed in, so it can be unit-tested frame by frame.
Each notch adds its distance to a target that is played out with exponential
easing (small steps, quick start, soft end). After a fast flick (several notches
in quick succession) the motion turns into a glide that starts at the speed the
easing has at that moment and slows down with friction, like a touchpad: the
harder the flick, the more distance is queued, the faster and longer the glide.
The inertia multiplier scales the glide's speed (and so its distance); the change
is eased in over a moment so the glide never jerks.
Distances are wheel-delta units (120 = one notch).
"""
import math
from collections import deque
from dataclasses import dataclass

NOTCH = 120
DURATIONS = {"fast": 0.12, "normal": 0.20, "slow": 0.32}  # seconds to play out about 95% of a notch
GLIDES = {"short": 0.22, "medium": 0.38, "long": 0.60}    # friction time constant of the glide, seconds

FRAME = 1 / 120         # seconds between frames
_FLICK_NOTCHES = 3      # this many notches...
_FLICK_WINDOW = 0.15    # ...within this many seconds make a flick (about 20 notches a second)
_FLICK_END = 0.05       # a flick is over when no notch came for this long
_MIN_SPEED = 120.0      # units per second (one unit a frame): slower glides stop
_MAX_GLIDE = 4.0        # seconds: a glide never runs longer
_MAX_DT = 0.05          # a late frame never jumps more than this
_RAMP = 0.06            # seconds to ease the inertia multiplier in at the start of a glide


@dataclass(frozen=True)
class SmoothSettings:
    animate: bool = True      # play each notch out in small steps
    duration: float = DURATIONS["normal"]
    distance: float = 1.0     # multiplier for each notch
    inertia: bool = True      # a fast flick keeps going
    glide: float = GLIDES["medium"]
    momentum: float = 1.0     # inertia multiplier: how fast (and so how far) a flick glides
    brake: bool = True        # turning the wheel back during a glide only stops it
    bounce: bool = False      # experimental overscroll bounce (played by the hook, not here)


class SmoothScroller:
    def __init__(self, settings: SmoothSettings = SmoothSettings()):
        self.settings = settings
        self.stop()

    def stop(self):
        self.remaining = 0.0   # distance still to play out from notches
        self.velocity = 0.0    # glide speed in units per second; 0 while easing
        self.carry = 0.0       # fraction of a unit not sent yet
        self.notches = deque()
        self.last = None       # time of the previous frame
        self.glide_start = 0.0
        self.glide_base = 0.0  # the easing's speed when the glide took over

    @property
    def active(self) -> bool:
        return bool(self.remaining or self.velocity)

    @property
    def gliding(self) -> bool:
        return bool(self.velocity)

    @property
    def direction(self) -> int:
        motion = self.velocity or self.remaining
        return (motion > 0) - (motion < 0)

    def add(self, delta: int, now: float):
        """A wheel notch arrived. Turning the wheel the other way stops the motion at once;
        during a glide (with `brake` on) that notch only stops it and doesn't scroll back."""
        sign = (delta > 0) - (delta < 0)
        if self.active and sign != self.direction:
            braked = self.gliding and self.settings.brake
            self.stop()
            if braked:
                return
        if not self.active:
            self.last = now - FRAME  # the first step goes out right away
        if self.velocity:  # a notch during a glide takes over from it
            self.remaining = self.velocity * self._tau()
            self.velocity = 0.0
        self.remaining += delta * self.settings.distance
        self.notches.append(now)
        while now - self.notches[0] > _FLICK_WINDOW:
            self.notches.popleft()

    def frame(self, now: float) -> int:
        """The whole units to send for this frame (0 when idle)."""
        if not self.active:
            return 0
        dt = min(max(now - self.last, 0.0), _MAX_DT)
        self.last = now
        step = self._glide_step(dt, now) if self.velocity else self._ease_step(dt, now)
        return self._emit(step)

    def _tau(self) -> float:
        return max(self.settings.duration, 1e-3) / 3  # exp(-3): about 5% left after `duration`

    def _ease_step(self, dt: float, now: float) -> float:
        if not self.settings.animate:
            step, self.remaining = self.remaining, 0.0
            return step
        tau = self._tau()
        step = self.remaining * (1 - math.exp(-dt / tau))
        self.remaining -= step
        if self.settings.inertia and self._flick_ended(now):
            # Glide on at the easing's current speed, so the motion stays continuous.
            self.glide_base = self.velocity = self.remaining / tau
            self.remaining = 0.0
            self.glide_start = now
        elif abs(self.remaining) < 1:
            step += self.remaining
            self.remaining = 0.0
        return step

    def _glide_speed(self, elapsed: float) -> float:
        """Speed `elapsed` seconds into the glide: the flick's speed times the inertia
        multiplier (eased in over _RAMP), slowing down with friction."""
        ramp = min(elapsed / _RAMP, 1.0)
        ramp = ramp * ramp * (3 - 2 * ramp)  # smoothstep: no sudden change of speed
        boost = 1 + (self.settings.momentum - 1) * ramp
        return self.glide_base * boost * math.exp(-elapsed / self.settings.glide)

    def _glide_step(self, dt: float, now: float) -> float:
        elapsed = now - self.glide_start
        before = self._glide_speed(max(elapsed - dt, 0.0))
        self.velocity = self._glide_speed(elapsed)
        step = (before + self.velocity) / 2 * dt  # frames are short: the average speed is exact enough
        if abs(self.velocity) < _MIN_SPEED or elapsed > _MAX_GLIDE:
            self.velocity = 0.0
        return step

    def _flick_ended(self, now: float) -> bool:
        if len(self.notches) < _FLICK_NOTCHES or now - self.notches[-1] < _FLICK_END:
            return False
        burst = [t for t in self.notches if self.notches[-1] - t <= _FLICK_WINDOW]
        return len(burst) >= _FLICK_NOTCHES

    def _emit(self, step: float) -> int:
        total = step + self.carry
        if self.active:
            whole = int(total)  # toward zero; the remainder goes out with a later frame
            self.carry = total - whole
        else:
            whole = round(total)  # the motion is over: send what's left
            self.carry = 0.0
        return whole
