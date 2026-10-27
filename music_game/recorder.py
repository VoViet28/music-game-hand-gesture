"""Record note events, replay them, and export standard WAV/MIDI files."""

from __future__ import annotations

import json
import math
import struct
import wave
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from .gestures import Gesture


MIDI_NOTES = {
    Gesture.FIST: 60,
    Gesture.POINT: 62,
    Gesture.PEACE: 64,
    Gesture.THREE: 65,
    Gesture.PALM: 67,
    Gesture.ROCK: 69,
    Gesture.THUMBS_UP: 71,
}


@dataclass(frozen=True)
class NoteEvent:
    gesture: Gesture
    start: float
    duration: float
    octave: int
    instrument: str


def _varlen(value: int) -> bytes:
    value = max(0, value)
    parts = [value & 0x7F]
    value >>= 7
    while value:
        parts.insert(0, 0x80 | (value & 0x7F))
        value >>= 7
    return bytes(parts)


def _write_midi(events: list[NoteEvent], path: Path) -> None:
    # Format 0, 480 ticks/quarter; tempo 500000 us/quarter => 960 ticks/sec.
    timeline: list[tuple[int, int, bytes]] = [(0, 0, b"\xff\x51\x03\x07\xa1\x20")]
    for note in events:
        pitch = MIDI_NOTES[note.gesture] + 12 * note.octave
        start_tick = round(note.start * 960)
        end_tick = round((note.start + max(note.duration, 0.05)) * 960)
        timeline.append((start_tick, 1, bytes((0x90, pitch, 100))))
        timeline.append((end_tick, 0, bytes((0x80, pitch, 0))))
    timeline.sort(key=lambda item: (item[0], item[1]))
    track = bytearray()
    previous = 0
    for tick, _, message in timeline:
        track.extend(_varlen(tick - previous))
        track.extend(message)
        previous = tick
    track.extend(b"\x00\xff\x2f\x00")
    path.write_bytes(
        b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
        + b"MTrk" + struct.pack(">I", len(track)) + track
    )


def _write_wav(events: list[NoteEvent], path: Path, sample_rate: int = 44_100) -> None:
    from .audio import FREQUENCIES, synthesize_note

    length = max((note.start + note.duration for note in events), default=0.0) + 0.18
    mix = np.zeros(max(1, math.ceil(length * sample_rate)), dtype=np.float32)
    for note in events:
        start = round(note.start * sample_rate)
        frequency = FREQUENCIES[note.gesture] * (2.0 ** note.octave)
        samples = synthesize_note(frequency, note.duration, sample_rate, note.instrument)
        end = min(start + len(samples), len(mix))
        mix[start:end] += samples[: end - start]
    if np.max(np.abs(mix)) > 0:
        mix /= max(1.0, float(np.max(np.abs(mix))) / 0.9)
    pcm = (np.clip(mix, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


class PerformanceRecorder:
    def __init__(self) -> None:
        self.recording = False
        self.started_at = 0.0
        self.notes: list[NoteEvent] = []
        self._active: dict[str, tuple[Gesture, float, int, str]] = {}
        self.last_saved: tuple[Path, Path, Path] | None = None

    def start(self, now: float) -> None:
        self.recording = True
        self.started_at = now
        self.notes = []
        self._active.clear()

    def note_on(
        self, voice: str, gesture: Gesture, now: float, octave: int, instrument: str
    ) -> None:
        if not self.recording:
            return
        self.note_off(voice, now)
        self._active[voice] = (gesture, now, octave, instrument)

    def note_off(self, voice: str, now: float) -> None:
        active = self._active.pop(voice, None)
        if active is None:
            return
        gesture, start, octave, instrument = active
        self.notes.append(
            NoteEvent(
                gesture,
                max(0.0, start - self.started_at),
                max(0.05, now - start),
                octave,
                instrument,
            )
        )

    def stop(self, now: float, directory: Path) -> tuple[Path, Path, Path] | None:
        if not self.recording:
            return None
        for voice in tuple(self._active):
            self.note_off(voice, now)
        self.recording = False
        if not self.notes:
            return None
        directory.mkdir(parents=True, exist_ok=True)
        base = datetime.now().strftime("music-game-%Y%m%d-%H%M%S-%f")
        json_path = directory / f"{base}.json"
        wav_path = directory / f"{base}.wav"
        midi_path = directory / f"{base}.mid"
        json_path.write_text(
            json.dumps([asdict(note) for note in self.notes], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _write_wav(self.notes, wav_path)
        _write_midi(self.notes, midi_path)
        self.last_saved = (json_path, wav_path, midi_path)
        return self.last_saved

