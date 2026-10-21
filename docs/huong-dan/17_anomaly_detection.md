# 17. Anomaly detection bằng Z-score

> **Trạng thái:** ✅ Hoàn thành ngày 14/10/2026. Đã kiểm chứng trên mock có đáp án, rồi chạy trên dữ liệu thật.
> Báo cáo: `docs/bao-cao/17_anomaly.md` (dữ liệu thật), `docs/bao-cao/17_anomaly_mock.md` (kiểm chứng)
> Đầu ra cho Phase 3: `data/processed/analytics/anomalies.parquet` (13.678 bản ghi), `anomaly_daily.parquet`

## 1. Mục tiêu

Theo plan (mục 13): phát hiện bản ghi bất thường bằng `z = (x − mean) / std`, đánh dấu `|z| > 3`. Đầu ra gồm `road_id, timestamp, vehicle_count, z_score, is_anomaly`. Áp dụng cho cả `vehicle_count` và `avg_speed`.

## 2. Giải trình thiết kế

### 2.1. "mean" và "std" của cái gì?

Plan chỉ cho công thức, không nói lấy mean/std từ đâu. Đây là quyết định quan trọng nhất của bước này. Thí nghiệm so sánh hai cách:

| Cách | mean, std tính trên | Vấn đề |
|---|---|---|
| **Toàn cục theo đường** | Mọi giờ trong năm của đường đó | Tốc độ 40 km/h lúc 17h là **bình thường** (ngày nào cũng tắc), nhưng so với trung bình cả ngày 70 km/h thì bị coi là "bất thường". Ngược lại, 40 km/h lúc 3h sáng thật sự bất thường nhưng lại bị bỏ sót |
| **Theo ngữ cảnh** (được chọn) | Cùng đường × **cùng giờ** × **cùng loại ngày** (ngày thường / cuối tuần + lễ) | So mỗi bản ghi với "bình thường của đúng thời điểm đó" |

### 2.2. Leave-one-out: một giới hạn toán học của Z-score

Lần chạy đầu, Z-score theo ngữ cảnh cho lưu lượng xe phát hiện **0 bất thường**. Nguyên nhân không phải do dữ liệu "sạch", mà do một tính chất toán học:

> Với n giá trị, Z-score (khi mean và std tính trên **chính n giá trị đó**) luôn thỏa **|z| ≤ (n − 1)/√n**.
> n = 5 → |z| ≤ 1,79 · n = 10 → |z| ≤ 2,85 · cần n ≥ 11 mới có thể vượt 3.

Dữ liệu lưu lượng đếm theo đợt 1–2 tuần, nên mỗi ô (điểm đếm × giờ × loại ngày) chỉ có 5–10 giá trị. **Không giá trị nào có thể đạt |z| > 3**, dù lạ đến đâu. Ngoài ra, chính giá trị bất thường làm std phình ra và tự "che" mình (*masking*).

**Cách xử lý: leave-one-out (LOO).** Khi chấm điểm một bản ghi, mean và std được tính trên **các bản ghi khác** trong ô, không gồm nó. Tính bằng window function với tổng và tổng bình phương, không cần join:

```
mean₋ᵢ = (S − x) / (n − 1)
var₋ᵢ  = (Q − x² − (n−1)·mean₋ᵢ²) / (n − 2)        S = Σx, Q = Σx² của cả ô
z      = (x − mean₋ᵢ) / std₋ᵢ
```

Với ô lớn (tốc độ có khoảng 150–250 giá trị mỗi ô), LOO cho kết quả gần giống cách thường: 13.503 so với 12.395 bất thường (+9%), phần tăng thêm chính là những điểm trước đó bị masking. Với ô nhỏ, LOO là cách duy nhất để Z-score có ý nghĩa. Cách toàn cục được giữ nguyên công thức gốc của plan để so sánh.

### 2.3. Kiểm chứng trước khi tin

Dữ liệu thật **không có đáp án** (không ai gắn nhãn "giờ này bất thường"). Vì vậy:

1. Sửa `scripts/generate_mock_integrated.py` để ghi danh sách **bất thường đã cài** (0,1% bản ghi: tốc độ × 0,25, lưu lượng × 3,5) ra `data/mock/injected_anomalies.parquet`.
2. Chạy bước 17 trên mock với `--validate` để đo **precision, recall**.
3. Chạy trên dữ liệu thật và **đối chiếu** các bất thường lớn với sự kiện đã biết (bước 16).

