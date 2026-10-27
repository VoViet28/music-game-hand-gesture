"""User-specific gesture templates derived from relative landmark geometry."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .gestures import Gesture, PLAYABLE_GESTURES


FEATURE_COUNT = 6  # Four finger extension scores, thumb score, thumb rise.


@dataclass
class GestureCalibration:
    samples: dict[Gesture, list[tuple[float, ...]]] = field(default_factory=dict)
    threshold: float = 0.42

    @property
    def complete(self) -> bool:
        return all(len(self.samples.get(gesture, [])) >= 8 for gesture in PLAYABLE_GESTURES)

    def add(self, gesture: Gesture, features: tuple[float, ...]) -> None:
        if gesture not in PLAYABLE_GESTURES or len(features) != FEATURE_COUNT:
            raise ValueError("Invalid gesture or feature vector")
        self.samples.setdefault(gesture, []).append(tuple(float(x) for x in features))

    def predict(self, features: tuple[float, ...]) -> tuple[Gesture, float] | None:
        if not self.complete:
            return None
        distances = []
        for gesture in PLAYABLE_GESTURES:
            samples = self.samples[gesture]
            mean = tuple(sum(sample[i] for sample in samples) / len(samples)
                         for i in range(FEATURE_COUNT))
            distance = (sum((a - b) ** 2 for a, b in zip(features, mean)) / FEATURE_COUNT) ** 0.5
            distances.append((distance, gesture))
        distances.sort(key=lambda item: item[0])
        best_distance, best_gesture = distances[0]
        if best_distance > self.threshold or distances[1][0] - best_distance < 0.045:
            return Gesture.UNKNOWN, 0.0
        return best_gesture, round(max(0.50, 1.0 - best_distance / self.threshold), 3)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "threshold": self.threshold,
            "samples": {gesture.value: items for gesture, items in self.samples.items()},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "GestureCalibration":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("version") != 1:
                return cls()
            samples = {
                Gesture(name): [tuple(map(float, vector)) for vector in vectors]
                for name, vectors in data.get("samples", {}).items()
                if Gesture(name) in PLAYABLE_GESTURES
            }
            if any(len(vector) != FEATURE_COUNT for vectors in samples.values() for vector in vectors):
                return cls()
            return cls(samples=samples, threshold=float(data.get("threshold", 0.42)))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return cls()


@dataclass
class CalibrationWizard:
    calibration: GestureCalibration = field(default_factory=GestureCalibration)
    index: int = 0
    collecting: bool = False
    required: int = 16

    @property
    def target(self) -> Gesture:
        return PLAYABLE_GESTURES[min(self.index, len(PLAYABLE_GESTURES) - 1)]

    @property
    def finished(self) -> bool:
        return self.index >= len(PLAYABLE_GESTURES)

    @property
    def count(self) -> int:
        return len(self.calibration.samples.get(self.target, [])) if not self.finished else self.required

    def begin_capture(self) -> None:
        if not self.finished:
            self.collecting = True

    def feed(self, features: tuple[float, ...] | None) -> bool:
        if not self.collecting or self.finished or features is None:
            return False
        self.calibration.add(self.target, features)
        if self.count >= self.required:
            self.collecting = False
            self.index += 1
            return True
        return False

