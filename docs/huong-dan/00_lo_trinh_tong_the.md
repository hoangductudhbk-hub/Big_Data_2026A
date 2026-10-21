# 00. Lộ trình tổng thể của project

**Đề tài:** Big Data Integration and Statistical Analysis System for Urban Traffic Data
**Tài liệu định hướng gốc:** `docs/ke_hoach_du_an.md`. Mọi bước dưới đây đều bám theo tài liệu này.
**Thư mục hướng dẫn:** `docs/huong-dan/`. Mỗi bước có một file riêng, được viết **sau khi bước đó đã làm xong và chạy thử thành công**. Bộ file này dùng làm phần giải trình khi bảo vệ project.

---

## 1. Bài toán

Hệ thống tích hợp dữ liệu giao thông đô thị từ **nhiều nguồn có schema khác nhau**, sau đó làm sạch và ghép thành một bộ dữ liệu thống nhất (`integrated_traffic`). Dữ liệu được xử lý quy mô lớn bằng **PySpark** để thống kê, phân tích **ảnh hưởng của thời tiết tới giao thông** và phát hiện bất thường. Kết quả được lưu vào **PostgreSQL**, cung cấp qua **FastAPI** và hiển thị trên **Dashboard**.

## 2. Nguồn dữ liệu đã chọn

Chi tiết và lý do chọn nằm ở bước 02.

| Nguồn | Nội dung | Vai trò |
|---|---|---|
| NYC DOT Traffic Speeds (`i4gi-tjb9`) | Tốc độ xe trên các tuyến đường, cập nhật vài phút/lần, khoảng 104 triệu dòng | Giao thông: tốc độ |
| NYC Automated Traffic Volume Counts (`7ym2-wayt`) | Số xe đếm theo từng 15 phút trên các đoạn phố, khoảng 1,9 triệu dòng | Giao thông: lưu lượng |
| Open-Meteo Historical Weather | Nhiệt độ, mưa, tuyết, mã thời tiết theo giờ | Thời tiết: yếu tố ảnh hưởng |

## 3. Kiến trúc tổng thể

```text
NYC Speeds ──────┐
NYC Volume ──────┼──→ Profiling → Cleaning → Schema Alignment → Record Linkage + Blocking
Open-Meteo ──────┘                                                      │
                                                                        ↓
                                                   integrated_traffic (Parquet)
                                                                        │
                                                                     PySpark
                                   ┌────────────────┬───────────────────┼──────────────────┐
                                   ↓                ↓                   ↓                  ↓
                           Query Processing   Exact vs Approx   Statistical Analysis   Weather vs Traffic
                                   └────────────────┴───────────────────┼──────────────────┘
                                                                        ↓
                                                              Anomaly Detection (Z-score)
                                                                        ↓
                                                         PostgreSQL → FastAPI → Dashboard
```

## 4. Danh sách các bước

Ký hiệu trạng thái: ✅ đã xong và đã có file hướng dẫn · 🔄 đang làm · ⏳ chưa làm.

### Phase 0: Chuẩn bị

| Bước | Nội dung | Đầu ra | Trạng thái |
|---|---|---|---|
| 01 | Môi trường và cấu trúc project | Cấu trúc thư mục, `requirements-*.txt`, `.gitignore` | ✅ |
| 02 | Lựa chọn và giải trình nguồn dữ liệu | Bảng mô tả nguồn, đánh giá 3V | ✅ |
| 03 | Data contract `integrated_traffic` | `docs/data_contract.md`, `common/contract.py` | ✅ |
| 04 | Mock dataset | `scripts/generate_mock_integrated.py`, `data/mock/` | ✅ |

### Phase 1: Data Integration (Người 2 trong plan)

| Bước | Nội dung | Đầu ra | Trạng thái |
|---|---|---|---|
| 05 | Thu thập dữ liệu (speeds, volume, weather) | `data/raw/...` (12,1 triệu dòng, 1,2 GB) | ✅ |
| 06 | Data profiling | `docs/bao-cao/06_profiling.md` | ✅ |
| 07 | Data cleaning | `data/interim/*_clean.parquet`, `docs/bao-cao/07_cleaning.md` | ✅ |
| 08 | Schema alignment | `data/interim/aligned/`, `docs/bao-cao/08_alignment.md` | ✅ |
| 09 | Record linkage + blocking | `data/processed/roads.parquet`, `docs/bao-cao/09_linkage.md` | ✅ |
| 10 | Ghép thời tiết và tạo `integrated_traffic` | `data/processed/integrated_traffic/` (805.780 dòng) | ✅ |

### Phase 2: Big Data Processing & Analysis (Người 3 trong plan)

| Bước | Nội dung | Trạng thái |
|---|---|---|
| 11 | PySpark setup và xử lý cơ bản (filter, select, join, groupBy, sort) | ✅ |
| 12 | Query processing: so sánh Join→Filter và Filter→Join (predicate pushdown) | ✅ |
| 13 | So sánh kết quả chính xác (exact) và kết quả từ sampling (approximate), tính relative error | ✅ |
| 14 | Scalability benchmark trên nhiều kích thước dữ liệu | ✅ |
| 15 | Statistical analysis theo giờ, ngày, đường, quận, thời tiết | ✅ |
| 16 | Phân tích tác động của thời tiết lên giao thông | ✅ |
| 17 | Anomaly detection bằng Z-score | ✅ |

### Phase 3: Backend Integration & Visualization (Người 1 trong plan)

| Bước | Nội dung | Trạng thái |
|---|---|---|
| 18 | Chỉnh database backend theo data contract và nạp kết quả từ Spark | ✅ |
| 19 | Hoàn thiện API: import, statistics, anomalies, xử lý lỗi, test | ✅ |
| 20 | Dashboard | ✅ |
| 21 | Chạy toàn hệ thống end-to-end | ✅ |
| 22 | Tổng kết theo Definition of Done và chuẩn bị báo cáo | ✅ |

> Docker đã chạy thật trên Windows của nhóm ngày 14/10/2026, kiểm tra end-to-end 18/18 đạt. Việc còn lại trước khi bảo vệ: `23_viec_con_lai.md`.

## 5. Cấu trúc mỗi file hướng dẫn

Mỗi file `NN_ten_buoc.md` gồm các mục:

1. **Mục tiêu**: bước này giải quyết việc gì.
2. **Giải trình**: vì sao làm như vậy, liên hệ với lý thuyết môn học.
3. **Thực hiện**: các lệnh cụ thể, chạy lại được từ đầu.
4. **Kết quả**: file đầu ra và số liệu thực tế đo được.
5. **Kiểm tra**: cách tự xác nhận bước đã đúng.
6. **Vấn đề gặp phải**: lỗi đã gặp và cách xử lý.
