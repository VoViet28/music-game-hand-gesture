# Music Game 2.0 - nhạc cụ bằng cử chỉ tay

Music Game đọc webcam hoặc video, lấy 21 landmark mỗi tay bằng MediaPipe rồi tự
phân tích hình học các ngón tay để chơi bảy nốt tự nhiên. Giữ form để ngân nốt;
thả hoặc đổi form để dừng/chuyển nốt. Chương trình có ba chế độ: chơi tự do,
thử thách form tay và chơi một giai điệu đúng nhịp.

## Cài đặt

Cần Python 3.10-3.12 (64-bit), webcam và loa. Trong PowerShell tại thư mục này:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

Sau đó bấm đúp `start_camera.bat` hoặc chạy:

```powershell
.\.venv\Scripts\python.exe run_music_game.py
```

Màn hình khởi động tiếng Việt cho chọn camera/video, chế độ, bài nhạc, nhạc cụ,
âm lượng, tay chơi nốt, độ nhạy và bộ đệm âm thanh. Nhấn **BẮT ĐẦU CHƠI**.

Nếu muốn bỏ qua màn hình khởi động, dùng tham số:

```powershell
.\.venv\Scripts\python.exe run_music_game.py --source 0 --mode melody --instrument Piano
.\.venv\Scripts\python.exe run_music_game.py --source "D:\video\hand.mp4" --loop-video
```

Với video cục bộ, chương trình phát theo FPS/mốc thời gian của video; thử thách
và bản ghi dùng cùng mốc thời gian đó. Nếu xử lý frame chậm hơn tốc độ video,
máy sẽ phát chậm; giảm `--width` và `--height` để cải thiện.

## Bảy nốt nhạc

| Form tay | Nốt | Tần số quãng chuẩn |
|---|---|---:|
| FIST - nắm tay | Đô / C4 | 261,63 Hz |
| POINT - một ngón trỏ | Rê / D4 | 293,66 Hz |
| PEACE - trỏ + giữa | Mi / E4 | 329,63 Hz |
| THREE - trỏ + giữa + áp út | Fa / F4 | 349,23 Hz |
| PALM - xòe tay | Sol / G4 | 392,00 Hz |
| ROCK - trỏ + út | La / A4 | 440,00 Hz |
| THUMBS UP - ngón cái lên | Si / B4 | 493,88 Hz |

Âm thanh được tổng hợp trực tiếp, không cần tải nhạc bên ngoài. Có ba màu âm:
Piano, Bell và Synth.

## Điều khiển

- `G`: chuyển Chơi tự do -> Thử thách form tay -> Giai điệu.
- `R`: bắt đầu lại thử thách/giai điệu.
- `M`: tắt/bật tiếng.
- `C`: bắt đầu hoặc hủy hiệu chỉnh form tay.
- `Space`: lấy mẫu form hiện tại khi màn hình hiệu chỉnh yêu cầu.
- `T`: bắt đầu/dừng ghi bản nhạc. Khi dừng, chương trình xuất JSON, WAV và MIDI
  vào thư mục `recordings/`.
- `P`: phát lại hoặc dừng bản ghi gần nhất trong phiên chạy.
- `Q` hoặc `Esc`: thoát. Nếu còn đang ghi, chương trình sẽ lưu bản ghi trước khi thoát.

### Hiệu chỉnh cử chỉ

Nhấn `C`, làm form được chỉ dẫn rồi nhấn `Space`. Giữ tay ổn định trong 16 frame.
Lặp lại cho đủ bảy form. Mẫu được lưu ở `config/calibration.json` và tự nạp lần
sau. Màn hình hiển thị trạng thái từng ngón (`C` cái, `T` trỏ, `G` giữa, `A` áp
út, `U` út; mũi tên lên = duỗi). Nếu chụp sai form, nhấn `C` để hủy và làm lại.

### Chơi bằng hai tay

Theo mặc định, **tay phải** chơi nốt; **tay trái** đổi nhạc cụ/quãng tám. Chỉ đưa
một tay vào khung hình thì tay đó luôn chơi nốt. Có thể chọn tay chơi nốt trong
màn hình khởi động hoặc dùng `--note-hand Left`.

