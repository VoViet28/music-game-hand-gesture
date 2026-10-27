"""Beat-based melody challenge with pitch and timing scoring."""

from __future__ import annotations

from dataclasses import dataclass, field

from .game import GameEvent
from .gestures import Gesture


MELODIES: dict[str, tuple[Gesture, ...]] = {
    "Twinkle": (
        Gesture.FIST, Gesture.FIST, Gesture.PALM, Gesture.PALM,
        Gesture.ROCK, Gesture.ROCK, Gesture.PALM,
        Gesture.THREE, Gesture.THREE, Gesture.PEACE, Gesture.PEACE,
        Gesture.POINT, Gesture.POINT, Gesture.FIST,
    ),
    "Scale": (
        Gesture.FIST, Gesture.POINT, Gesture.PEACE, Gesture.THREE,
        Gesture.PALM, Gesture.ROCK, Gesture.THUMBS_UP,
    ),
}


@dataclass
class MelodyChallenge:
    song: str = "Twinkle"
    beat_seconds: float = 1.40
    hit_window: float = 0.55
    score: int = field(default=0, init=False)
    streak: int = field(default=0, init=False)
    best_streak: int = field(default=0, init=False)
    index: int = field(default=0, init=False)
    misses: int = field(default=0, init=False)
    started_at: float = field(default=0.0, init=False)
    finished: bool = field(default=False, init=False)

    @property
    def sequence(self) -> tuple[Gesture, ...]:
        return MELODIES[self.song]

    @property
    def target(self) -> Gesture:
        return self.sequence[min(self.index, len(self.sequence) - 1)]

    @property
    def completed(self) -> int:
        return self.index

    @property
    def rounds(self) -> int:
        return len(self.sequence)

    @property
    def deadline(self) -> float:
        return self.beat_time(self.index) + self.hit_window

    def beat_time(self, index: int) -> float:
        # Two-beat count-in gives the player time to see the first note.
        return self.started_at + (index + 2) * self.beat_seconds

    def start(self, now: float) -> None:
        self.score = self.streak = self.best_streak = self.index = self.misses = 0
        self.started_at = now
        self.finished = False

    def submit(self, gesture: Gesture, now: float) -> GameEvent | None:
        if self.finished or gesture is Gesture.UNKNOWN:
            return None
        offset = now - self.beat_time(self.index)
        if offset < -self.hit_window:
            return GameEvent(False, 0, "CHỜ ĐÚNG NHỊP")
        if offset > self.hit_window:
            self.tick(now)
            return None
        if gesture is not self.target:
            self.streak = 0
            self.score = max(0, self.score - 15)
            return GameEvent(False, -15, "SAI NỐT -15")
        absolute = abs(offset)
        points = 120 if absolute <= 0.16 else 80 if absolute <= 0.34 else 45
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        self.score += points
        self.index += 1
        self.finished = self.index >= len(self.sequence)
        return GameEvent(True, points, f"ĐÚNG NHỊP +{points}")

    def tick(self, now: float) -> GameEvent | None:
        if self.finished:
            return None
        missed = 0
        while self.index < len(self.sequence) and now > self.deadline:
            self.index += 1
            self.misses += 1
            missed += 1
        if not missed:
            return None
        self.streak = 0
        self.finished = self.index >= len(self.sequence)
        return GameEvent(False, 0, "LỠ NHỊP")

    def progress(self, now: float) -> float:
        if self.finished:
            return 0.0
        return max(0.0, min(1.0, 1.0 - abs(now - self.beat_time(self.index)) / self.hit_window))

