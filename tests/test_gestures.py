import pytest

from music_game.gestures import Gesture, HandGestureClassifier, Point


@pytest.mark.parametrize(
    ("fingers", "thumb", "thumb_up", "expected"),
    [
        ((True, True, True, True), True, False, Gesture.PALM),
        ((False, False, False, False), False, False, Gesture.FIST),
        ((True, True, False, False), False, False, Gesture.PEACE),
        ((True, True, True, False), False, False, Gesture.THREE),
        ((True, False, False, False), False, False, Gesture.POINT),
        ((True, False, False, True), False, False, Gesture.ROCK),
        ((False, False, False, False), True, True, Gesture.THUMBS_UP),
        ((False, True, False, False), False, False, Gesture.UNKNOWN),
    ],
)
def test_pose_pattern_mapping(fingers, thumb, thumb_up, expected):
    assert HandGestureClassifier.classify_pattern(fingers, thumb, thumb_up) is expected


def test_classifier_rejects_wrong_landmark_count():
    with pytest.raises(ValueError, match="Expected 21"):
        HandGestureClassifier().classify([Point(0.0, 0.0)] * 20)


def test_geometry_detects_an_open_palm():
    landmarks = [Point(0.5, 0.85)] * 21
    values = {
        0: (0.50, 0.85),
        1: (0.45, 0.77), 2: (0.39, 0.70), 3: (0.32, 0.63), 4: (0.24, 0.57),
        5: (0.42, 0.68), 6: (0.42, 0.51), 7: (0.42, 0.38), 8: (0.42, 0.24),
        9: (0.49, 0.65), 10: (0.49, 0.46), 11: (0.49, 0.30), 12: (0.49, 0.14),
        13: (0.56, 0.68), 14: (0.56, 0.50), 15: (0.56, 0.37), 16: (0.56, 0.24),
        17: (0.63, 0.72), 18: (0.63, 0.57), 19: (0.63, 0.46), 20: (0.63, 0.34),
    }
    for index, (x, y) in values.items():
        landmarks[index] = Point(x, y)
    result = HandGestureClassifier().classify(landmarks)
    assert result.gesture is Gesture.PALM
    assert result.fingers == (True, True, True, True, True)
