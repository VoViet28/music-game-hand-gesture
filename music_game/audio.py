"""Low-latency, sustained procedural notes for live play and WAV export."""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

from .gestures import Gesture


FREQUENCIES = {
    Gesture.FIST: 261.63,
    Gesture.POINT: 293.66,
    Gesture.PEACE: 329.63,
    Gesture.THREE: 349.23,
    Gesture.PALM: 392.00,
    Gesture.ROCK: 440.00,
    Gesture.THUMBS_UP: 493.88,
}

INSTRUMENTS = ("Piano", "Bell", "Synth")


def _wave(frequency: float, t: np.ndarray, instrument: str) -> np.ndarray:
    phase = 2.0 * np.pi * frequency * t
    if instrument == "Bell":
        return (np.sin(phase) + 0.33 * np.sin(2 * phase)
                + 0.16 * np.sin(4 * phase)) / 1.49
    if instrument == "Synth":
        return (np.sin(phase) + 0.40 * np.sin(2 * phase)
                + 0.20 * np.sin(3 * phase)) / 1.60
    return (np.sin(phase) + 0.20 * np.sin(2 * phase)
            + 0.08 * np.sin(3 * phase)) / 1.28


def synthesize_note(
    frequency: float, duration: float, sample_rate: int, instrument: str
) -> np.ndarray:
    """One note with a short release tail, returned as normalized float samples."""
    duration = max(0.05, duration)
    release = 0.10
    t = np.arange(int((duration + release) * sample_rate)) / sample_rate
    signal = _wave(frequency, t, instrument)
    attack = np.minimum(1.0, t / 0.020)
    tail = np.clip((duration + release - t) / release, 0.0, 1.0)
    if instrument == "Piano":
        envelope = np.exp(-0.38 * t)
    elif instrument == "Bell":
        envelope = np.exp(-0.60 * t)
    else:
        envelope = np.ones_like(t)
    return (signal * attack * tail * envelope * 0.55).astype(np.float32)


def _loop_samples(frequency: float, sample_rate: int, instrument: str) -> np.ndarray:
    # Integer fundamental cycles make the loop boundary continuous.
    cycles = max(1, round(frequency * 0.25))
    count = max(1, round(cycles * sample_rate / frequency))
    t = np.arange(count) / sample_rate
    exact_frequency = cycles * sample_rate / count
    wave = _wave(exact_frequency, t, instrument) * 0.55
    return (np.clip(wave, -1.0, 1.0) * 32767).astype(np.int16)


@dataclass
class AudioEngine:
    sample_rate: int = 44_100
    volume: float = 0.55
    buffer_size: int = 512
    instrument: str = "Piano"

    def __post_init__(self) -> None:
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        self.available = False
        self.error = ""
        self._active: dict[str, object] = {}
        self._sounds: dict[tuple[Gesture, int, str], object] = {}
        self._pygame = None
        try:
            import pygame

            pygame.mixer.init(
                frequency=self.sample_rate,
                size=-16,
                channels=2,
                buffer=self.buffer_size,
            )
            pygame.mixer.set_num_channels(16)
            self._pygame = pygame
            self.available = True
        except Exception as exc:
            self.error = str(exc)

    def _sound(self, gesture: Gesture, octave: int, instrument: str):
        key = (gesture, octave, instrument)
        if key not in self._sounds:
            frequency = FREQUENCIES[gesture] * (2.0 ** octave)
            pcm = _loop_samples(frequency, self.sample_rate, instrument)
            stereo = np.ascontiguousarray(np.column_stack((pcm, pcm)))
            self._sounds[key] = self._pygame.sndarray.make_sound(stereo)
        return self._sounds[key]

    def note_on(
        self, voice: str, gesture: Gesture, octave: int = 0,
        instrument: str | None = None,
    ) -> bool:
        if not self.available or gesture not in FREQUENCIES:
            return False
        self.note_off(voice)
        sound = self._sound(gesture, octave, instrument or self.instrument)
        channel = self._pygame.mixer.find_channel(force=True)
        if channel is None:
            return False
        channel.play(sound, loops=-1, fade_ms=25)
        channel.set_volume(self.volume)
        self._active[voice] = channel
        return True

    def note_off(self, voice: str) -> None:
        channel = self._active.pop(voice, None)
        if channel is not None:
            channel.fadeout(90)

    def all_notes_off(self) -> None:
        for voice in tuple(self._active):
            self.note_off(voice)

    def play(self, gesture: Gesture) -> bool:
        """Compatibility method for a short note."""
        if not self.available or gesture not in FREQUENCIES:
            return False
        frequency = FREQUENCIES[gesture]
        pcm = synthesize_note(frequency, 0.34, self.sample_rate, self.instrument)
        stereo = np.ascontiguousarray(np.column_stack((pcm, pcm)) * 32767, dtype=np.int16)
        self._pygame.sndarray.make_sound(stereo).play()
        return True

    def set_muted(self, muted: bool) -> None:
        if self.available and muted:
            self._pygame.mixer.stop()
            self._active.clear()

    def close(self) -> None:
        if self.available:
            self._pygame.mixer.quit()
