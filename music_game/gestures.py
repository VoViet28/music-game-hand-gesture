"""Geometry-based hand gesture classification.

MediaPipe supplies 21 normalized landmarks.  This module deliberately owns the
classification logic so the project can explain the full path from landmarks
to an application event without relying on a pre-trained gesture model.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import acos, degrees, sqrt
from typing import Any, Sequence


class Gesture(str, Enum):
    PALM = "PALM"
    FIST = "FIST"
    PEACE = "PEACE"
    THREE = "THREE"
    POINT = "POINT"
    ROCK = "ROCK"
    THUMBS_UP = "THUMBS UP"
    UNKNOWN = "UNKNOWN"


PLAYABLE_GESTURES: tuple[Gesture, ...] = (
    Gesture.FIST,
    Gesture.POINT,
    Gesture.PEACE,
    Gesture.THREE,
    Gesture.PALM,
    Gesture.ROCK,
    Gesture.THUMBS_UP,
)


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class GestureResult:
    gesture: Gesture
    confidence: float
    fingers: tuple[bool, bool, bool, bool, bool]


def _distance(a: Point, b: Point) -> float:
    return sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def _angle(a: Point, b: Point, c: Point) -> float:
    """Return angle ABC in degrees, protected against degenerate vectors."""
    ba = (a.x - b.x, a.y - b.y, a.z - b.z)
    bc = (c.x - b.x, c.y - b.y, c.z - b.z)
    ba_len = sqrt(sum(v * v for v in ba))
    bc_len = sqrt(sum(v * v for v in bc))
    if ba_len < 1e-9 or bc_len < 1e-9:
        return 0.0
    cosine = sum(x * y for x, y in zip(ba, bc)) / (ba_len * bc_len)
    return degrees(acos(max(-1.0, min(1.0, cosine))))


class HandGestureClassifier:
    """Recognize seven explainable poses from MediaPipe hand landmarks.

    Finger extension is determined from joint straightness plus fingertip reach
    relative to the wrist.  All thresholds use ratios, not pixels, so moving the
    hand toward the camera does not change the result.
    """

    # MediaPipe landmark indices: (MCP, PIP, DIP, TIP)
    _FINGERS = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))

    def __init__(self, calibration: Any = None) -> None:
        self.calibration = calibration

    def feature_vector(self, landmarks: Sequence[Point]) -> tuple[float, ...]:
        if len(landmarks) != 21:
            raise ValueError(f"Expected 21 hand landmarks, received {len(landmarks)}")
        wrist = landmarks[0]
        palm_size = max(_distance(wrist, landmarks[9]), 1e-6)
        scores = []
        for mcp, pip, dip, tip in self._FINGERS:
            pip_angle = _angle(landmarks[mcp], landmarks[pip], landmarks[dip])
            dip_angle = _angle(landmarks[pip], landmarks[dip], landmarks[tip])
            reach_ratio = _distance(wrist, landmarks[tip]) / max(
                _distance(wrist, landmarks[pip]), 1e-6
            )
            scores.append(min(pip_angle / 160.0, dip_angle / 155.0, reach_ratio / 1.08))
        thumb_angle = _angle(landmarks[2], landmarks[3], landmarks[4])
        thumb_reach = _distance(landmarks[4], landmarks[9]) / palm_size
        thumb_score = min(thumb_angle / 150.0, thumb_reach / 0.92)
        thumb_rise = (landmarks[2].y - landmarks[4].y) / palm_size
        return (*scores, thumb_score, thumb_rise)

    def classify(self, landmarks: Sequence[Point]) -> GestureResult:
        features = self.feature_vector(landmarks)
        extended = [score >= 1.0 for score in features[:4]]
        thumb_score, thumb_rise = features[4], features[5]
        thumb_extended = thumb_score >= 1.0

        # A thumbs-up needs a vertical thumb and folded fingers.  Comparing with
        # palm size makes this invariant to resolution and camera distance.
        is_thumb_up = thumb_extended and thumb_rise > 0.42 and not any(extended)

        gesture = self.classify_pattern(tuple(extended), thumb_extended, is_thumb_up)
        calibrated = self.calibration.predict(features) if self.calibration is not None else None
        if calibrated is not None:
            gesture, confidence = calibrated
            return GestureResult(gesture, confidence, (thumb_extended, *extended))
        if gesture is Gesture.UNKNOWN:
            confidence = 0.0
        else:
            separation = min([abs(score - 1.0) for score in features[:5]])
            confidence = min(0.99, 0.68 + separation * 0.55)

        return GestureResult(
            gesture=gesture,
            confidence=round(confidence, 3),
            fingers=(thumb_extended, *extended),
        )

    @staticmethod
    def classify_pattern(
        fingers: tuple[bool, bool, bool, bool],
        thumb_extended: bool,
        thumb_up: bool = False,
    ) -> Gesture:
        """Map (index, middle, ring, pinky) states to an application gesture."""
        index, middle, ring, pinky = fingers
        if thumb_up:
            return Gesture.THUMBS_UP
        if all(fingers):
            return Gesture.PALM
        if not any(fingers) and not thumb_extended:
            return Gesture.FIST
        if index and middle and not ring and not pinky:
            return Gesture.PEACE
        if index and middle and ring and not pinky:
            return Gesture.THREE
        if index and not middle and not ring and not pinky:
            return Gesture.POINT
        if index and not middle and not ring and pinky:
            return Gesture.ROCK
        return Gesture.UNKNOWN
