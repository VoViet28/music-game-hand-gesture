"""Assign hand roles and translate the second hand into sound settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, TypeVar

from .gestures import Gesture


T = TypeVar("T")


def select_hands(
    observations: Sequence[T], note_hand: str = "Right", mirrored: bool = True
) -> tuple[T | None, T | None]:
    """Return (note hand, control hand); a single visible hand always plays notes."""
    if not observations:
        return None, None
    if len(observations) == 1:
        return observations[0], None
    desired_label = note_hand if mirrored else ("Left" if note_hand == "Right" else "Right")
    matches = [hand for hand in observations if getattr(hand, "handedness", "") == desired_label]
    if len(matches) == 1:
        note = matches[0]
    else:
        # Mirroring reverses which side of the frame contains the physical hand.
        right_side = (note_hand == "Right") == mirrored
        order = max if right_side else min
        note = order(observations, key=lambda hand: hand.points[0].x)
    control = next((hand for hand in observations if hand is not note), None)
    return note, control


@dataclass
class ControlState:
    octave: int = 0
    instrument: str = "Piano"

    def apply(self, gesture: Gesture) -> str | None:
        if gesture is Gesture.FIST:
            self.octave = -1
            return "Quãng tám thấp"
        if gesture is Gesture.POINT:
            self.octave = 0
            return "Quãng tám chuẩn"
        if gesture is Gesture.PALM:
            self.octave = 1
            return "Quãng tám cao"
        instrument_map = {
            Gesture.PEACE: "Piano",
            Gesture.THREE: "Bell",
            Gesture.ROCK: "Synth",
        }
        if gesture in instrument_map:
            self.instrument = instrument_map[gesture]
            return f"Nhạc cụ: {self.instrument}"
        return None

