"""Music Game application: camera, hands, instruments, challenges and export."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .audio import AudioEngine, INSTRUMENTS
from .calibration import CalibrationWizard, GestureCalibration
from .controls import ControlState, select_hands
from .game import RhythmChallenge
from .gestures import Gesture, GestureResult, HandGestureClassifier
from .launcher import choose_settings
from .melody import MELODIES, MelodyChallenge
from .recorder import NoteEvent, PerformanceRecorder
from .stabilizer import GestureStabilizer
from .ui import PANEL_WIDTH, UiState, render
from .vision import HandTracker, open_capture, parse_source


WINDOW_TITLE = "Music Game - Ban tay am nhac"
PROJECT_DIR = Path(__file__).resolve().parent.parent
CALIBRATION_FILE = PROJECT_DIR / "config" / "calibration.json"
RECORDINGS_DIR = PROJECT_DIR / "recordings"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Music Game - nhạc cụ bằng cử chỉ tay.")
    parser.add_argument("--source", default="0", help="Camera 0-3, file video hoặc URL.")
    parser.add_argument("--mode", choices=("free", "challenge", "melody"), default="free")
    parser.add_argument("--instrument", choices=INSTRUMENTS, default="Piano")
    parser.add_argument("--song", choices=tuple(MELODIES), default="Twinkle")
    parser.add_argument("--note-hand", choices=("Right", "Left"), default="Right")
    parser.add_argument("--volume", type=float, default=0.55)
    parser.add_argument("--buffer-size", type=int, choices=(256, 512, 1024), default=512)
    parser.add_argument("--sensitivity", choices=("Nhanh", "Vừa", "Ổn định"), default="Vừa")
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--no-mirror", action="store_true")
    parser.add_argument("--loop-video", action="store_true")
    parser.add_argument("--direct", action="store_true", help="Bỏ qua màn hình cài đặt.")
    parser.add_argument("--check", action="store_true", help="Kiểm tra không cần camera.")
    return parser


class VideoTimeline:
    """Pace local files to source timestamps; keep game time monotonic on loops."""

    def __init__(self, fps: float) -> None:
        self.fps = fps if 1.0 <= fps <= 240.0 else 30.0
        self.frame_number = 0
        self.offset = 0.0
        self.last_time = 0.0
        self.real_start = time.monotonic()

    def advance(self, capture) -> float:
        self.frame_number += 1
        timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if timestamp <= 0:
            timestamp = (self.frame_number - 1) / self.fps
        self.last_time = self.offset + timestamp
        # Sleep only while ahead of the recording's timeline. Processing slower
        # than real time cannot be repaired by sleeping.
        ahead = self.real_start + self.last_time - time.monotonic()
        if ahead > 0:
            time.sleep(min(ahead, 0.10))
        return self.last_time

    def loop(self) -> None:
        self.offset = self.last_time + 1.0 / self.fps
        self.frame_number = 0


class ReplayScheduler:
    def __init__(self) -> None:
        self.notes: list[NoteEvent] = []
        self.started_at = 0.0
        self.next_index = 0
        self.active: dict[str, float] = {}
        self.playing = False

    def start(self, notes: list[NoteEvent], now: float) -> bool:
        if not notes:
            return False
        self.notes = list(notes)
        self.started_at = now
        self.next_index = 0
        self.active.clear()
        self.playing = True
        return True

    def stop(self, audio: AudioEngine) -> None:
        for voice in tuple(self.active):
            audio.note_off(voice)
        self.active.clear()
        self.playing = False

    def tick(self, now: float, audio: AudioEngine, muted: bool) -> None:
        if not self.playing:
            return
        elapsed = now - self.started_at
        while self.next_index < len(self.notes) and self.notes[self.next_index].start <= elapsed:
            index = self.next_index
            note = self.notes[index]
            voice = f"replay-{index}"
            if not muted:
                audio.note_on(voice, note.gesture, note.octave, note.instrument)
            self.active[voice] = note.start + note.duration
            self.next_index += 1
        for voice, end in tuple(self.active.items()):
            if elapsed >= end:
                audio.note_off(voice)
                del self.active[voice]
        if self.next_index == len(self.notes) and not self.active:
            self.playing = False


def installation_check() -> int:
    classifier = HandGestureClassifier()
    assert classifier.classify_pattern((True, True, True, False), False) is Gesture.THREE
    audio = AudioEngine(volume=0.10)
    game = RhythmChallenge(rounds=3, seed=7)
    game.start(0.0)
    blank = np.full((540, 960, 3), (29, 25, 39), dtype=np.uint8)
    result = GestureResult(Gesture.UNKNOWN, 0.0, (False,) * 5)
    rendered = render(blank, result, Gesture.UNKNOWN, UiState("free", False, 60.0), game, 0.1)
    assert rendered.shape == (540, 960 + PANEL_WIDTH, 3)
    melody = MelodyChallenge()
    melody.start(0.0)
    assert melody.target is Gesture.FIST
    audio.close()
    print("Music Game check: OK")
    print(f"Audio available: {'yes' if audio.available else 'no'}")
    return 0


def _stabilizer(sensitivity: str) -> GestureStabilizer:
    votes = {"Nhanh": 3, "Vừa": 5, "Ổn định": 7}[sensitivity]
    return GestureStabilizer(window_size=7, votes_required=votes,
                             release_frames=3, cooldown_seconds=0.20)


def _set_message(state: UiState, value: str, now: float, seconds: float = 1.0) -> None:
    state.message = value
    state.message_until = now + seconds


def run(args: argparse.Namespace) -> int:
    source = parse_source(args.source)
    capture = open_capture(source, args.width, args.height)
    tracker = None
    audio = None
    recorder = PerformanceRecorder()
    replay = ReplayScheduler()
    try:
        tracker = HandTracker()
        audio = AudioEngine(volume=max(0.0, min(1.0, args.volume)),
                            buffer_size=args.buffer_size, instrument=args.instrument)
        calibration = GestureCalibration.load(CALIBRATION_FILE)
        classifier = HandGestureClassifier(calibration)
        note_filter = _stabilizer(args.sensitivity)
        control_filter = GestureStabilizer(window_size=5, votes_required=4,
                                           release_frames=3, cooldown_seconds=0.25)
        control = ControlState(instrument=args.instrument)
        game = RhythmChallenge()
        melody = MelodyChallenge(song=args.song)
        is_local_video = isinstance(source, str) and "://" not in source
        timeline = VideoTimeline(capture.get(cv2.CAP_PROP_FPS)) if is_local_video else None
        now = 0.0 if timeline else time.monotonic()
        game.start(now)
        melody.start(now)
        state = UiState(args.mode, False, 0.0, instrument=args.instrument,
                        volume=audio.volume, buffer_size=args.buffer_size)
        active_note: Gesture | None = None
        raw_candidate = Gesture.UNKNOWN
        candidate_since = now
        wizard: CalibrationWizard | None = None
        last_frame_time = time.monotonic()

        cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_TITLE, args.width + PANEL_WIDTH, args.height)

        while True:
            ok, frame = capture.read()
            if not ok:
                if args.loop_video and is_local_video:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    if timeline:
                        timeline.loop()
                    continue
                break

            now = timeline.advance(capture) if timeline else time.monotonic()
            if not args.no_mirror:
                frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (args.width, args.height), interpolation=cv2.INTER_AREA)
            observations = tracker.process(frame)
            tracker.draw(frame, observations)
            note_hand, control_hand = select_hands(
                observations, args.note_hand, mirrored=not args.no_mirror
            )
            raw_result = (
                classifier.classify(note_hand.points) if note_hand is not None
                else GestureResult(Gesture.UNKNOWN, 0.0, (False,) * 5)
            )
            stable = Gesture.UNKNOWN
            state.finger_states = raw_result.fingers
            state.control_present = control_hand is not None

            if wizard is not None:
                if note_hand is not None:
                    finished_pose = wizard.feed(classifier.feature_vector(note_hand.points))
                    if finished_pose:
                        _set_message(state, "Đã lấy mẫu. Làm form tiếp theo!", now)
                if wizard.finished:
                    wizard.calibration.save(CALIBRATION_FILE)
                    classifier.calibration = wizard.calibration
                    wizard = None
                    _set_message(state, "Hiệu chỉnh hoàn tất và đã lưu", now, 2.0)
                else:
                    state.calibration_target = wizard.target
                    state.calibration_count = wizard.count
                    state.calibration_required = wizard.required
                    state.calibration_collecting = wizard.collecting
            else:
                state.calibration_target = None
                if control_hand is not None:
                    control_result = classifier.classify(control_hand.points)
                    control_event, _ = control_filter.update(control_result.gesture, now)
                    if control_event is not None:
                        message = control.apply(control_event)
                        if message:
                            _set_message(state, message, now)
                            if active_note is not None:
                                audio.note_off("live")
                                recorder.note_off("live", now)
                                if not state.muted:
                                    audio.note_on("live", active_note, control.octave,
                                                  control.instrument)
                                recorder.note_on("live", active_note, now, control.octave,
                                                 control.instrument)
                else:
                    control_filter.update(Gesture.UNKNOWN, now)

                if raw_result.gesture is not raw_candidate:
                    raw_candidate = raw_result.gesture
                    candidate_since = now
                event, stable = note_filter.update(raw_result.gesture, now)
                if active_note is not None and stable is not active_note:
                    audio.note_off("live")
                    recorder.note_off("live", now)
                    active_note = None
                if event is not None:
                    state.latency_ms = max(0.0, (now - candidate_since) * 1000.0)
                    if not state.muted:
                        audio.note_on("live", event, control.octave, control.instrument)
                    recorder.note_on("live", event, now, control.octave, control.instrument)
                    active_note = event
                    if state.mode == "free":
                        _set_message(state, f"Đang chơi {event.value}", now, 0.6)
                    else:
                        current_game = melody if state.mode == "melody" else game
                        game_event = current_game.submit(event, now)
                        if game_event is not None:
                            _set_message(state, game_event.message, now)

                if state.mode != "free":
                    current_game = melody if state.mode == "melody" else game
                    timeout = current_game.tick(now)
                    if timeout is not None:
                        _set_message(state, timeout.message, now)
                replay.tick(now, audio, state.muted)

            state.instrument = control.instrument
            state.octave = control.octave
            state.recording = recorder.recording
            state.playback = replay.playing
            elapsed = max(time.monotonic() - last_frame_time, 1e-6)
            instant_fps = 1.0 / elapsed
            state.fps = instant_fps if state.fps == 0 else state.fps * 0.90 + instant_fps * 0.10
            last_frame_time = time.monotonic()
            stable = Gesture.UNKNOWN if wizard is not None else stable
            current_game = melody if state.mode == "melody" else game
            cv2.imshow(WINDOW_TITLE, render(frame, raw_result, stable, state, current_game, now))
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("c"):
                if wizard is None:
                    replay.stop(audio)
                    if active_note is not None:
                        audio.note_off("live")
                        recorder.note_off("live", now)
                        active_note = None
                    note_filter.reset()
                    wizard = CalibrationWizard()
                    _set_message(state, "Hiệu chỉnh: làm form rồi nhấn Space", now, 2.0)
                else:
                    wizard = None
                    state.calibration_target = None
                    _set_message(state, "Đã hủy hiệu chỉnh", now)
            elif key == 32 and wizard is not None:
                wizard.begin_capture()
            elif key == ord("g") and wizard is None:
                modes = ("free", "challenge", "melody")
                state.mode = modes[(modes.index(state.mode) + 1) % len(modes)]
                game.start(now)
                melody.start(now)
                note_filter.reset()
                _set_message(state, f"Chế độ: {state.mode}", now)
            elif key == ord("r") and wizard is None:
                game.start(now)
                melody.start(now)
                note_filter.reset()
                _set_message(state, "Đã chơi lại", now)
            elif key == ord("m"):
                state.muted = not state.muted
                audio.set_muted(state.muted)
                if not state.muted and active_note is not None:
                    audio.note_on("live", active_note, control.octave, control.instrument)
            elif key == ord("t"):
                if recorder.recording:
                    saved = recorder.stop(now, RECORDINGS_DIR)
                    _set_message(state, "Đã lưu WAV + MIDI + JSON" if saved else "Chưa có nốt để lưu",
                                 now, 2.0)
                else:
                    recorder.start(now)
                    if active_note is not None:
                        recorder.note_on("live", active_note, now, control.octave,
                                         control.instrument)
                    _set_message(state, "Bắt đầu ghi âm", now)
            elif key == ord("p"):
                if replay.playing:
                    replay.stop(audio)
                elif replay.start(recorder.notes, now):
                    _set_message(state, "Đang phát lại bản ghi", now)
                else:
                    _set_message(state, "Chưa có bản ghi", now)
        if recorder.recording:
            recorder.stop(now, RECORDINGS_DIR)
    finally:
        capture.release()
        if tracker is not None:
            tracker.close()
        if audio is not None:
            replay.stop(audio)
            audio.close()
        cv2.destroyAllWindows()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.check:
        return installation_check()
    if not argv:
        settings = choose_settings()
        if settings is None:
            return 0
        for name, value in settings.items():
            if name == "buffer":
                args.buffer_size = value
            else:
                setattr(args, name, value)
    try:
        return run(args)
    except (FileNotFoundError, RuntimeError, cv2.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

