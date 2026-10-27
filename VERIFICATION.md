# Kiểm chứng Music Game 2.0 - 2026-10-26

Đã kiểm thử trong môi trường Python 3.12 trên Windows.

```text
22 passed in 0.17s
Music Game check: OK
Audio available: yes
camera_read=True, frame=(480,640,3)
launcher_window_ok=1
free_mode=OK, challenge_mode=OK, melody_mode=OK
note_on_off_ok=True, buffer=256
```

## Phạm vi kiểm thử

- Unit test cho bảy form tay, bộ lọc frame, luật chơi cũ và chu kỳ bảy nốt.
- Unit test cho hiệu chỉnh đủ bảy form và nạp lại mẫu từ JSON.
- Unit test cho điểm giai điệu theo nốt/thời điểm và miss.
- Unit test cho phân vai hai tay và đổi quãng tám/nhạc cụ.
- Unit test ghi nốt, xuất JSON/WAV/MIDI và phát lại theo mốc thời gian.
- Unit test dòng thời gian video tiếp tục tăng khi lặp.
- Smoke test giao diện không cần camera; xem ảnh render ở 540p và 480p của Free,
  Challenge, Melody và màn hình hiệu chỉnh. Không có thẻ nốt bị cắt ở 480p.
- Video AVI 60 frame/30 FPS đã chạy hết ba chế độ và thoát với mã 0.
- Camera mặc định trả frame thật và MediaPipe xử lý frame thành công; frame
  thử không có bàn tay nên số tay phát hiện là 0.
- Tkinter mở được cửa sổ cài đặt; chưa có người dùng thao tác thủ công qua nút.
- Pygame mở audio mixer ở bộ đệm 256, bắt đầu và kết thúc nốt thành công.

## Giới hạn xác minh

Chưa có người đứng trước camera để thử đủ bảy form và hiệu chỉnh bằng tay thật;
chưa đo độ trễ tay tới loa bằng thiết bị ngoài. Con số trên màn hình là độ trễ
của bộ lọc sau khi MediaPipe đã có nhãn thô. Chất lượng nhận dạng thực tế phụ
thuộc ánh sáng, nền và vị trí bàn tay.