## 3. Thực hiện

```bash
python scripts/generate_mock_integrated.py                       # sinh mock + đáp án
INTEGRATED_PATH=data/mock/integrated_traffic python -m spark_jobs.s17_anomaly --validate
python -m spark_jobs.s17_anomaly                                 # dữ liệu thật, khoảng 45 giây
```

(Windows PowerShell: `$env:INTEGRATED_PATH="data/mock/integrated_traffic"` trước lệnh thứ hai.)

## 4. Kết quả kiểm chứng trên mock

Mock có 1.205 bất thường tốc độ và 746 bất thường lưu lượng được cài sẵn.

| Chỉ số | Cách | Báo | Đúng | Precision | Recall |
|---|---|---|---|---|---|
| Tốc độ | Toàn cục theo đường | 22 | 22 | 1,00 | **0,02** |
| Tốc độ | Theo ngữ cảnh (LOO) | 11.906 | 1.175 | 0,10 | **0,97** |
| Lưu lượng | Toàn cục theo đường | 450 | 450 | 1,00 | 0,60 |
| Lưu lượng | Theo ngữ cảnh (LOO) | 6.188 | 746 | 0,12 | **1,00** |

**Nhận xét:**

1. **Cách toàn cục gần như mù với bất thường tốc độ: chỉ bắt được 2%.** Tốc độ dao động mạnh trong ngày, nên std toàn cục rất lớn và cú giảm tốc 75% vẫn chưa vượt 3 std. 95% số bất thường nó báo lại rơi vào giờ cao điểm.
2. **Cách theo ngữ cảnh bắt được 97–100%** bất thường đã cài.
3. **Vì sao precision thấp (0,10)?** Trong các bản ghi bị báo nhưng không phải bất thường cài sẵn, **95% rơi vào giờ mưa/tuyết**. Mock cố ý làm xe chậm 12–25% khi mưa/tuyết (bước 04), và đó *thật sự* là trạng thái khác thường so với lúc khô ráo. Z-score báo đúng là "lạ", chỉ là không nằm trong danh sách đã cài.
4. **Đánh đổi theo ngưỡng (tốc độ):**

| Ngưỡng | Precision | Recall | F1 |
|---|---|---|---|
| \|z\| > 3 (plan) | 0,10 | 0,97 | 0,18 |
| \|z\| > 4 | 0,54 | 0,93 | 0,68 |
| \|z\| > 5 | **0,97** | 0,89 | **0,93** |

Ngưỡng 3 của plan cho recall cao nhất (ít bỏ sót) nhưng báo nhiều. **Báo cáo giữ ngưỡng 3 theo plan**, và dashboard có thể lọc theo `|z|` (cột `z_score` được lưu sẵn) để người dùng tự chọn mức độ.

## 5. Kết quả trên dữ liệu thật

### 5.1. Tổng quan

| Chỉ số | Cách | Được chấm | Bất thường | Tỉ lệ | Thấp / Cao | Rơi vào giờ cao điểm |
|---|---|---|---|---|---|---|
| Tốc độ | Toàn cục | 789.403 | 7.726 | 0,98% | 7.084 / 642 | **36,1%** |
| Tốc độ | **Ngữ cảnh (LOO)** | 788.360 | **13.503** | 1,71% | 11.509 / 1.994 | 13,4% |
| Lưu lượng | Toàn cục | 16.530 | 12 | 0,07% | 0 / 12 | 58,3% |
| Lưu lượng | **Ngữ cảnh (LOO)** | 3.952 | **175** | 4,43% | 57 / 118 | 25,7% |

