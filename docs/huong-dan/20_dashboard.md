# 20. Dashboard

> **Trạng thái:** ✅ Hoàn thành ngày 14/10/2026. Đã kiểm tra trên trình duyệt (Chromium), giao diện sáng và tối, màn hình máy tính và điện thoại.
> Code: `backend/dashboard/` (`index.html`, `app.js`, `style.css`, `vendor/`) · Địa chỉ: `http://localhost:8000/`

## 1. Mục tiêu

Theo plan (mục 17 và 18): luồng dữ liệu kết thúc ở **Dashboard / visualization**. Người xem (giảng viên, người điều hành giao thông) phải thấy được kết quả của cả ba phase mà không cần đọc code hay SQL.

## 2. Giải trình thiết kế

### 2.1. Kiến trúc: trang tĩnh gọi API

```
Trình duyệt ──GET /dashboard/──► FastAPI (StaticFiles) ── trả về index.html, app.js
     │
     └──GET /api/v1/...──► FastAPI ──► PostgreSQL
```

- **Không có server riêng cho dashboard.** FastAPI phục vụ luôn các file tĩnh, nên chỉ cần chạy một tiến trình.
- **Dashboard chỉ dùng API công khai**, không truy cập database trực tiếp. Mọi thứ dashboard làm được thì client khác cũng làm được qua API. Điều này chứng minh API đủ dùng.
- **Không dùng framework (React, Vue).** HTML + JavaScript thuần, không cần bước build. Phù hợp phạm vi đồ án (plan: "không làm hệ thống phức tạp").
- **Thư viện để sẵn trong `vendor/`** (Chart.js 4.4.1, Leaflet 1.9.4, kèm giấy phép). Dashboard chạy được khi không có Internet. Riêng nền bản đồ OpenStreetMap cần mạng.

### 2.2. Nguyên tắc trình bày số liệu

| Nguyên tắc | Áp dụng |
|---|---|
| Mỗi biểu đồ chỉ một trục y | Tốc độ và lưu lượng theo giờ là **hai biểu đồ riêng**, không vẽ chung hai trục (biểu đồ hai trục dễ tạo ra "tương quan" giả) |
| Màu theo ý nghĩa, không trang trí | Xanh = ngày thường / chỉ số chính, cam = cuối tuần / so sánh thô. Bản đồ dùng thang **phân kỳ** đỏ – xám – xanh quanh trung vị (chậm hơn / như thường / nhanh hơn) |
| Bảng màu kiểm tra mù màu bằng công cụ | Cặp xanh–cam đạt ngưỡng phân biệt với người mù màu (ΔE 9,2, ngưỡng 8) ở cả giao diện sáng và tối |
| Không để màu là kênh duy nhất | Có chú giải (legend) cho mọi biểu đồ có từ 2 chuỗi trở lên, và mọi biểu đồ có **bảng số liệu** đi kèm |
| Dữ liệu kém tin cậy được đánh dấu | Ngày mất dữ liệu (độ phủ < 50%) vẽ màu xám; bất thường lưu lượng ghi "chỉ để tham khảo" |
| Tooltip khi rê chuột | Hiện giá trị, kèm ngữ cảnh (mưa, tuyết, độ phủ dữ liệu) |
| Giao diện tối | Bảng màu riêng cho nền tối, theo cài đặt của hệ điều hành |

### 2.3. Bảo mật

- Tên đường, tên quận lấy từ API đều được đưa vào trang bằng `textContent`, không dùng `innerHTML`. Dữ liệu import từ bên ngoài không thể chèn mã vào dashboard.
- Dashboard chỉ **đọc**, trừ tab "Nhập dữ liệu" (gọi endpoint import, vẫn được kiểm tra theo contract ở server).

## 3. Các tab

