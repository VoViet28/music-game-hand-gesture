import json
import wave
from pathlib import Path
from types import SimpleNamespace

from music_game.app import ReplayScheduler, VideoTimeline
from music_game.calibration import CalibrationWizard, GestureCalibration
from music_game.controls import ControlState, select_hands
from music_game.gestures import Gesture
from music_game.melody import MelodyChallenge
from music_game.recorder import PerformanceRecorder


def test_calibration_capture_predict_and_reload(tmp_path: Path):
    wizard = CalibrationWizard(required=8)
    for index in range(7):
        target = wizard.target
        wizard.begin_capture()
        features = (index * 0.3, 0.2, 0.4, 0.6, 0.8, 0.1)
        for _ in range(8):
            wizard.feed(features)
        assert target in wizard.calibration.samples
    assert wizard.finished and wizard.calibration.complete
    path = tmp_path / "calibration.json"
    wizard.calibration.save(path)
    loaded = GestureCalibration.load(path)
    assert loaded.complete
    assert loaded.predict((0.0, 0.2, 0.4, 0.6, 0.8, 0.1))[0] is Gesture.FIST


def test_melody_scores_note_and_timing():
    melody = MelodyChallenge(song="Scale", beat_seconds=1.0, hit_window=0.45)
    melody.start(10.0)
    assert melody.submit(Gesture.FIST, 11.0).points_delta == 0  # too early
    first = melody.submit(Gesture.FIST, 12.0)
    assert first.correct and first.points_delta == 120
    second = melody.submit(Gesture.POINT, 13.35)
    assert second.correct and second.points_delta == 45
    assert melody.completed == 2
    assert melody.tick(14.5) is not None
    assert melody.misses == 1


def test_hand_roles_and_control_mapping():
    right = SimpleNamespace(handedness="Right", points=[SimpleNamespace(x=0.8)])
    left = SimpleNamespace(handedness="Left", points=[SimpleNamespace(x=0.2)])
    assert select_hands([left, right], "Right") == (right, left)
    assert select_hands([left], "Right") == (left, None)
    # In a non-mirrored preview, MediaPipe's handedness labels are reversed.
    assert select_hands([left, right], "Right", mirrored=False) == (left, right)
    control = ControlState()
    control.apply(Gesture.PALM)
    control.apply(Gesture.THREE)
    assert (control.octave, control.instrument) == (1, "Bell")


def test_recording_exports_audio_and_midi(tmp_path: Path):
    recorder = PerformanceRecorder()
    recorder.start(10.0)
    recorder.note_on("live", Gesture.FIST, 10.1, 0, "Piano")
    recorder.note_off("live", 10.4)
    saved = recorder.stop(10.5, tmp_path)
    assert saved is not None
    json_path, wav_path, midi_path = saved
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data[0]["gesture"] == "FIST"
    assert 0.29 <= data[0]["duration"] <= 0.31
    with wave.open(str(wav_path), "rb") as audio:
        assert audio.getframerate() == 44100
        assert audio.getnframes() > 1000
    assert midi_path.read_bytes().startswith(b"MThd")


def test_replay_schedules_note_on_and_off():
    class FakeAudio:
        def __init__(self):
            self.actions = []
        def note_on(self, *args):
            self.actions.append(("on", args))
        def note_off(self, voice):
            self.actions.append(("off", voice))

    recorder = PerformanceRecorder()
    recorder.start(0.0)
    recorder.note_on("live", Gesture.PEACE, 0.2, 0, "Piano")
    recorder.note_off("live", 0.6)
    player, audio = ReplayScheduler(), FakeAudio()
    assert player.start(recorder.notes, 10.0)
    player.tick(10.1, audio, False)
    assert not audio.actions
    player.tick(10.3, audio, False)
    assert audio.actions[0][0] == "on"
    player.tick(10.7, audio, False)
    assert audio.actions[1][0] == "off"
    assert not player.playing


def test_video_clock_uses_media_timestamp_and_continues_after_loop(monkeypatch):
    import music_game.app as app

    monkeypatch.setattr(app.time, "sleep", lambda _: None)
    capture = SimpleNamespace(get=lambda _: 1000.0)
    timeline = VideoTimeline(30.0)
    assert timeline.advance(capture) == 1.0
    timeline.loop()
    assert timeline.advance(capture) > 2.0

