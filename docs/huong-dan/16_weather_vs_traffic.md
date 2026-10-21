# 16. Tác động của thời tiết lên giao thông

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026 trên dữ liệu thật.
> Báo cáo: `docs/bao-cao/16_weather_impact.md` · Đầu ra: `data/processed/analytics/weather_impact.parquet`

## 1. Mục tiêu

Theo plan (mục 12): phân tích mối quan hệ **Rainfall → Vehicle Count / Speed** và **Weather Condition → Average Speed** bằng thống kê theo nhóm và tương quan đơn giản, không dùng Machine Learning. Đây cũng là lý do thời tiết được tích hợp vào `integrated_traffic` từ Phase 1.

## 2. Giải trình: vì sao không thể chỉ so sánh trung bình

Bước 15 cho kết quả thô: mưa chậm hơn trời quang 6,6%, còn **tuyết lại nhanh hơn 0,6%**. Tuyết làm xe chạy nhanh hơn là điều vô lý về mặt vật lý. Nguyên nhân là **biến gây nhiễu (confounding)**:

```
  giờ trong ngày, loại ngày, đường, MÙA ──► tốc độ
          │
          └──► thời tiết (tuyết chỉ có vào mùa đông, mưa phân bố không đều theo giờ)
```

Ví dụ: tuyết chỉ rơi vào tháng 1, 2 và 12. Tháng 1 vốn là tháng vắng xe nhất (tốc độ TB 64,7 km/h so với 58,7 của tháng 5, theo bước 15). So "giờ có tuyết" với "mọi giờ khác" thực chất là so **mùa đông với cả năm**.

### 2.1. Phương pháp: so sánh có kiểm soát

Mỗi bản ghi được so với **chính nó lúc trời khô ráo**:

1. **Baseline** = tốc độ trung bình của *cùng đường, cùng giờ, cùng loại ngày* trong các giờ **khô** (không mưa, không tuyết). Ô nào có dưới 10 giờ khô thì bỏ.
2. **Chỉ số tương đối** `speed_idx = avg_speed / baseline`. Ví dụ `0,95` nghĩa là chậm hơn bình thường 5%.
3. Nhóm `speed_idx` theo điều kiện thời tiết, lượng mưa, lượng tuyết, nhiệt độ. **% thay đổi = (TB speed_idx − 1) × 100.**

Có hai mức kiểm soát:

| Cột trong báo cáo | Baseline theo | Loại bỏ ảnh hưởng của |
|---|---|---|
| `thay_doi_tho_pct` | (không) | Không loại bỏ gì. Đây là cách so sánh của bước 15 |
| `thay_doi_kiem_soat_pct` | đường × giờ × loại ngày | Giờ cao điểm, cuối tuần, loại đường |
| `kiem_soat_them_thang_pct` | đường × giờ × loại ngày × **tháng** | Như trên, **thêm mùa** (ngưỡng ≥ 5 giờ khô mỗi ô) |

**Các xử lý bổ sung:**

- **Ngày lễ** (14 ngày lễ liên bang và ngày nghỉ phổ biến của năm 2024) được xếp vào loại "cuối tuần", vì giao thông ngày lễ giống cuối tuần. Lần chạy đầu chưa làm việc này, và ngày 27/5 (Memorial Day, có mưa 30 mm) cho tốc độ **+23%**: đó là hiệu ứng ngày lễ, không phải hiệu ứng của mưa.
- **14 ngày mất dữ liệu** (bước 07) bị loại.

### 2.2. Vì sao chọn cách này thay vì hồi quy?

Plan không yêu cầu Machine Learning. So sánh có kiểm soát (còn gọi là *stratification*: so trong từng tầng) dễ giải thích, dễ kiểm tra, và mỗi con số đều có ý nghĩa trực tiếp: "chậm hơn X% so với chính đường đó, giờ đó, lúc khô ráo".

## 3. Thực hiện

```bash
python -m spark_jobs.s16_weather_impact
```

Thời gian chạy khoảng 40 giây. Phân tích dùng 785.767 bản ghi tốc độ.

## 4. Kết quả

### 4.1. Theo điều kiện thời tiết: nhiễu đã bị loại bỏ thế nào

| Thời tiết | n | Số ngày | Thô | Kiểm soát | **Kiểm soát + mùa** |
|---|---|---|---|---|---|
| Clear | 353.216 | 303 | 0 | −0,4% | −0,5% |
| Cloudy | 315.209 | 327 | −0,6% | +0,5% | +0,5% |
| Drizzle | 83.330 | 193 | −5,4% | −2,7% | **−2,4%** |
| Rain | 23.421 | 96 | −6,6% | −4,8% | **−4,6%** |
| Snow | 10.591 | 27 | +0,6% | +5,8% | **−0,1%** |

