from music_game.gestures import Gesture
from music_game.stabilizer import GestureStabilizer


def test_requires_stable_votes_and_fires_once_until_release():
    stabilizer = GestureStabilizer(
        window_size=5, votes_required=3, release_frames=2, cooldown_seconds=0.1
    )
    events = [stabilizer.update(Gesture.PEACE, i * 0.05)[0] for i in range(5)]
    assert events.count(Gesture.PEACE) == 1

    stabilizer.update(Gesture.UNKNOWN, 1.0)
    stabilizer.update(Gesture.UNKNOWN, 1.1)
    # Old votes remain in the window but cooldown and release permit a new event.
    event, _ = stabilizer.update(Gesture.PEACE, 1.2)
    assert event is Gesture.PEACE


def test_no_event_for_unstable_input():
    stabilizer = GestureStabilizer(window_size=5, votes_required=4)
    sequence = [Gesture.PALM, Gesture.FIST, Gesture.PEACE, Gesture.ROCK]
    assert all(stabilizer.update(item, index * 0.1)[0] is None for index, item in enumerate(sequence))

