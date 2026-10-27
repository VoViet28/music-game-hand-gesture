"""Camera/video capture and MediaPipe hand landmark extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2

from .gestures import Point


@dataclass(frozen=True)
class HandObservation:
    points: tuple[Point, ...]
    handedness: str
    raw_landmarks: Any


class HandTracker:
    def __init__(
        self,
        detection_confidence: float = 0.65,
        tracking_confidence: float = 0.60,
    ) -> None:
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError(
                "MediaPipe is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self._mp = mp
        self._hands_api = mp.solutions.hands
        self._drawing = mp.solutions.drawing_utils
        self._styles = mp.solutions.drawing_styles
        self._hands = self._hands_api.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

    def process(self, frame) -> tuple[HandObservation, ...]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._hands.process(rgb)
        if not result.multi_hand_landmarks:
            return ()
        observations = []
        for index, raw in enumerate(result.multi_hand_landmarks):
            handedness = ""
            if result.multi_handedness and index < len(result.multi_handedness):
                handedness = result.multi_handedness[index].classification[0].label
            points = tuple(Point(item.x, item.y, item.z) for item in raw.landmark)
            observations.append(HandObservation(points, handedness, raw))
        return tuple(observations)

    def draw(self, frame, observations: tuple[HandObservation, ...]) -> None:
        for observation in observations:
            self._drawing.draw_landmarks(
                frame,
                observation.raw_landmarks,
                self._hands_api.HAND_CONNECTIONS,
                self._styles.get_default_hand_landmarks_style(),
                self._styles.get_default_hand_connections_style(),
            )

    def close(self) -> None:
        self._hands.close()


def parse_source(value: str) -> int | str:
    """Convert a numeric CLI source to a camera index; otherwise validate a file/URL."""
    stripped = value.strip()
    if stripped.lstrip("-").isdigit():
        return int(stripped)
    if "://" in stripped:
        return stripped
    path = Path(stripped).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Video file does not exist: {path}")
    return str(path.resolve())


def open_capture(source: int | str, width: int, height: int):
    backend = cv2.CAP_DSHOW if isinstance(source, int) else cv2.CAP_ANY
    capture = cv2.VideoCapture(source, backend)
    if isinstance(source, int):
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(
            f"Cannot open video source {source!r}. Close other camera apps or use "
            "--source PATH_TO_VIDEO."
        )
    return capture