**Nhận xét:**

1. **Mưa làm giảm tốc độ, nhưng ít hơn so sánh thô cho thấy:** −4,6% chứ không phải −6,6%. Khoảng 1/3 mức giảm trong so sánh thô là do mưa hay rơi vào các giờ vốn chậm. Mưa phùn (Drizzle) −2,4%, mưa (Rain) −4,6%: **mưa càng nặng hạt thì càng chậm**.
2. **Tuyết là ví dụ rõ nhất về confounding:**
   - So sánh thô: +0,6%.
   - Kiểm soát giờ và đường: **+5,8%**, còn lạ hơn.
   - Kiểm soát thêm **mùa**: **−0,1%**, tức hầu như không có ảnh hưởng.

   Toàn bộ "hiệu ứng tuyết làm xe nhanh hơn" thực chất là **hiệu ứng mùa đông**: đường vắng hơn trong tháng 1–2 (sau kỳ nghỉ lễ, ít du lịch). Chỉ khi so tuyết với *các giờ khô của cùng tháng* thì nhiễu mới bị loại bỏ.
3. Kiểm soát mùa gần như **không làm thay đổi kết quả của mưa** (−4,8% so với −4,6%), vì mưa có quanh năm. Đây là dấu hiệu kết quả của mưa vững chắc.

### 4.2. Liều – đáp ứng: lượng mưa

| Lượng mưa | n | Số ngày | Kiểm soát + mùa |
|---|---|---|---|
| Không mưa | 668.425 | 344 | 0 |
| 0–0,5 mm/h (rất nhẹ) | 65.466 | 192 | −1,6% |
| 0,5–2 mm/h (nhẹ) | 26.249 | 124 | **−5,1%** |
| 2–5 mm/h (vừa) | 11.082 | 77 | −4,7% |
| > 5 mm/h (to) | 3.954 | 41 | −3,2% |

- Từ không mưa đến mưa nhẹ, tốc độ giảm rõ rệt (−1,6% rồi −5,1%). Trên 2 mm/h thì **không giảm thêm**, thậm chí mưa to chỉ −3,2%.
- **Giả thuyết (chưa kiểm chứng):** mưa to thường ngắn (giông mùa hè) và có thể làm người dân hoãn chuyến đi, đường vắng hơn bù lại cho việc xe chạy chậm vì tầm nhìn kém. Nhóm "> 5 mm/h" chỉ có 41 ngày, nên kết quả kém chắc chắn nhất.

### 4.3. Mưa trong giờ cao điểm

| Thời điểm | Mưa > 0,5 mm/h (kiểm soát + mùa) |
|---|---|
| **Cao điểm ngày thường** (7–9h, 16–18h) | **−8,4%** |
| Ngoài cao điểm | −4,1% |

**Mưa giờ cao điểm gây chậm gấp đôi.** Lúc đường đã gần hết năng lực, chỉ cần mỗi xe giữ khoảng cách xa hơn một chút là năng lực đường giảm và tắc nghẽn tăng mạnh. Đây là hiện tượng phi tuyến: tốc độ giảm nhanh khi lưu lượng tiến gần năng lực, giống mô hình BPR dùng ở bước 04. Đây cũng là phát hiện có ích nhất cho người điều hành giao thông: **cảnh báo mưa cần ưu tiên khung giờ cao điểm**.

### 4.4. Tuyết: chỉ có một trận tuyết lớn

| Ngày | Tuyết | Loại ngày | Kiểm soát + mùa |
|---|---|---|---|
| **13/02/2024** | **16 cm** | ngày thường | **+25%** |
| 06/01 | 3,9 cm | cuối tuần | +0,5% |
| 17/02 | 3,9 cm | cuối tuần | +4,1% |
| 16/01 | 3,5 cm | ngày thường | −2,3% |
| 21/12 | 2,3 cm | cuối tuần | −8,1% |

- Năm 2024 New York chỉ có **một trận tuyết đáng kể**: ngày 13/02, khoảng 16 cm. Ngày đó tốc độ **cao hơn bình thường 25%**, dù có tuyết. Hôm đó trường công lập New York chuyển sang học trực tuyến và nhiều người làm việc tại nhà, nên lượng xe giảm mạnh. Tác động "người dân ở nhà" lớn hơn tác động "đường trơn". *Nhóm nên kiểm tra lại sự kiện này qua tin tức của ngày 13/02/2024 trước khi trình bày.*
- Nhóm "> 1 cm/h" (+15,1%) gần như **chỉ gồm ngày 13/02**, vì chỉ có 3 ngày. **Không thể kết luận chung về tuyết từ 1 trận**, đó là giới hạn của dữ liệu một năm.

