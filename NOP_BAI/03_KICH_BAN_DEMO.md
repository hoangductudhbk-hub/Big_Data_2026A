# KỊCH BẢN DEMO HỆ THỐNG

**Mục tiêu** (theo `Projects.pdf`): *"Dashboard with charts that help understand an overview of the data analysis"*, chứng minh hệ thống chạy thật trên dữ liệu thật.
**Thời lượng:** 2–3 phút · **Thực hiện:** Nhóm 2 (một người thao tác, một người thuyết minh)

**Mã nguồn:** https://github.com/hoangductudhbk-hub/Big_Data_2026A · **Dữ liệu gốc:** [Google Drive](https://drive.google.com/drive/folders/1dQq9kATcZ4wKA_DBr2S8nlsjQdZNfEy-?usp=sharing)

---

## 0. Chuẩn bị (làm trước buổi bảo vệ, không trình chiếu)

| Việc | Lệnh / thao tác | Kiểm tra |
|---|---|---|
| Bật Docker Desktop | Mở Docker Desktop, đợi biểu tượng hết xoay | Góc dưới trái báo *Engine running* |
| Khởi động hệ thống | `cd /d D:\BigData\Big_Data_2026A` → `docker compose up -d --build` | `docker compose ps`: `db` healthy, `api` running |
| Nạp dữ liệu (một lần) | `docker compose run --rm api python -m app.etl.load_processed` | Dòng cuối: `Xong trong ... s: 864,750 dòng vào 8 bảng.` |
| Mở sẵn 3 tab trình duyệt | `http://localhost:8000` · `http://localhost:8000/docs` · cửa sổ cmd | Dashboard hiện "API hoạt động · postgresql" |
| Chuẩn bị file sai | `backend\examples\import_traffic_mau.csv` (6 dòng, 2 dòng sai) | Mở được bằng Notepad |
| Có Internet | Để nền bản đồ OpenStreetMap hiển thị | Tab Bản đồ có nền đường phố |

> **Phương án dự phòng** nếu mất mạng hoặc Docker lỗi: chiếu ảnh trong `NOP_BAI/hinh/` (h6, h7, h8) và báo cáo `docs/bao-cao/21_e2e_docker.md`. Dashboard vẫn chạy khi không có mạng, chỉ thiếu nền bản đồ.

---

## 1. Khởi động và nạp dữ liệu (khoảng 30 giây)

**Thao tác:** chuyển sang cửa sổ cmd, chạy lại lệnh nạp (hoặc chiếu kết quả lần chạy trước nếu muốn tiết kiệm thời gian):

```bat
docker compose ps
docker compose run --rm api python -m app.etl.load_processed
```

**Điểm cần chỉ:**
- 2 container `db` (PostgreSQL 16) và `api` (FastAPI) đang chạy
- Kết quả nạp: `integrated_traffic 805,780 dòng`, `anomalies 13,678 dòng`, tổng **864.750 dòng vào 8 bảng trong khoảng 44 giây**

**Lời thoại:** "Toàn bộ hệ thống chạy trong Docker. Chương trình nạp kiểm tra data contract trước rồi mới ghi, tất cả trong một transaction; nếu file sai lược đồ thì không ghi gì và dữ liệu cũ còn nguyên."

---

## 2. Dashboard (khoảng 1 phút 30 giây)

### 2.1. Tab Tổng quan (15 giây)

**Thao tác:** mở `http://localhost:8000`.

**Điểm cần chỉ:**
- 5 ô số liệu: 805.780 bản ghi, 211 đường, 61 km/h, 13.678 bất thường, 14 ngày mất dữ liệu (ngày có ít dữ liệu, độ phủ < 50%; tính cả các ngày không có bản ghi nào thì nguồn tốc độ mất dữ liệu 22 ngày)
- Biểu đồ theo giờ: ngày thường có 2 đỉnh, chậm nhất 16h; cuối tuần không có cao điểm sáng
- Biểu đồ theo ngày: các điểm xám là ngày mất dữ liệu, được đánh dấu chứ không xóa

### 2.2. Tab Bản đồ (25 giây)

**Thao tác:**
1. Bấm tab **Bản đồ**: mỗi chấm là một tuyến có cảm biến, đỏ là chậm hơn trung vị, xanh là nhanh hơn
2. Bấm một chấm đỏ ở Bronx: **Cross Bronx Expressway**
3. Chỉ bảng bên phải: tốc độ TB 56 km/h (±33,8), 8.214 giờ dữ liệu, 133 bất thường; biểu đồ theo tuần; danh sách bất thường mạnh nhất
4. (Tuỳ chọn) đổi "Hiển thị" sang **Điểm đếm lưu lượng**: kích thước chấm theo số xe

