"""Scroll Inertia: after a fast flick, the wheel keeps going like a free-spinning wheel.

Pure Python with the clock passed in, so it can be unit-tested frame by frame.
Every notch goes out whole and at once, like a normal wheel. After a fast flick (several notches
in quick succession) the motion glides on in whole notches that come fast at first and then
slower, the way a free-spinning wheel sends them, so apps that react to every wheel event get
nothing but whole notches. Browsers animate each notch themselves, so it still looks smooth.
- Short, Medium and Long glides slow down exponentially, like a touchpad.
- Free spin coasts like a heavy free-spinning wheel: constant friction plus a little drag, so a
  hard flick keeps going for seconds before it stops.
A glide starts at a speed set by the flick's pace (boosted for hard flicks in Free spin) and the
inertia multiplier, which is eased in over a moment so the glide never jerks. Each further notch
the same way spins it faster. It ends once its notches would come so far apart that they'd read
as a stutter, the way friction stops a wheel once it's slow.
Distances are wheel-delta units (120 = one notch).
"""
import math
from collections import deque
from dataclasses import dataclass

NOTCH = 120
GLIDES = {"short": 0.22, "medium": 0.38, "long": 0.60}  # friction time constant of the glide, seconds

FRAME = 1 / 120         # seconds between frames
_FLICK_WINDOW = 0.15    # notches this close together make a flick (how many: SmoothSettings.flick)
_FLICK_END = 0.05       # a flick is over when no notch came for this long
_MAX_GLIDE = 4.0        # seconds: a glide never runs longer
_MAX_DT = 0.05          # a late frame never jumps more than this
_RAMP = 0.06            # seconds to ease the inertia multiplier in at the start of a glide
_NOTCH_GAP = 0.125      # a glide ends once its notches would come further apart than this
_PACE_SHARE = 0.55      # a glide starts at this share of the flick's pace...
_LEAST_SPEED = 2.0 * NOTCH / _NOTCH_GAP  # ...but at least this fast, so even a gentle flick glides a little
_CONTRAST_FROM = 40 * NOTCH  # flicks faster than this (units per second) get the flick contrast boost
CONTRASTS = (0.0, 0.5, 1.0, 1.5)  # flick contrast Off, Low, Medium, High: the boost's power
# Free spin slows down like a heavy wheel: dv/dt = -(_SPIN_FRICTION + _SPIN_DRAG * v).
_SPIN_FRICTION = 300.0  # units per second, every second
_SPIN_DRAG = 0.35       # per second
_SPIN_REF = 3000.0      # a flick at this pace (25 notches a second) spins at exactly its pace;
_SPIN_BOOST = (0.75, 2.5)  # slower and faster flicks get this range of square-root boost
_SPIN_PUSH = 0.25       # a notch during a glide adds its distance, spread over this many seconds, as speed
_MAX_SPIN = 10.0        # seconds a free spin may run after its last push


@dataclass(frozen=True)
class SmoothSettings:
    glide: float = GLIDES["medium"]
    free_spin: bool = False   # glide like a free-spinning wheel instead (`glide` is then unused)
    momentum: float = 1.0     # inertia multiplier: how fast (and so how far) a flick glides
    flick: int = 3            # quick notches (within _FLICK_WINDOW) that make a flick
    contrast: float = 0.0     # how much farther than in proportion a fast flick goes (one of CONTRASTS)
    brake: bool = True        # turning the wheel back during a glide only stops it
    carry: bool = False       # a glide goes on in the next window the cursor moves to (played by the hook)
    bounce: bool = False      # experimental overscroll bounce (played by the hook, not here)