| Tab | Nội dung | API dùng |
|---|---|---|
| **Tổng quan** | 5 ô số liệu; tốc độ và lưu lượng theo giờ (ngày thường / cuối tuần); tốc độ mỗi ngày + lượng mưa; tốc độ theo quận + bảng | `statistics/summary`, `statistics?dimension=hour_daytype`, `statistics/daily`, `statistics?dimension=district` |
| **Bản đồ** | 110 đường có cảm biến tô màu theo tốc độ, hoặc 103 điểm đếm có kích thước theo lưu lượng; bấm vào một đường → thông tin, biểu đồ theo tuần, các bất thường mạnh nhất | `roads`, `statistics?dimension=road`, `roads/{id}`, `traffic/timeseries`, `anomalies?road_id=` |
| **Thời tiết** | So sánh thô và có kiểm soát (bước 16); theo lượng mưa; theo nhiệt độ; tóm tắt kết luận | `statistics/weather-impact` |
| **Bất thường** | Bộ lọc (chỉ số, quận, hướng, \|z\| tối thiểu); số bất thường mỗi ngày; danh sách phân trang. Bấm một dòng → mở đường đó trên bản đồ | `anomalies`, `anomalies/summary`, `anomalies/daily` |
| **Thống kê** | Chọn chiều + chỉ số → biểu đồ và bảng count/mean/std/min/median/max; truy vấn trực tiếp PostgreSQL theo khoảng ngày | `statistics/dimensions`, `statistics`, `statistics/live` |
| **Nhập dữ liệu** | Tải file CSV/JSON/Parquet → kết quả từng dòng; nhật ký nạp | `import/{traffic,weather}/file`, `import/logs` |

## 4. Hình ảnh

Ảnh chụp trong môi trường phát triển không có Internet, nên bản đồ không có nền OpenStreetMap; trên máy có mạng sẽ có nền đường phố.

| Tab | Ảnh |
|---|---|
| Tổng quan | `hinh/20_dashboard_overview.png` |
| Bản đồ | `hinh/20_dashboard_map.png` |
| Thời tiết | `hinh/20_dashboard_weather.png` |
| Bất thường | `hinh/20_dashboard_anomalies.png` |
| Thống kê | `hinh/20_dashboard_stats.png` |
| Nhập dữ liệu | `hinh/20_dashboard_import.png` |

**Những gì dashboard cho thấy ngay:**

- Hai biểu đồ theo giờ: cao điểm sáng chỉ có ở ngày thường; cao điểm chiều 16–17h là chậm nhất (bước 15).
- Biểu đồ theo ngày: các ngày tốc độ thấp thường trùng ngày mưa lớn (bước 16).
- Biểu đồ bất thường: đỉnh nhọn ngày 13/02 (trận tuyết), chuỗi bất thường tháng 6–7 (West Shore Expressway) (bước 17).
- Bản đồ: Manhattan và hầm/cầu đỏ (chậm), Staten Island xanh (nhanh).

## 5. Thực hiện

```bash
cd backend && uvicorn app.main:app      # rồi mở http://localhost:8000
```

Không cần cài gì thêm cho dashboard.

## 6. Kiểm tra

- [x] Mở cả 6 tab bằng trình duyệt tự động (Playwright): **không có lỗi JavaScript**, không có request lỗi (trừ nền bản đồ khi không có mạng).
- [x] Số trên ô tổng quan khớp với kiểm tra end-to-end (805.780 bản ghi, 211 đường, 13.678 bất thường).
- [x] Bảng "Truy vấn trực tiếp" (SQL) khớp với bảng "Spark tính sẵn" khi không lọc thời gian.
- [x] Tải file mẫu `backend/examples/import_traffic_mau.csv`: thêm 4 dòng, từ chối 2 dòng kèm lý do, nhật ký cập nhật ngay.
- [x] Giao diện tối và màn hình rộng 390 px (điện thoại): chữ đọc được, không tràn ngang.

## 7. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| Môi trường phát triển không tải được thư viện từ CDN | Đưa thư viện vào `vendor/` (tải bằng npm, kèm giấy phép). Kết quả tốt hơn: dashboard chạy được khi không có mạng |
| Bảng ở tab Tổng quan không hiện: `f.format is not a function` | Hàm định dạng nhận nhầm tham số thứ hai. Sửa cách gọi |
| Mở thẳng `/dashboard/#map` không chuyển tab | Thêm xử lý sự kiện `hashchange` |
| Ô "Thời gian" ghi cứng "2024", sai khi import dữ liệu năm 2025 | Lấy năm từ dữ liệu thật trong `statistics/summary` |
