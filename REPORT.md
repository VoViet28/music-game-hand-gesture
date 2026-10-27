# Báo cáo kỹ thuật - Music Game

**Mã nguồn GitHub:** [VoViet28/music-game-hand-gesture](https://github.com/VoViet28/music-game-hand-gesture)

## 1. Ý tưởng và mục tiêu

Music Game biến bàn tay thành một nhạc cụ không chạm. Người dùng giữ form tay
để ngân nốt và thả tay để dừng. Có ba cách chơi: tự do, nhận dạng form tay và
chơi giai điệu theo nhịp.

Mục tiêu kỹ thuật là thể hiện rõ chuỗi xử lý `camera -> landmark -> thuật toán
tự xây dựng -> sự kiện -> âm thanh/game`, đúng trọng tâm của assignment.

## 2. Input và Output

**Input:** webcam, camera index khác, file video hoặc URL video stream. Mỗi frame
được OpenCV đọc và chuyển từ BGR sang RGB trước khi đưa vào MediaPipe.

**Output:** tên form tay, trạng thái năm ngón, độ tin cậy, landmark trực quan,
âm thanh tương ứng và số đo trễ lọc cử chỉ. Hai chế độ thử thách hiển thị nốt
mục tiêu, điểm, streak, số vòng và thanh nhịp. Bản ghi xuất JSON, WAV, MIDI.

## 3. Dữ liệu MediaPipe cung cấp

MediaPipe Hands trả về 21 điểm cho mỗi bàn tay (tối đa hai tay). Mỗi điểm có tọa độ chuẩn hóa
`(x, y, z)`. Chương trình dùng các nhóm điểm:

- `0`: cổ tay.
- `1-4`: ngón cái.
- `5-8`: ngón trỏ.
- `9-12`: ngón giữa.
- `13-16`: ngón áp út.
- `17-20`: ngón út.

MediaPipe chỉ phát hiện landmark; nó không quyết định 7 form tay của game.

## 4. Thuật toán phân loại tự xây dựng

### 4.1 Trạng thái ngón tay

Với bốn ngón trỏ, giữa, áp út và út, chương trình tính:

1. Góc tại khớp PIP: `angle(MCP, PIP, DIP)`.
2. Góc tại khớp DIP: `angle(PIP, DIP, TIP)`.
3. Tỉ lệ vươn: `distance(WRIST, TIP) / distance(WRIST, PIP)`.

Một ngón được xem là duỗi khi hai góc đủ thẳng và đầu ngón xa cổ tay hơn khớp
PIP. Kết hợp ba đại lượng giảm lỗi khi một khớp bị che hoặc bàn tay nghiêng.

Ngón cái dùng góc tại IP và khoảng cách từ đầu ngón cái tới gốc ngón giữa,
chuẩn hóa theo kích thước lòng bàn tay. THUMBS UP còn yêu cầu đầu ngón cái cao
hơn gốc ngón một khoảng tương đối và bốn ngón kia đều co.

### 4.2 Bảng luật form tay

| Trỏ | Giữa | Áp út | Út | Điều kiện thêm | Kết quả |
|---|---|---|---|---|---|
| 1 | 1 | 1 | 1 | - | PALM |
| 0 | 0 | 0 | 0 | cái co | FIST |
| 1 | 1 | 0 | 0 | - | PEACE |
| 1 | 1 | 1 | 0 | - | THREE |
| 1 | 0 | 0 | 0 | - | POINT |
| 1 | 0 | 0 | 1 | - | ROCK |
| 0 | 0 | 0 | 0 | cái duỗi lên | THUMBS UP |

Các mẫu không khớp được gán UNKNOWN để tránh phát âm sai.

### 4.3 Ổn định theo thời gian

Camera có thể dao động giữa hai nhãn ở từng frame. Bộ lọc giữ cửa sổ 7 frame
và chỉ công nhận khi một nhãn đạt 3, 5 hoặc 7 phiếu tùy mức độ nhạy. Mỗi nốt
có hai sự kiện: bắt đầu khi form ổn định và kết thúc khi form thay đổi/mất. Cooldown
0,20 giây hạn chế nhấp nháy. Màn hình đo thời gian từ nhãn thô đầu tiên đến lúc
ổn định; đây là trễ lọc, chưa phải trễ vật lý từ tay đến loa.

### 4.4 Hiệu chỉnh theo người dùng

Người dùng giữ từng form tay 16 frame. Chương trình lưu sáu đặc trưng hình học:
điểm duỗi của bốn ngón, điểm duỗi ngón cái và độ vươn lên của ngón cái. Khi đủ
bảy form, chương trình so khoảng cách của vector hiện tại với vector trung bình
của từng form; khoảng cách quá lớn hoặc hai ứng viên quá gần được gán UNKNOWN.
Mẫu được lưu vào `config/calibration.json`.

### 4.5 Phân vai hai tay

Một tay chơi nốt, tay còn lại điều khiển quãng tám (-1/0/+1) hoặc nhạc cụ
(Piano/Bell/Synth). Khi chỉ thấy một tay, tay đó luôn được dùng để chơi nốt.
Mỗi vai có bộ lọc cử chỉ riêng. Khi tay điều khiển đổi âm sắc hoặc quãng tám,
nốt đang ngân được kết thúc và phát lại với cài đặt mới.

## 5. Âm thanh

Âm thanh được tổng hợp ở 44,1 kHz theo âm giai Đô trưởng: Đô C4 261,63 Hz, Rê D4
293,66 Hz, Mi E4 329,63 Hz, Fa F4 349,23 Hz, Sol G4 392 Hz, La A4 440 Hz và Si
B4 493,88 Hz. Mỗi âm gồm tần số gốc và các họa âm theo nhạc cụ. Mẫu âm được tạo
theo chu kỳ nguyên để lặp liên tục khi giữ form tay. Khi bắt đầu có fade-in và khi
thả có fade-out 90 ms. Dữ liệu PCM stereo 16-bit được chuyển thành `pygame.Sound`
trong bộ nhớ. Bộ đệm 256/512/1024 mẫu có thể chọn tại màn hình khởi động.

## 6. Luật chơi

Challenge gồm 12 vòng, mỗi vòng 5 giây. Một túi trộn gồm đủ 7 nốt bảo đảm mỗi nốt
xuất hiện một lần trước khi lặp lại. Form đúng nhận 100 điểm và thêm 20 điểm
cho mỗi mức streak (tối đa 5 mức). Form sai trừ 25 điểm nhưng không đổi target.
Hết thời gian tính là một miss và chuyển vòng. Target kế tiếp luôn khác target
vừa qua để người chơi phải đổi form, đồng thời giúp bộ khóa sự kiện hoạt động rõ.

Chế độ Melody dùng chuỗi nốt `Twinkle` hoặc `Scale` với nhịp cố định. Có hai
nhịp đếm đầu và cửa sổ chấp nhận +/-0,55 giây quanh mỗi nhịp. Đúng rất sát
nhịp nhận 120 điểm, mức trung bình nhận 80, sát biên nhận 45; sai nốt trừ 15;
bỏ lỡ tăng số lần miss. Bản ghi lưu thời điểm bắt đầu, độ dài, quãng tám và
nhạc cụ từng nốt; WAV tổng hợp lại các nốt, MIDI ghi note-on/note-off chuẩn.

Với video cục bộ, vòng lặp chờ theo timestamp hoặc FPS của file, và đồng hồ
chấm điểm dùng chính dòng thời gian đó. Khi lặp video, offset tăng để thời gian
không đi ngược.

## 7. Kết quả kiểm thử

Unit test bao phủ:

- 7 mẫu form tay và trường hợp UNKNOWN.
- Chu kỳ thử thách đầu tiên chứa đủ 7 nốt, không lặp.
- Số lượng landmark không hợp lệ.
- Điều kiện 5/7 frame, khóa và nhả sự kiện.
- Chấm đúng, phạt sai, chuyển vòng và timeout.
- Smoke check dựng toàn bộ giao diện 1380 x 540 không cần camera.
- Hiệu chỉnh/lưu và nạp mẫu, phân vai tay, chấm nhịp, ghi và phát lại WAV/MIDI,
  đồng hồ video.

Kiểm thử thực tế nên thực hiện ở nhiều khoảng cách, hai loại nền, ánh sáng mạnh/
yếu và với file video. Kết quả phụ thuộc khả năng MediaPipe nhìn rõ 21 landmark.

## 8. Khó khăn và hướng phát triển

Khó khăn chính là ngón bị che khi bàn tay xoay ngang và sự dao động giữa các
frame. Thuật toán dùng tỉ lệ thay vì pixel, kết hợp góc + độ vươn và bộ lọc thời
gian để giảm hai vấn đề này.

Hướng phát triển: đo trễ end-to-end bằng thiết bị ngoài, thêm hợp âm đồng thời
bằng hai tay và huấn luyện trên bộ video ghi từ nhiều người dùng.