class SmoothScroller:
    def __init__(self, settings: SmoothSettings = SmoothSettings()):
        self.settings = settings
        self.stop()

    def stop(self):
        self.remaining = 0.0     # notch distance to send with the next frame
        self.velocity = 0.0      # glide speed in units per second; 0 when not gliding
        self.carry = 0.0         # part of a notch the glide hasn't sent yet
        self.notches = deque()   # (time, distance) of the recent notches
        self.last = None         # time of the previous frame
        self.watching = 0        # direction of notches just sent, watched to see whether they were a flick
        self.glide_start = 0.0   # when the glide's slowdown started (a push restarts it)
        self.boost_start = 0.0   # when its speed started easing from glide_base to glide_target
        self.glide_base = 0.0    # the speed the glide started at: set by the flick's pace
        self.glide_target = 0.0  # the speed it eases to: with the inertia multiplier

    @property
    def active(self) -> bool:
        return bool(self.remaining or self.velocity or self.watching)

    @property
    def gliding(self) -> bool:
        return bool(self.velocity)

    @property
    def direction(self) -> int:
        motion = self.velocity or self.remaining or self.watching
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
            self.last = now - FRAME
        if self.velocity:
            self._push(delta, now)  # spin the wheel faster
        else:
            self.remaining += delta
            self.watching = sign
        self.notches.append((now, abs(delta)))
        while now - self.notches[0][0] > _FLICK_WINDOW:
            self.notches.popleft()

    def frame(self, now: float) -> int:
        """The units to send for this frame (0 when there's nothing to send)."""
        if not self.active:
            return 0
        dt = min(max(now - self.last, 0.0), _MAX_DT)
        self.last = now
        if self.velocity:
            return self._emit_notches(self._glide_step(dt, now))
        step, self.remaining = self.remaining, 0.0
        if self.watching and now - self.notches[-1][0] >= _FLICK_END:  # the notches have stopped coming
            sign, self.watching = self.watching, 0
            if self._flick_ended(now):
                self._glide(sign, now)
        return round(step)

    def _glide(self, sign: int, now: float):
        """The flick is over: glide on at a speed set by its pace, easing the multiplier in."""
        raw = pace = self._pace()
        if self.settings.free_spin:  # a harder flick spins the wheel disproportionately faster
            low, high = _SPIN_BOOST
            pace *= min(max(math.sqrt(pace / _SPIN_REF), low), high)
        else:
            pace *= _PACE_SHARE
        # Flick contrast: flicks faster than _CONTRAST_FROM get disproportionately faster still;
        # slower ones are untouched.
        pace *= max(raw / _CONTRAST_FROM, 1.0) ** self.settings.contrast
        speed = sign * max(pace, _LEAST_SPEED)
        self.glide_base, self.glide_target = speed, speed * self.settings.momentum
        self.glide_start = self.boost_start = now
        self.velocity = speed

    def _pace(self) -> float:
        """How fast the flick's notches came, in units per second."""
        last = self.notches[-1][0]
        burst = [(t, distance) for t, distance in self.notches if last - t <= _FLICK_WINDOW]
        span = last - burst[0][0]
        return sum(distance for _, distance in burst[1:]) / span if span > 0 else 0.0

    def _push(self, distance: float, now: float):
        """A notch the same way during a glide: its distance, spread over _SPIN_PUSH, joins the
        current speed (times the multiplier), and the glide slows down from there."""
        speed = self._glide_speed(now) + distance / _SPIN_PUSH * self.settings.momentum
        self.glide_base = self.glide_target = speed
        self.glide_start = self.boost_start = now
        self.velocity = speed

    def _glide_speed(self, now: float) -> float:
        """The glide's speed at `now`: the multiplier eased in over _RAMP, slowing down."""
        ramp = min((now - self.boost_start) / _RAMP, 1.0)
        ramp = ramp * ramp * (3 - 2 * ramp)  # smoothstep: no sudden change of speed
        level = self.glide_base + (self.glide_target - self.glide_base) * ramp
        elapsed = now - self.glide_start
        if self.settings.free_spin:
            terminal = _SPIN_FRICTION / _SPIN_DRAG
            spin = (abs(level) + terminal) * math.exp(-_SPIN_DRAG * elapsed) - terminal
            return math.copysign(max(spin, 0.0), level)
        return level * math.exp(-elapsed / self.settings.glide)

    def _glide_step(self, dt: float, now: float) -> float:
        before = self._glide_speed(max(now - dt, self.glide_start))
        self.velocity = self._glide_speed(now)
        step = (before + self.velocity) / 2 * dt  # frames are short: the average speed is exact enough
        limit = _MAX_SPIN if self.settings.free_spin else _MAX_GLIDE
        if abs(self.velocity) < NOTCH / _NOTCH_GAP or now - self.glide_start > limit:
            self.velocity = 0.0  # notches would now come so far apart that they'd read as a stutter
        return step

    def _flick_ended(self, now: float) -> bool:
        flick = self.settings.flick
        if len(self.notches) < flick or now - self.notches[-1][0] < _FLICK_END:
            return False
        last = self.notches[-1][0]
        return sum(1 for t, _ in self.notches if last - t <= _FLICK_WINDOW) >= flick

    def _emit_notches(self, step: float) -> int:
        """A glide goes out in whole notches; at its end, what's left rounds to a notch or nothing."""
        self.carry += step
        if self.velocity:
            whole = int(self.carry / NOTCH) * NOTCH  # toward zero
            self.carry -= whole
        else:
            whole = round(self.carry / NOTCH) * NOTCH
            self.carry = 0.0
        return whole
