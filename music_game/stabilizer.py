"""Temporal filtering so a pose produces one clean musical event."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field

from .gestures import Gesture


@dataclass
class GestureStabilizer:
    window_size: int = 7
    votes_required: int = 5
    release_frames: int = 3
    cooldown_seconds: float = 0.35
    history: deque[Gesture] = field(init=False)
    latched: Gesture | None = field(default=None, init=False)
    unknown_run: int = field(default=0, init=False)
    last_event_time: float = field(default=-10_000.0, init=False)

    def __post_init__(self) -> None:
        if not 1 <= self.votes_required <= self.window_size:
            raise ValueError("votes_required must be between 1 and window_size")
        self.history = deque(maxlen=self.window_size)

    def update(self, gesture: Gesture, now: float) -> tuple[Gesture | None, Gesture]:
        """Return (new_event, stable_display_gesture)."""
        self.history.append(gesture)
        self.unknown_run = self.unknown_run + 1 if gesture is Gesture.UNKNOWN else 0

        if self.unknown_run >= self.release_frames:
            self.latched = None

        playable = [item for item in self.history if item is not Gesture.UNKNOWN]
        if not playable:
            return None, Gesture.UNKNOWN

        candidate, votes = Counter(playable).most_common(1)[0]
        stable = candidate if votes >= self.votes_required else Gesture.UNKNOWN
        can_fire = (
            stable is not Gesture.UNKNOWN
            and gesture is stable
            and stable != self.latched
            and now - self.last_event_time >= self.cooldown_seconds
        )
        if can_fire:
            self.latched = stable
            self.last_event_time = now
            return stable, stable
        return None, stable

    def reset(self) -> None:
        self.history.clear()
        self.latched = None
        self.unknown_run = 0
        self.last_event_time = -10_000.0
