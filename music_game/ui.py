"""Vietnamese camera overlay and compact seven-note game dashboard."""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .gestures import Gesture, GestureResult, PLAYABLE_GESTURES


PANEL_WIDTH = 420
COLORS = {
    Gesture.FIST: (100, 95, 247), Gesture.POINT: (245, 196, 71),
    Gesture.PEACE: (94, 214, 121), Gesture.THREE: (89, 198, 240),
    Gesture.PALM: (248, 166, 74), Gesture.ROCK: (218, 90, 217),
    Gesture.THUMBS_UP: (57, 214, 250), Gesture.UNKNOWN: (144, 150, 165),
}
NOTE_NAMES = {
    Gesture.FIST: "Đô · C4", Gesture.POINT: "Rê · D4",
    Gesture.PEACE: "Mi · E4", Gesture.THREE: "Fa · F4",
    Gesture.PALM: "Sol · G4", Gesture.ROCK: "La · A4",
    Gesture.THUMBS_UP: "Si · B4",
}
GESTURE_NAMES = {
    Gesture.FIST: "Nắm tay", Gesture.POINT: "Một ngón",
    Gesture.PEACE: "Hai ngón", Gesture.THREE: "Ba ngón",
    Gesture.PALM: "Xòe tay", Gesture.ROCK: "Trỏ + út",
    Gesture.THUMBS_UP: "Ngón cái lên", Gesture.UNKNOWN: "Chưa thấy tay",
}


@dataclass
class UiState:
    mode: str
    muted: bool
    fps: float
    message: str = ""
    message_until: float = 0.0
    instrument: str = "Piano"
    octave: int = 0
    volume: float = 0.55
    latency_ms: float = 0.0
    buffer_size: int = 512
    recording: bool = False
    playback: bool = False
    finger_states: tuple[bool, bool, bool, bool, bool] = (False,) * 5
    control_present: bool = False
    calibration_target: Gesture | None = None
    calibration_count: int = 0
    calibration_required: int = 16
    calibration_collecting: bool = False


@lru_cache(maxsize=12)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _rect(image, left: int, top: int, right: int, bottom: int, color) -> None:
    cv2.rectangle(image, (left, top), (right, bottom), color, -1)


def _icon(image, gesture: Gesture, center: tuple[int, int], color, scale=0.7) -> None:
    cx, cy = center
    fingers = {
        Gesture.FIST: (0, 0, 0, 0, 0), Gesture.POINT: (0, 1, 0, 0, 0),
        Gesture.PEACE: (0, 1, 1, 0, 0), Gesture.THREE: (0, 1, 1, 1, 0),
        Gesture.PALM: (1, 1, 1, 1, 1), Gesture.ROCK: (0, 1, 0, 0, 1),
        Gesture.THUMBS_UP: (1, 0, 0, 0, 0),
    }.get(gesture, (0, 0, 0, 0, 0))
    def p(dx, dy):
        return cx + int(dx * scale), cy + int(dy * scale)
    cv2.circle(image, p(0, 6), max(4, int(12 * scale)), color, -1, cv2.LINE_AA)
    if gesture is Gesture.THUMBS_UP:
        cv2.line(image, p(-8, 2), p(-8, -19), color, max(2, int(6 * scale)), cv2.LINE_AA)
        return
    for raised, x in zip(fingers[1:], (-12, -5, 2, 9)):
        cv2.line(image, p(x, 5), p(x, -21 if raised else -4),
                 color, max(2, int(4 * scale)), cv2.LINE_AA)
    if fingers[0]:
        cv2.line(image, p(-8, 7), p(-21, -3), color, max(2, int(5 * scale)), cv2.LINE_AA)