### 4.5. Nhiệt độ

| Nhiệt độ | Thô | Kiểm soát | Kiểm soát + mùa |
|---|---|---|---|
| < 0 °C | +6,8% | +3,6% | −0,7% |
| 0–10 °C | +0,5% | +1,5% | −1,2% |
| 10–20 °C | 0 | −1,6% | −0,2% |
| 20–30 °C | −6,7% | −2,0% | +0,3% |
| ≥ 30 °C | **−17,7%** | −1,8% | −0,2% |

So sánh thô cho thấy trời nóng ≥ 30 °C làm xe chậm 17,7%. Thực tế, **trời nóng xảy ra vào chiều mùa hè, đúng giờ cao điểm chiều**. Kiểm soát giờ và mùa thì ảnh hưởng còn dưới ±1,2%: **nhiệt độ hầu như không tác động trực tiếp lên tốc độ**. Đây là ví dụ thứ hai về một "tương quan" hoàn toàn do nhiễu.

### 4.6. Lưu lượng xe theo lượng mưa

5.844 giờ đếm có baseline (ngưỡng ≥ 5 giờ khô mỗi ô, vì mỗi đợt đếm chỉ kéo dài 1–2 tuần).

| Lượng mưa | n | Số ngày | Thô | Kiểm soát | Kiểm soát + mùa | KTC 95% |
|---|---|---|---|---|---|---|
| Không mưa | 5.327 | 149 | 0 | 0 | 0 | ±0,5% |
| 0–0,5 mm/h | 263 | 45 | **−31,8%** | −0,2% | +1,0% | ±2,0% |
| 0,5–2 mm/h | 161 | 27 | −20,2% | −1,9% | −1,3% | ±2,6% |
| 2–5 mm/h | 61 | 17 | −20,9% | −3,8% | −1,2% | ±4,0% |
| > 5 mm/h | 4 | 4 | −30,0% | −18,0% | +5,6% | ±24,6% |

- **So sánh thô cho thấy mưa làm giảm lưu lượng 20–32%. Đây hoàn toàn là nhiễu:** những điểm đếm tình cờ gặp mưa là các điểm vắng xe hơn. Khi so mỗi điểm với chính nó lúc khô ráo, mức thay đổi chỉ còn từ −3,8% đến +1,0%, đều nằm trong khoảng sai số.
- **Kết luận: không phát hiện được tác động của mưa lên lưu lượng xe.** Lưu ý "không phát hiện được" khác với "không có": dữ liệu đếm quá thưa (17 ngày mưa vừa, 4 giờ mưa to) để thấy một tác động nhỏ.
- Kết quả này **khớp với lý thuyết**: phần lớn chuyến đi (đi làm, đi học) không hủy vì mưa. Mưa làm xe *chạy chậm hơn* (mục 4.1) chứ không làm *ít xe hơn* đáng kể. Trận tuyết 13/02 là ngoại lệ, vì có quyết định học/làm tại nhà.

### 4.7. Tương quan Pearson

| Cặp biến | r |
|---|---|
| rainfall – avg_speed (từng bản ghi) | −0,02 |
| rainfall – speed_idx (TB thành phố mỗi giờ) | −0,07 |
| temperature – speed_idx (TB thành phố mỗi giờ) | −0,19 |

**Hệ số tương quan gần 0 không có nghĩa mưa không ảnh hưởng.** Vì:

- Khoảng 86% bản ghi không có mưa (rainfall = 0). Pearson đo quan hệ **tuyến tính** trên toàn bộ dữ liệu, nên bị khối giá trị 0 này lấn át.
- Quan hệ **không tuyến tính**: giảm mạnh từ 0 đến 2 mm/h rồi đi ngang (mục 4.2).
- Tốc độ dao động theo giờ và đường (std 26 km/h) lớn hơn nhiều so với tác động của mưa (khoảng 3 km/h).

Vì vậy, với dữ liệu kiểu này, **so sánh theo nhóm có kiểm soát cho thông tin tốt hơn hệ số tương quan**. Plan cũng ghi "correlation đơn giản *nếu phù hợp*", và ở đây nó không phù hợp. Riêng tương quan với nhiệt độ (−0,19) lại cao hơn mưa, nhưng mục 4.5 đã cho thấy đó là nhiễu do mùa.

### 4.8. Những ngày mưa lớn nhất

