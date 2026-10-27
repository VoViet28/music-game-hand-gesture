from music_game.game import RhythmChallenge
from music_game.gestures import Gesture


def test_correct_pose_scores_and_advances():
    game = RhythmChallenge(rounds=2, seconds_per_round=5.0, seed=2)
    game.start(10.0)
    first = game.target
    event = game.submit(first, 11.0)
    assert event is not None and event.correct
    assert game.score == 100
    assert game.completed == 1
    assert game.target is not first


def test_wrong_pose_penalizes_without_advancing():
    game = RhythmChallenge(seed=3)
    game.start(0.0)
    wrong = next(item for item in Gesture if item not in (game.target, Gesture.UNKNOWN))
    target = game.target
    event = game.submit(wrong, 1.0)
    assert event is not None and not event.correct
    assert game.target is target
    assert game.completed == 0
    assert game.score == 0


def test_timeout_finishes_last_round():
    game = RhythmChallenge(rounds=1, seconds_per_round=2.0, seed=1)
    game.start(5.0)
    assert game.tick(6.9) is None
    event = game.tick(7.0)
    assert event is not None and event.message == "TIME OUT"
    assert game.finished
    assert game.misses == 1


def test_first_scale_cycle_contains_all_seven_notes():
    game = RhythmChallenge(rounds=7, seed=9)
    game.start(0.0)
    targets = []
    for step in range(7):
        targets.append(game.target)
        game.submit(game.target, step + 0.1)
    assert len(set(targets)) == 7
