"""Pure, testable game rules for the gesture rhythm challenge."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .gestures import Gesture, PLAYABLE_GESTURES


@dataclass(frozen=True)
class GameEvent:
    correct: bool
    points_delta: int
    message: str


@dataclass
class RhythmChallenge:
    rounds: int = 12
    seconds_per_round: float = 5.0
    seed: int | None = None
    score: int = field(default=0, init=False)
    streak: int = field(default=0, init=False)
    best_streak: int = field(default=0, init=False)
    completed: int = field(default=0, init=False)
    misses: int = field(default=0, init=False)
    target: Gesture = field(init=False)
    deadline: float = field(default=0.0, init=False)
    finished: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._bag: list[Gesture] = []
        self.target = self._next_target()

    def start(self, now: float) -> None:
        self.score = self.streak = self.best_streak = self.completed = self.misses = 0
        self.finished = False
        self._bag.clear()
        self.target = self._next_target()
        self.deadline = now + self.seconds_per_round

    def submit(self, gesture: Gesture, now: float) -> GameEvent | None:
        if self.finished or gesture is Gesture.UNKNOWN:
            return None
        if gesture == self.target:
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            delta = 100 + min(self.streak - 1, 5) * 20
            self.score += delta
            self.completed += 1
            event = GameEvent(True, delta, f"PERFECT +{delta}")
            self._advance(now)
            return event

        self.streak = 0
        self.score = max(0, self.score - 25)
        return GameEvent(False, -25, "TRY AGAIN -25")

    def tick(self, now: float) -> GameEvent | None:
        if self.finished or self.deadline <= 0 or now < self.deadline:
            return None
        self.streak = 0
        self.misses += 1
        self.completed += 1
        event = GameEvent(False, 0, "TIME OUT")
        self._advance(now)
        return event

    def progress(self, now: float) -> float:
        if self.finished or self.deadline <= 0:
            return 0.0
        remaining = max(0.0, self.deadline - now)
        return min(1.0, remaining / self.seconds_per_round)

    def _advance(self, now: float) -> None:
        if self.completed >= self.rounds:
            self.finished = True
            self.deadline = 0.0
            return
        self.target = self._next_target(exclude=self.target)
        self.deadline = now + self.seconds_per_round

    def _next_target(self, exclude: Gesture | None = None) -> Gesture:
        """Draw from a shuffled scale so every note appears before repeats."""
        if not self._bag:
            self._bag = list(PLAYABLE_GESTURES)
            self._rng.shuffle(self._bag)
        if exclude is not None and self._bag[-1] is exclude and len(self._bag) > 1:
            self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
        return self._bag.pop()