| Ngày | Mưa | Loại ngày | Kiểm soát + mùa |
|---|---|---|---|
| 21/11 | 47,5 mm | ngày thường | **−12,1%** |
| 06/03 | 34,9 mm | ngày thường | −6,5% |
| 09/01 | 36,1 mm | ngày thường | −6,2% |
| 11/12 | 39,2 mm | ngày thường | −3,3% |
| 23/03 | **64,0 mm** | **cuối tuần** | **+1,1%** |

Ngày mưa nhiều nhất năm (23/03, 64 mm) lại **không chậm**, vì rơi vào **thứ Bảy**. Mưa lớn vào ngày làm việc thì gây chậm 3–12%. Điều này khớp với mục 4.3: mưa gây hại nhất khi đường đã đông.

## 5. Kết luận cho phần giải trình

| Câu hỏi | Trả lời |
|---|---|
| Mưa có làm chậm giao thông? | **Có**: −4,6% (Rain), −2,4% (Drizzle), so với chính đường đó lúc khô ráo |
| Khi nào ảnh hưởng nặng nhất? | **Mưa vào giờ cao điểm ngày thường: −8,4%**, gấp đôi ngoài cao điểm |
| Tuyết? | Năm 2024 chỉ có 1 trận lớn (13/02), hôm đó đường **vắng và nhanh hơn** (+25%) vì người dân ở nhà. Không đủ dữ liệu để kết luận chung |
| Nhiệt độ? | Không ảnh hưởng trực tiếp (dưới ±1,2% sau kiểm soát). "Nóng thì chậm" là nhiễu do mùa và giờ |
| Lưu lượng xe theo mưa? | Thô: −20 đến −32%, nhưng sau kiểm soát còn −4% đến +1%, trong sai số. **Không phát hiện tác động**: mưa làm xe chậm hơn chứ không làm ít xe hơn |
| Bài học phương pháp | **So sánh thô có thể sai cả về chiều** (tuyết, nhiệt độ). Phải so trong cùng giờ, cùng đường, cùng mùa. Pearson gần 0 không có nghĩa là không có quan hệ |

**Kết quả bước 04 được dùng như thế nào?** Mock dataset được cài sẵn tác động "mưa −12%, tuyết −25%". Dữ liệu thật cho mức tác động **nhỏ hơn nhiều** (mưa khoảng −5%). Đó là lý do mock **chỉ dùng để test code**, không dùng để rút ra kết luận.

## 6. Kiểm tra

- [x] Nhóm "Không mưa" có `thay_doi_kiem_soat_pct = 0,00`, đúng theo định nghĩa (baseline tính từ chính các giờ khô).
- [x] Tổng `n` các mức mưa (775.176) = số bản ghi không có tuyết ở mục D. Khớp.
- [x] Xếp ngày lễ vào "cuối tuần" làm ngày 27/5 giảm từ +23% xuống +9% (kiểm soát theo năm), trong khi kết quả tổng của mưa gần như không đổi (Rain −4,30% → −4,79%, kiểm soát theo năm). Kết luận không phụ thuộc vào chi tiết xử lý này.

## 7. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| So sánh thô cho thấy tuyết làm xe nhanh hơn | Thêm so sánh có kiểm soát theo đường × giờ × loại ngày. Vẫn còn +5,8%, nên kiểm soát thêm theo tháng. Kết quả về khoảng 0 |
| Ngày 27/5 (Memorial Day, mưa 30 mm) tốc độ +23% | Ngày lễ giống cuối tuần. Thêm danh sách ngày lễ 2024 và xếp vào "weekend" |
| Phân tích lưu lượng: sau khi thêm ngày lễ, số giờ dùng được giảm từ 925 xuống 285 | Mỗi đợt đếm chỉ 1–2 tuần, nên ô (điểm đếm × giờ × ngày thường) chỉ có khoảng 5–10 giờ. Thêm một ngày lễ là ô tụt dưới ngưỡng 10 và bị bỏ cả ô. Hạ ngưỡng của lưu lượng xuống 5 giờ khô, số giờ dùng được tăng lên 5.844 |
| `AnalysisException: baseline cannot be resolved` | Cột `baseline` chỉ có sau khi join. Tính bảng "giờ có tuyết rơi vào lúc nào" trên DataFrame đã join |
| Khoảng tin cậy 95% trong báo cáo rất hẹp (±0,1–0,8%) | Các giờ trong cùng một trận mưa **không độc lập**, nên khoảng tin cậy thật rộng hơn. Báo cáo kèm cột `so_ngay` (số ngày độc lập) để người đọc đánh giá: kết luận về tuyết chỉ dựa trên 3 ngày |