| Form của tay điều khiển | Tác dụng |
|---|---|
| FIST | Quãng tám thấp (-1) |
| POINT | Quãng tám chuẩn (0) |
| PALM | Quãng tám cao (+1) |
| PEACE | Piano |
| THREE | Bell |
| ROCK | Synth |

Khi đổi nhạc cụ/quãng tám trong lúc giữ nốt, nốt hiện tại được chuyển ngay sang
cài đặt mới. Tay điều khiển không bắt buộc.

### Chế độ giai điệu

`Twinkle` gồm 14 nốt; `Scale` gồm bảy nốt đi lên. Có hai nhịp đếm đầu. Chơi
đúng form gần thời điểm thanh nhịp sáng nhất để được 120 điểm; chơi hơi lệch
nhịp nhận 80 hoặc 45 điểm. Sai nốt trừ 15; lỡ nhịp được tính là miss. Khi bài
có hai nốt giống nhau liền nhau, phải thả tay giữa hai nốt để kích hoạt lại.

## Điều chỉnh độ trễ

Màn hình hiển thị **trễ lọc cử chỉ**: thời gian từ frame đầu tiên mang nhãn mới
đến lúc nhãn được ổn định và bắt đầu phát âm. Đây chưa phải độ trễ vật lý từ lúc
tay bắt đầu chuyển động đến lúc loa phát tiếng. Mức `Nhanh` cần 3/7 frame,
`Vừa` cần 5/7, `Ổn định` cần 7/7. Bộ đệm âm thanh 256 mẫu thường giảm trễ hơn
nhưng có thể gây tiếng giật; nếu gặp lỗi âm hãy chọn 512 hoặc 1024.

## Mã nguồn và kiểm thử

```text
music_game/vision.py       Camera/video -> landmark của tối đa hai tay
music_game/gestures.py     Góc khớp, tỉ lệ khoảng cách, bảng luật bảy form
music_game/calibration.py  Mẫu riêng của người dùng
music_game/stabilizer.py   Lọc theo frame và chống kích hoạt lặp
music_game/controls.py     Phân vai hai tay, đổi quãng tám/nhạc cụ
music_game/audio.py        Tổng hợp và ngân nốt
music_game/game.py         Thử thách form tay
music_game/melody.py       Giai điệu và chấm đúng nhịp
music_game/recorder.py     Ghi, phát lại, xuất WAV/MIDI/JSON
music_game/launcher.py     Màn hình cài đặt tiếng Việt
music_game/ui.py           Giao diện camera tiếng Việt
music_game/app.py          Vòng lặp tích hợp, đồng bộ video
```

Kiểm thử không cần camera:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe run_music_game.py --check
```

## Khắc phục sự cố

- Không mở được webcam: đóng các ứng dụng khác đang giữ camera, thử camera `1`
  hoặc kiểm tra quyền Camera trong Windows.
- Không nghe âm: kiểm tra loa mặc định, tăng âm lượng trong màn hình cài đặt và
  xác nhận không bật `M`.
- Nhận sai ngón: đưa cả bàn tay vào khung hình, tăng ánh sáng, tránh ngón che nhau
  rồi chạy hiệu chỉnh `C`.
- Màn hình bị chậm: thử `--width 640 --height 480`, độ nhạy `Nhanh`; khi cần,
  dùng bộ đệm 512 để tránh tiếng giật.

Ý tưởng ban đầu tham khảo:
<https://github.com/jambhaleAnuj/Music-control-with-hand-gesture-recognition>.
Thuật toán phân loại và các chế độ chơi trong project này được viết riêng.

## Báo cáo đồ án

- [Báo cáo PDF (5 trang A4)](docs/Bao_cao_Music_Game.pdf): có bìa để trống
  thông tin sinh viên, lớp và giảng viên để tự điền sau.
- [Báo cáo kỹ thuật dạng Markdown](REPORT.md).
- [Kết quả và giới hạn kiểm thử](VERIFICATION.md).