def render(camera_frame, raw_result: GestureResult, stable_gesture: Gesture,
           state: UiState, game, now: float | None = None):
    now = time.monotonic() if now is None else now
    height, width = camera_frame.shape[:2]
    canvas = np.zeros((height, width + PANEL_WIDTH, 3), dtype=np.uint8)
    canvas[:, :width] = camera_frame
    panel_x = width
    _rect(canvas, panel_x, 0, width + PANEL_WIDTH, height, (38, 27, 36))
    overlay = canvas[:, :width].copy()
    _rect(overlay, 0, 0, width, 82, (17, 20, 31))
    _rect(overlay, 0, height - 80, width, height, (17, 20, 31))
    cv2.addWeighted(overlay, 0.80, canvas[:, :width], 0.20, 0, canvas[:, :width])

    labels: list[tuple[str, tuple[int, int], int, tuple[int, int, int], bool]] = []
    def label(text: str, x: int, y: int, size=16, color=(238, 240, 247), bold=False):
        labels.append((text, (x, y), size, color, bold))

    label("MUSIC GAME", 24, 17, 28, bold=True)
    mode_name = {"free": "Chơi tự do", "challenge": "Thử thách form tay",
                 "melody": "Chơi theo giai điệu"}.get(state.mode, state.mode)
    label(mode_name, 25, 52, 16, (166, 184, 205))
    label(f"{state.fps:.0f} FPS  ·  {'Tắt âm' if state.muted else 'Có âm'}", width - 185, 26, 14)

    selected_color = COLORS[stable_gesture]
    _rect(canvas, 20, height - 148, 410, height - 90, (34, 29, 45))
    cv2.circle(canvas, (45, height - 118), 12, selected_color, -1, cv2.LINE_AA)
    label(GESTURE_NAMES[stable_gesture], 66, height - 136, 23,
          tuple(reversed(selected_color)), True)
    if stable_gesture in NOTE_NAMES:
        label(NOTE_NAMES[stable_gesture], 290, height - 131, 19,
              tuple(reversed(selected_color)), True)
    finger_line = "Ngón: " + " ".join(
        f"{name}{'↑' if extended else '↓'}"
        for name, extended in zip(("C", "T", "G", "A", "U"), state.finger_states)
    )
    label(finger_line, 22, height - 74, 14, (205, 212, 224))
    label("G chế độ  ·  R đặt lại  ·  M âm  ·  C hiệu chỉnh  ·  Q thoát", 22,
          height - 53, 14)
    label("T ghi/dừng  ·  P phát lại  ·  Space chụp form khi hiệu chỉnh", 22,
          height - 31, 14)

    x0, x1 = width + 18, width + PANEL_WIDTH - 18
    label("BẢNG ĐIỀU KHIỂN", x0, 14, 15, (156, 196, 219), True)
    panel_bottom = min(220, height - 272)
    _rect(canvas, x0, 48, x1, panel_bottom, (55, 39, 54))
    if state.calibration_target is not None:
        label("HIỆU CHỈNH CỬ CHỈ", x0 + 15, 62, 17, (111, 232, 175), True)
        label(f"Làm form: {GESTURE_NAMES[state.calibration_target]}", x0 + 15, 96, 20, bold=True)
        label(f"Đã lấy {state.calibration_count}/{state.calibration_required} frame",
              x0 + 15, 134, 16)
        help_text = "Giữ tay yên..." if state.calibration_collecting else "Nhấn Space để lấy mẫu"
        label(help_text, x0 + 15, 174, 15, (177, 218, 230))
        label("Nhấn C để hủy", x0 + 15, 198, 13)
    elif state.mode == "free":
        label("Giữ form để ngân nốt; thả tay để dừng.", x0 + 15, 61, 15, bold=True)
        label(f"Nhạc cụ: {state.instrument}   ·   Quãng tám: {state.octave:+d}",
              x0 + 15, 92, 16)
        label(f"Âm lượng: {state.volume:.0%}   ·   Đệm: {state.buffer_size} mẫu",
              x0 + 15, 119, 14)
        label(f"Trễ lọc cử chỉ: {state.latency_ms:.0f} ms", x0 + 15, 144, 14)
        label("Tay 2: nắm/trỏ/xòe = quãng tám;", x0 + 15, 171, 14)
        label("hai/ba/trỏ+út = Piano/Bell/Synth", x0 + 15, 191, 14)
    else:
        if game.finished:
            label("HOÀN THÀNH!", x0 + 16, 61, 20, (127, 234, 180), True)
            label(f"Điểm: {game.score}   ·   Chuỗi tốt nhất: {game.best_streak}",
                  x0 + 16, 104, 16, bold=True)
            label("Nhấn R để chơi lại", x0 + 16, 162, 16)
        else:
            target = game.target
            label("CHƠI NỐT NÀY", x0 + 16, 58, 15, (169, 177, 201), True)
            _icon(canvas, target, (x0 + 44, 117), COLORS[target], 1.1)
            label(f"{NOTE_NAMES[target]} · {GESTURE_NAMES[target]}", x0 + 79, 100,
                  19, tuple(reversed(COLORS[target])), True)
            label(f"{game.completed + 1}/{game.rounds}   Điểm {game.score}   Chuỗi ×{game.streak}",
                  x0 + 16, 154, 15)
            bar_left, bar_right, bar_y = x0 + 16, x1 - 16, min(197, panel_bottom - 16)
            cv2.line(canvas, (bar_left, bar_y), (bar_right, bar_y), (77, 66, 83), 8, cv2.LINE_AA)
            end = int(bar_left + (bar_right - bar_left) * game.progress(now))
            cv2.line(canvas, (bar_left, bar_y), (end, bar_y), COLORS[target], 8, cv2.LINE_AA)

    card_top = panel_bottom + 27
    card_height = min(35, max(26, (height - card_top - 16 - 18) // 7))
    label("BẢY NỐT NHẠC", x0, panel_bottom + 6, 14, (159, 184, 210), True)
    for index, gesture in enumerate(PLAYABLE_GESTURES):
        top = card_top + index * (card_height + 3)
        if top + card_height > height - 12:
            break
        active = gesture is stable_gesture
        _rect(canvas, x0, top, x1, top + card_height, (65, 47, 70) if active else (48, 38, 56))
        _icon(canvas, gesture, (x0 + 25, top + card_height // 2), COLORS[gesture])
        label(GESTURE_NAMES[gesture], x0 + 49, top + 5, 15, bold=active)
        label(NOTE_NAMES[gesture], x1 - 103, top + 5, 15,
              tuple(reversed(COLORS[gesture])), True)

    if state.recording:
        cv2.circle(canvas, (width - 220, 34), 9, (70, 67, 250), -1)
        label("ĐANG GHI", width - 205, 23, 15, (255, 215, 215), True)
    if state.playback:
        label("PHÁT LẠI", width - 345, 23, 15, (150, 240, 190), True)
    if state.message and now <= state.message_until:
        _rect(canvas, width // 2 - 235, 96, width // 2 + 235, 151, (36, 40, 55))
        label(state.message, width // 2 - 212, 110, 20, (145, 239, 184), True)

    # Pillow draws every Vietnamese label in one pass (OpenCV's built-in font
    # cannot render Vietnamese diacritics).
    image = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    for value, position, size, color, bold in labels:
        draw.text(position, value, fill=color, font=_font(size, bold))
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)

