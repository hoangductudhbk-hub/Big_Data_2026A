# 15. Statistical analysis

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026 trên `integrated_traffic` thật (805.780 dòng).
> Báo cáo: `docs/bao-cao/15_statistics.md`
> Đầu ra cho Phase 3: `data/processed/analytics/statistics.parquet` (419 dòng), `road_stats.parquet`, `daily_stats.parquet`

## 1. Mục tiêu

Theo plan (mục 11): tính **count, mean, min, max, standard deviation, median** của hai chỉ số giao thông, nhóm theo **giờ, ngày, đường, quận, điều kiện thời tiết**. Kết quả được lưu thành bảng để backend và dashboard (Phase 3) dùng trực tiếp.

## 2. Giải trình thiết kế

### 2.1. Hai chỉ số, hai nguồn

| Chỉ số | Nguồn | Số giá trị | Ghi chú |
|---|---|---|---|
| `avg_speed` (km/h) | DOT Traffic Speeds | 789.403 | Liên tục cả năm trên 110 đường cao tốc/trục chính |
| `vehicle_count` (xe/giờ) | Automated Traffic Volume Counts | 16.530 | **Đếm theo đợt**: mỗi điểm chỉ đếm vài ngày, mỗi tháng đếm ở một nhóm điểm khác |

Hàm `describe()` **bỏ giá trị null** trước khi tính. Null ở đây nghĩa là "nguồn đó không đo" (data contract, bước 03), không phải 0. Nếu thay null bằng 0, trung bình lưu lượng sẽ sai hoàn toàn.

### 2.2. Một bảng thống kê dạng "dài" cho backend

Thay vì mỗi kiểu nhóm một bảng, mọi kết quả nằm trong **một bảng** `statistics`:

| dimension | group_key | metric | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|---|---|
| district | Manhattan | avg_speed | 138419 | 40.49 | 19.94 | 1.0 | 156.99 | 40.91 |
| hour_daytype | Ngày thường 17h | vehicle_count | … | … | … | … | … | … |

9 chiều (`overall, hour, hour_daytype, day_of_week, day_type, month, district, road, weather_condition`) × 2 chỉ số = **419 dòng**. Lợi ích: API chỉ cần **một endpoint** `GET /statistics?dimension=district&metric=avg_speed`. Muốn thêm chiều mới (ví dụ theo mùa) chỉ cần thêm một dòng trong `dimensions()`, không phải sửa database.

Hai bảng phụ phục vụ dashboard:

- `road_stats`: thống kê từng đường kèm tên, quận, tọa độ, dùng cho **bản đồ**.
- `daily_stats`: chuỗi theo ngày kèm nhiệt độ, lượng mưa/tuyết và cờ `is_outage`, dùng cho **biểu đồ thời gian**.

### 2.3. Median chính xác, không xấp xỉ

Bước 13 đã đo: ở quy mô này `percentile` chính xác nhanh hơn `percentile_approx`. Vì vậy bước này dùng bản chính xác.

### 2.4. Ngày mất dữ liệu

Bước 07 đã đánh dấu 14 ngày có độ phủ dữ liệu tốc độ < 50% (sự cố của nguồn). Thống kê theo nhóm vẫn dùng mọi bản ghi, vì trung bình không bị lệch khi thiếu dữ liệu ngẫu nhiên. Riêng **thống kê theo ngày** thì loại 14 ngày này: một ngày chỉ có vài giờ dữ liệu (ví dụ chỉ có ban đêm) sẽ cho trung bình ngày sai lệch.

## 3. Thực hiện

```bash
python -m spark_jobs.s15_statistics
```

Thời gian chạy khoảng 25 giây.

## 4. Kết quả chính

### 4.1. Tổng quan

| Chỉ số | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| avg_speed (km/h) | 789.403 | 61,0 | 26,0 | 1,0 | 157,0 | 67,0 |
| vehicle_count (xe/giờ) | 16.530 | 527 | 702 | 0 | 7.266 | 300 |

- **Median > mean ở tốc độ (67 so với 61):** phân phối lệch trái. Phần lớn thời gian xe chạy nhanh, nhưng các giờ tắc nghẽn (tốc độ rất thấp) kéo trung bình xuống.
- **Median < mean ở lưu lượng (300 so với 527), std > mean:** phân phối lệch phải mạnh. Một số ít điểm đếm rất đông (Grand Central Parkway, trung bình 4.300 xe/giờ) kéo trung bình lên. Với dữ liệu kiểu này, **median đại diện tốt hơn mean**.

### 4.2. Theo giờ

| Giờ (ngày thường) | 3h | 8h | 13h | **16h–17h** | 20h |
|---|---|---|---|---|---|
| Tốc độ TB (km/h) | 78,3 | 52,4 | 54,8 | **44,1–44,2** | 62,5 |
| Lưu lượng TB (xe/giờ) | 111 | 758 | 729 | **823–824** | 620 |

- Ngày thường có **2 đỉnh lưu lượng**: sáng 7–8h (khoảng 755 xe/giờ) và chiều 15–17h (khoảng 820 xe/giờ). Tốc độ thấp nhất lúc 16h. **Cao điểm chiều nặng hơn cao điểm sáng.**
- Cuối tuần **không có cao điểm sáng**: lúc 6h tốc độ đạt 78,3 km/h (ngày thường chỉ 62,5). Lưu lượng tăng dần đến đỉnh khoảng 15h (682 xe/giờ).
- Nửa đêm cuối tuần (0–3h) **đông xe hơn ngày thường** (344 so với 281 xe/giờ lúc 0h): hoạt động về đêm của tối thứ Sáu và thứ Bảy.

