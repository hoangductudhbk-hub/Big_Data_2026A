# 04. Mock dataset `integrated_traffic`

## 1. Mục tiêu

Sinh một bộ dữ liệu **giả nhưng đúng contract** để Phase 2 (PySpark) bắt đầu ngay, không phải chờ Phase 1 xong. Đây là đầu ra cuối của Phase 0 trong plan ("Mock integrated dataset"), và là cách plan dùng để Người 3 không phụ thuộc vào Người 2 (mục 15 của plan).

> ⚠️ Mock dataset **chỉ dùng để phát triển và test code**. Mọi số liệu trong báo cáo cuối phải chạy trên dữ liệu thật (`data/processed/integrated_traffic`).

## 2. Giải trình

### 2.1. Vì sao mock phải "giống thật"

Nếu mock chỉ là số ngẫu nhiên, code Phase 2 vẫn chạy nhưng không kiểm chứng được logic phân tích. Vì vậy mock được thiết kế có sẵn các **mẫu hình đã biết trước**. Khi chạy phân tích trên mock, kết quả phải tìm lại được đúng các mẫu hình này. Đây là cách kiểm thử (test) cho code phân tích.

| Mẫu hình cài sẵn | Cách sinh | Phase 2 phải phát hiện được |
|---|---|---|
| Giờ cao điểm sáng và chiều, cuối tuần vắng hơn | Hệ số lưu lượng theo giờ dạng 2 đỉnh Gauss quanh 8h và 17h30 | Bước 15: thống kê theo giờ |
| Đông xe thì chậm | Hàm BPR: `speed = free_flow / (1 + (v/c)^4)` | Tương quan âm giữa lưu lượng và tốc độ |
| Thời tiết xấu làm chậm xe | Mưa giảm khoảng 12–27%, tuyết khoảng 25–40%, giông thêm 10% | Bước 16: weather vs traffic |
| Mưa và tuyết kéo dài nhiều giờ | Chuỗi Markov: đang mưa thì xác suất mưa tiếp là 0,85 | Phân bố thời gian mưa hợp lý |
| Nhiệt độ theo mùa và theo ngày | Hàm cos theo ngày trong năm, sin theo giờ | Tuyết chỉ xuất hiện khi lạnh |
| Bất thường | 0,1% số dòng: tốc độ ×0,25, lưu lượng ×3,5 | Bước 17: Z-score |
| Mất dữ liệu cảm biến | Bỏ ngẫu nhiên 2% số giờ | Code phải chịu được dữ liệu thiếu |
| Đường chỉ có một loại cảm biến | `source` = speeds / volume / speeds+volume | Code phải xử lý được giá trị null |

### 2.2. Bài học rút ra khi kiểm tra mock

Phiên bản đầu của mock dùng công thức `speed = free_flow × (1 − tắc nghẽn)`. Khi kiểm tra bằng Spark, kết quả cho thấy **trời tuyết xe lại chạy nhanh nhất**:

| Thời tiết | Tốc độ TB (mọi giờ) | Tỉ lệ giờ đêm (0–5h) |
|---|---|---|
| Snow | 42,1 km/h | **46,3%** |
| Clear | 37,9 km/h | 25,0% |

Có hai nguyên nhân:

1. **Biến gây nhiễu (confounding):** tuyết rơi nhiều vào ban đêm (vì trời lạnh), mà ban đêm đường vắng nên xe chạy nhanh. So sánh gộp mọi giờ sẽ ra kết luận sai.
2. **Mô hình quá nhạy:** lưu lượng chỉ giảm 15% nhưng tốc độ ở giờ cao điểm tăng gấp đôi, lấn át tác động làm chậm của thời tiết.

Cách sửa: dùng **hàm BPR**, công thức chuẩn trong kỹ thuật giao thông, và luôn **so sánh trong cùng khung giờ**. Kết quả sau khi sửa, tính trong cùng khung 7–9h ngày thường:

| Thời tiết | Tốc độ TB |
|---|---|
| Clear | 29,5 km/h |
| Cloudy | 29,4 km/h |
| Rain | 26,1 km/h |
| Snow | 23,2 km/h |
| Thunderstorm | 19,6 km/h |

> **Áp dụng cho bước 16:** khi phân tích tác động của thời tiết trên dữ liệu thật, phải kiểm soát khung giờ và loại ngày (ngày thường hay cuối tuần). Không được so trung bình gộp.

## 3. Thực hiện

```bash
# Mặc định: 200 đường × cả năm 2024
python scripts/generate_mock_integrated.py

# Bộ nhỏ để test nhanh
python scripts/generate_mock_integrated.py --roads 20 --start 2024-01-01 --end 2024-01-07

# Bộ lớn để thử benchmark (khoảng 8,6 triệu dòng)
python scripts/generate_mock_integrated.py --roads 1000 --out data/mock/integrated_traffic_1000
```

Script làm các việc sau:

1. Sinh danh mục đường, gồm quận, tọa độ, tốc độ tự do và lưu lượng nền.
2. Sinh thời tiết theo quận và giờ.
3. Nhân chéo đường × giờ, rồi tính lưu lượng và tốc độ theo các mẫu hình ở mục 2.1.
4. Chạy `validate_pandas()` của contract. Nếu không đạt contract, script dừng và báo lỗi.
5. Ghi Parquet, chia partition theo `year/month`.

## 4. Kết quả (chạy thực tế)

```text
Đạt contract. 1,721,535 dòng, 200 đường → data/mock/integrated_traffic (19.8 MB)
source
speeds           929613
volume           550873
speeds+volume    241049
```

- Thời gian sinh khoảng 3 giây.
- Spark đọc lại được, schema khớp contract (`type mismatch: []`) và có 12 partition tháng.
- Lưu lượng và tốc độ trung bình theo giờ (Spark):

| Giờ | Xe/giờ | km/h |
|---|---|---|
| 3h | 294 | 65,3 |
| 8h | 1.466 | 33,0 |
| 12h | 915 | 56,9 |
| 17h | 1.664 | 27,4 |
| 22h | 419 | 65,2 |

- Z-score theo từng đường × giờ × (ngày thường/cuối tuần): có **2.442** điểm |z| > 3 trên 791.922 dòng có lưu lượng (0,31%).

## 5. Kiểm tra

- [ ] Script in ra `Đạt contract`.
- [ ] Đọc bằng Spark:

```python
df = spark.read.parquet("data/mock/integrated_traffic")
df.printSchema()      # 14 cột contract + year, month
```

## 6. Khi có dữ liệu thật

Ở Phase 2 chỉ cần đổi **một** đường dẫn, từ `data/mock/integrated_traffic` thành `data/processed/integrated_traffic`. Code Phase 2 nên đọc đường dẫn này từ tham số hoặc biến môi trường, không viết cứng trong code.