**Lời thoại:** "Manhattan và các hầm, cầu màu đỏ; Staten Island màu xanh. Cross Bronx là tuyến biến động lớn nhất thành phố: lúc thông thì nhanh, lúc tắc thì rất chậm."

### 2.3. Tab Bất thường (25 giây)

**Thao tác:**
1. Bấm tab **Bất thường**
2. Rê chuột lên đỉnh màu cam đầu tháng 2 trên biểu đồ: ngày **13/02/2024**, 207 bản ghi nhanh bất thường, tuyết khoảng 16 cm
3. Đổi bộ lọc **|z| tối thiểu** từ 3 lên 5: số bất thường giảm, chỉ còn các trường hợp mạnh
4. Bấm một dòng trong danh sách: dashboard chuyển sang bản đồ và mở đúng đường đó

**Lời thoại:** "Thuật toán Z-score theo ngữ cảnh tự tìm ra ngày bão tuyết lớn nhất năm mà không cần ai chỉ trước. Hôm đó đường vắng nên xe chạy nhanh hơn bình thường; người dùng có thể chọn ngưỡng |z| để xem các bất thường mạnh hơn."

### 2.4. Tab Thời tiết (25 giây)

**Thao tác:** bấm tab **Thời tiết**, chỉ biểu đồ cột đầu tiên.

**Điểm cần chỉ:**
- Cột cam (so sánh thô) và cột xanh (có kiểm soát): Rain −6,6% → **−4,6%**; Snow +0,6% → **−0,1%**
- Biểu đồ nhiệt độ: thô −17,7% khi trời ≥ 30 °C, sau kiểm soát gần 0

**Lời thoại:** "So sánh thô nói tuyết làm xe nhanh hơn và trời nóng làm xe chậm 18%. Cả hai đều là nhiễu do mùa và giờ. Sau khi so mỗi giờ với chính đường đó cùng giờ, cùng tháng lúc khô ráo, chỉ còn mưa là có tác động thật."

---

## 3. Quản trị dữ liệu: bắt lỗi theo Data Contract (khoảng 30 giây)

**Thao tác:**
1. Bấm tab **Nhập dữ liệu**
2. Chọn file `backend\examples\import_traffic_mau.csv` → **Tải lên**
3. Chỉ kết quả: `PARTIAL · nhận 6 · thêm mới 4 · từ chối 2 · đường mới: S900001`
4. Chỉ bảng lý do:
   - Dòng 5: `timestamp phải là đầu giờ (vd 2024-03-01T08:00:00): contract dùng khung 1 giờ`
   - Dòng 6: `avg_speed=250.0 lớn hơn 160 km/h`
5. Chỉ bảng **Nhật ký nạp dữ liệu** vừa có thêm một dòng

**Lời thoại:** "Dữ liệu từ người dùng được kiểm tra bằng đúng quy tắc của data contract mà pipeline dùng. Dòng sai bị từ chối kèm lý do cụ thể, dòng đúng vẫn được ghi, và gửi lại cùng dữ liệu không tạo bản trùng."

> Sau buổi demo, chạy lại lệnh nạp ở mục 1 để xóa 4 dòng thử nghiệm khỏi database.

---

## 4. Tài liệu API (khoảng 20 giây)

**Thao tác:**
1. Mở `http://localhost:8000/docs`: 7 nhóm (health, roads, traffic, weather, statistics, anomalies, import), **27 endpoint**
2. Mở `GET /api/v1/statistics/live` → **Try it out** → `group_by = district` → **Execute**
3. Chỉ kết quả Manhattan: `n = 138419`, `mean ≈ 40,49`, `median = 40,91`, khớp với bảng Spark tính ở bước 15

**Lời thoại:** "API có tài liệu tự sinh. Endpoint này tính trực tiếp bằng SQL trên PostgreSQL và cho kết quả trùng với Spark, chứng minh dữ liệu không bị sai lệch qua các tầng."

---

## 5. Kết thúc (10 giây)

**Lời thoại:** "Hệ thống đạt 18 trên 18 kiểm tra end-to-end khi chạy trong Docker. Mã nguồn, tài liệu từng bước và báo cáo số liệu nằm trong repo của nhóm. Em xin cảm ơn."

---

## Bảng kiểm trước khi lên bảo vệ

- [ ] `docker compose ps` thấy `db` healthy, `api` running
- [ ] Dashboard hiện "API hoạt động · postgresql · schema 0001_contract_v1"
- [ ] Tab Bản đồ có nền OpenStreetMap (có Internet)
- [ ] File `import_traffic_mau.csv` mở được
- [ ] Đã chạy thử toàn bộ kịch bản ít nhất 1 lần trên đúng máy dùng khi bảo vệ
- [ ] Đã kiểm tra tin tức ngày 13/02/2024 (bão tuyết New York) để trả lời nếu hội đồng hỏi