### 4.3. Theo ngày trong tuần

Chủ nhật nhanh nhất (65,1 km/h), **thứ Năm chậm nhất (58,7 km/h)**. Tốc độ giảm dần từ thứ Hai đến thứ Năm và hơi tăng vào thứ Sáu. Lưu lượng cao nhất thứ Ba đến thứ Năm (khoảng 600–615 xe/giờ), thấp nhất Chủ nhật (431).

### 4.4. Theo quận

| Quận | Tốc độ TB | Median | Lưu lượng TB |
|---|---|---|---|
| Staten Island | **79,4** | 86,2 | 102 |
| Bronx | 62,2 | 70,3 | 497 |
| Queens | 62,2 | 69,2 | 472 |
| Brooklyn | 54,9 | 63,3 | 375 |
| Manhattan | **40,5** | 40,9 | **938** |

Manhattan **chậm nhất và đông xe nhất**. Staten Island ngược lại. Tốc độ phụ thuộc vào loại đường các cảm biến đo: Staten Island chủ yếu là cao tốc (West Shore, Staten Island Expressway), còn Manhattan có nhiều đại lộ, cầu và hầm.

### 4.5. Theo đường

- **Chậm nhất:** 11th Avenue (9,3 km/h), 12th Avenue (9,9), BQE đoạn Manhattan (11,0), Belt Parkway (17,1).
- **Nhanh nhất:** West Shore Expressway (88–95 km/h), Bruckner Expressway (87,9), Staten Island Expressway (85,2).
- **Biến động lớn nhất (std):** **Cross Bronx Expressway** chiếm 5/10 vị trí (std tới 33,8 km/h). Đường này lúc thông thì nhanh, lúc tắc thì rất chậm. Std cao là dấu hiệu tắc nghẽn theo giờ, khác với "chậm đều" như 11th Avenue (std thấp, mean thấp).
- **Lưu lượng cao nhất:** Grand Central Parkway (4.300 xe/giờ), FDR Drive (2.761), Henry Hudson Parkway (2.647).

### 4.6. Theo ngày

344 ngày đủ dữ liệu: tốc độ trung bình ngày 61,0 ± 3,6 km/h. **4/5 ngày chậm nhất đều có mưa lớn** (11/12: 38,9 mm; 21/11: 47,5 mm; 28/3: 24,9 mm; 16/12: 15,7 mm). Đây là gợi ý đầu tiên cho bước 16.

### 4.7. Theo thời tiết: số liệu thô, chưa kết luận

| Thời tiết | Tốc độ TB | Chênh với Clear |
|---|---|---|
| Clear | 61,6 | — |
| Cloudy | 61,2 | −0,7% |
| Drizzle | 58,4 | −5,3% |
| Rain | 57,5 | **−6,6%** |
| Snow | 62,0 | **+0,6%** |

Nhìn bảng thô có thể nghĩ "mưa làm chậm 6,6%, còn tuyết không ảnh hưởng". **Kết luận như vậy là chưa đủ cơ sở**, vì các nhóm thời tiết khác nhau về *giờ*, *ngày* và *đường*. Ví dụ, nếu tuyết hay rơi vào ban đêm hay cuối tuần (lúc đường vắng) thì tốc độ lúc có tuyết tự nhiên sẽ cao. Đây là **biến gây nhiễu (confounding)**. Bước 16 sẽ so sánh có kiểm soát: cùng đường, cùng giờ, cùng loại ngày.

## 5. Những điều cần nói rõ khi trình bày

- **Lưu lượng theo tháng không so sánh được với nhau.** Tháng 10 trung bình 932 xe/giờ, tháng 1 chỉ 220, nhưng đó là do **đếm ở các điểm khác nhau**, không phải tháng 10 đông xe hơn. Tháng 7 và 8 không có đợt đếm nào. Các so sánh lưu lượng có ý nghĩa nhất là **theo giờ trong ngày**, vì mỗi đợt đếm đều phủ đủ 24 giờ.
- Tương tự, lưu lượng theo quận phụ thuộc vào việc đếm ở đường nào. Staten Island chỉ có 96 giờ đếm.
- Tốc độ là **tốc độ của đoạn đường có cảm biến** (chủ yếu cao tốc và trục chính), không phải tốc độ trung bình của mọi con đường trong thành phố.

## 6. Kiểm tra

- [x] Tổng `n` của `avg_speed` = 789.403 = 805.780 − 16.377 dòng chỉ có lưu lượng (bước 10). Khớp.
- [x] Tổng `n` của `vehicle_count` = 16.530 = 16.377 + 153 dòng có cả hai nguồn. Khớp.
- [x] **Kiểm tra độc lập:** tính lại n, mean, std, median của Manhattan bằng pandas, kết quả **trùng 4/4** với Spark (mục cuối của báo cáo).
- [x] Giờ cao điểm ở mục 4.2 khớp với kết quả `hourly_profile` của bước 11.

## 7. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| `AssertionError` khi import module: bảng các chiều dùng `F.lit`/`F.col` ở cấp module | Giống lỗi ở bước 12: biểu thức Spark cần SparkSession đang chạy. Chuyển thành hàm `dimensions()` |
| Ban đầu tính lượng mưa ngày bằng tổng chia số (quận × giờ), công thức rối và dễ sai | Đổi thành trung bình mưa mỗi giờ × 24, ghi rõ là trung bình theo các bản ghi |