- **Cách toàn cục báo bất thường ở giờ cao điểm** (36% tốc độ, 58% lưu lượng), đúng như dự đoán ở mục 2.1. Cách theo ngữ cảnh giảm tỉ lệ này xuống 13%, gần với tỉ lệ giờ cao điểm trong dữ liệu (6/24 giờ × 5/7 ngày ≈ 18%).
- Tỉ lệ 1,71% **cao hơn 0,27%** của phân phối chuẩn. Tốc độ có **đuôi dày**: tắc nghẽn do sự cố, thi công làm tốc độ giảm sâu hơn nhiều so với phân phối chuẩn dự đoán. Vì vậy 85% bất thường là **chậm bất thường**.
- **44% bất thường tốc độ nối tiếp nhau trong cùng một đường** (giờ kế tiếp cũng bất thường). Bất thường thật thường là **sự kiện kéo dài vài giờ**, không phải nhiễu đơn lẻ. Đây là dấu hiệu tốt cho thấy phương pháp bắt được hiện tượng có thật.

### 5.2. Bất thường mạnh nhất

| Đường | Thời điểm | Tốc độ | Bình thường | z |
|---|---|---|---|---|
| West Shore Expressway | 23/06 21–22h | 5–7 km/h | 97 km/h | −30 |
| Staten Island Expressway | 26/09 1–2h | 2–2,5 km/h | 91 km/h | −29 |
| Cross Bronx Expressway | 17/02 0h (tuyết) | 5,5 km/h | 87 km/h | −22 |
| Long Island Expressway | 03/10 4h | 14,8 km/h | 93 km/h | −21 |

Tốc độ 2–7 km/h lúc nửa đêm trên cao tốc thường 90+ km/h: rất có thể là **đóng làn hoặc đóng đường để thi công ban đêm**, hoặc tai nạn. *Nhóm không kiểm chứng được nguyên nhân từng trường hợp (không có dữ liệu sự cố); đây là giả thuyết.*

### 5.3. Đường có nhiều bất thường nhất: phát hiện được "giai đoạn" chứ không chỉ "thời điểm"

**West Shore Expressway (L4616201)** có 363 bất thường, **tất cả là chậm**. 263 trong số đó nằm ở tháng 6 và 99 ở tháng 7, rải đều mọi giờ trong ngày. Đây không phải 363 sự cố riêng lẻ mà là **một giai đoạn kéo dài khoảng 6 tuần** đường bị chậm liên tục, nhiều khả năng do công trình. Tương tự, Triborough Bridge (L4616225) tập trung vào tháng 1, 7 và 12.

> **Giới hạn của Z-score:** baseline tính trên cả năm, nên một giai đoạn kéo dài (thi công 6 tuần) sẽ bị báo **mọi giờ** trong giai đoạn đó. Nếu giai đoạn đủ dài, nó còn làm lệch chính baseline. Phương pháp tốt hơn cho trường hợp này là baseline trượt (rolling, ví dụ 4 tuần gần nhất) hoặc phát hiện điểm thay đổi (change-point detection). Plan không yêu cầu, nên nhóm ghi nhận là hướng phát triển.

### 5.4. Những ngày bất thường của cả thành phố

Khi **nhiều đường cùng bất thường trong một ngày**, nguyên nhân là sự kiện chung. Đối chiếu với bước 16:

| Ngày | Bất thường | Giải thích |
|---|---|---|
| **13/02** | **10,7%** (207 nhanh, 45 chậm), cao nhất năm | Trận tuyết 16 cm, người dân ở nhà, đường vắng (bước 16, mục 4.4) |
| 04/07, 05/07 | 7,0–7,4%, cả nhanh lẫn chậm | Quốc khánh Mỹ: sáng vắng, tối đông đi xem pháo hoa |
| 01/01 – 04/01 | 2–7%, chủ yếu nhanh | Tuần nghỉ lễ đầu năm: nhiều người chưa đi làm |
| 17/02, 21/12 | 4,6–6,0%, chậm | Ngày có tuyết (3,9 cm và 2,3 cm) |
| 29/01 | 5,3% | **Độ phủ dữ liệu chỉ 34,5%**: ngày thiếu dữ liệu, không phải sự kiện giao thông |

- **Phương pháp tìm lại được đúng các sự kiện đã biết** mà không cần được "chỉ" trước: trận tuyết lớn nhất, các ngày lễ. Đây là bằng chứng gián tiếp quan trọng nhất về độ tin cậy trên dữ liệu thật.
- Ngày 01/01 và 04/07 được xếp vào "cuối tuần", nhưng giao thông ngày lễ lớn vẫn khác cuối tuần thường, nên vẫn bị báo bất thường. Điều này hợp lý.
- Ngày 13/12 và 14/12 (5,2% và 4,3%, chậm, không có thời tiết xấu) **chưa giải thích được**. Có thể do sự kiện mua sắm cuối năm. Cần thêm dữ liệu sự kiện.

### 5.5. Lưu lượng xe: kết quả chỉ để tham khảo

Chỉ 3.952 / 16.530 giờ đếm được chấm điểm (ô cần ≥ 6 giá trị khác). Tỉ lệ bất thường 4,43% là **quá cao**: std ước lượng từ 6–9 giá trị rất không ổn định. Ví dụ, DeKalb Avenue 439 xe so với kỳ vọng 362 cho z = 23, chỉ vì 6 giờ còn lại có giá trị gần như bằng nhau (std ≈ 3). **Dữ liệu đếm theo đợt ngắn không đủ để phát hiện bất thường lưu lượng đáng tin cậy.** Kết quả vẫn được lưu nhưng dashboard cần ghi chú điều này.

## 6. Đầu ra

`anomalies.parquet`: đúng các cột plan yêu cầu, cộng thêm ngữ cảnh để dashboard hiển thị:

| Cột | Ý nghĩa |
|---|---|
| `road_id`, `timestamp`, `vehicle_count`, `z_score`, `is_anomaly` | Theo plan |
| `metric` | `avg_speed` hoặc `vehicle_count`: chỉ số nào bất thường |
| `value`, `expected`, `std` | Giá trị thực, giá trị bình thường của ngữ cảnh, độ lệch chuẩn |
| `direction` | "thấp bất thường" / "cao bất thường" |
| `avg_speed`, `weather_condition`, `rainfall`, `snowfall`, `road_name`, `district` | Ngữ cảnh để giải thích |

`anomaly_daily.parquet`: mỗi ngày một dòng, gồm số bất thường chậm/nhanh, tỉ lệ, lượng mưa/tuyết, độ phủ dữ liệu.

## 7. Kết luận cho phần giải trình

| Câu hỏi | Trả lời |
|---|---|
| Công thức | `z = (x − mean)/std`, `\|z\| > 3`, đúng plan |
| mean/std lấy từ đâu | Theo ngữ cảnh (đường × giờ × loại ngày), leave-one-out. Cách toàn cục chỉ bắt 2% bất thường tốc độ trên mock |
| Có tin được không? | Mock: recall 97–100%. Dữ liệu thật: tìm lại được trận tuyết 13/02 và các ngày lễ mà không cần được chỉ trước |
| Hạn chế | Ngưỡng 3 báo nhiều (precision 0,10 trên mock; ngưỡng 5 cho F1 0,93). Không phân biệt sự cố ngắn với giai đoạn thi công dài. Lưu lượng: không đủ dữ liệu |

## 8. Kiểm tra

- [x] Mock: recall ≥ 0,97 với cách theo ngữ cảnh; số bất thường cài sẵn khớp với file đáp án.
- [x] `is_anomaly` = True ⇔ `|z_score|` > 3 trên mọi dòng của `anomalies.parquet` (file chỉ lưu dòng bất thường).
- [x] Ngày bất thường nhất (13/02) trùng với kết luận độc lập của bước 16.
- [x] 39 test của Phase 0–1 vẫn đạt sau khi sửa `generate_mock_integrated.py`.

## 9. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| Lưu lượng theo ngữ cảnh: **0 bất thường** | Giới hạn \|z\| ≤ (n−1)/√n với ô nhỏ. Chuyển sang leave-one-out |
| Mock không có nhãn bất thường nên không đo được precision/recall | Sửa script sinh mock để ghi file đáp án `injected_anomalies.parquet` (không thuộc contract, không ảnh hưởng `integrated_traffic`) |
| Precision trên mock thấp, tưởng là lỗi | Phân tích các báo thừa: 95% rơi vào giờ mưa/tuyết, đúng là trạng thái khác thường do mock cố ý tạo ra. Thêm bảng thay đổi ngưỡng để thấy đánh đổi |
| Máy ảo mất kết nối giữa chừng | Phát triển và kiểm chứng trên mock trong môi trường cloud (PySpark 4.0.1), rồi chạy dữ liệu thật trên máy ảo khi có kết nối lại. Code chạy được trên cả Spark 3.5 và 4.0 |
