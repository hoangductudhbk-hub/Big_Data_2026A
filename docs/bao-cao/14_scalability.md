# Báo cáo bước 14 — Scalability benchmark

Sinh tự động lúc 2026-10-13 16:23 · Spark 3.5.3 · local[*] (2 nhân) · dữ liệu `data/processed/integrated_traffic`.
Job chuẩn: thống kê count/mean/min/max tốc độ theo (tuyến × giờ × ngày thường/cuối tuần). Mỗi kích thước chạy nhiều lần, mỗi lần dựng DataFrame mới; `best_s` là lần nhanh nhất.

## A. CSV gốc: 1 → 12 tháng

| du_lieu | size_mb | rows | groups | first_s | best_s | input_mb | shuffle_mb | tasks | peak_mem_moi_task_mb | trieu_dong_moi_s |
|---|---|---|---|---|---|---|---|---|---|---|
| CSV 1 tháng | 98.80 | 817,609 | 5,115 | 4.85 | 1.29 | 99.00 | 0.09 | 2 | 33.80 | 0.63 |
| CSV 3 tháng | 263.70 | 2,153,618 | 5,230 | 3.79 | 3.59 | 263.70 | 0.14 | 1 | 33.80 | 0.60 |
| CSV 6 tháng | 579.20 | 4,664,643 | 5,233 | 6.55 | 6.55 | 579.20 | 0.28 | 6 | 33.80 | 0.71 |
| CSV 12 tháng | 1,185.20 | 9,555,071 | 5,280 | 13.22 | 13.22 | 1,185.20 | 0.57 | 12 | 33.80 | 0.72 |


## B. Parquet đã làm sạch, nhân bản

| du_lieu | size_mb | rows | groups | first_s | best_s | input_mb | shuffle_mb | tasks | peak_mem_moi_task_mb | trieu_dong_moi_s |
|---|---|---|---|---|---|---|---|---|---|---|
| Parquet ×1 | 22.90 | 9,048,108 | 5,248 | 4.46 | 1.43 | 13.80 | 0.06 | 1 | 33.80 | 6.33 |
| Parquet ×2 | 47.90 | 18,096,216 | 10,496 | 1.60 | 1.57 | 29.50 | 0.12 | 1 | 34.10 | 11.53 |
| Parquet ×4 | 97.50 | 36,192,432 | 20,992 | 2.58 | 2.58 | 60.80 | 0.25 | 1 | 34.60 | 14.03 |
| Parquet ×8 | 196.30 | 72,384,864 | 41,984 | 5.23 | 5.23 | 123.00 | 0.50 | 1 | 35.70 | 13.84 |
| Parquet ×16 | 393.20 | 144,769,728 | 83,968 | 10.90 | 10.90 | 246.90 | 0.99 | 1 | 37.70 | 13.28 |


## Hồi quy tuyến tính: thời gian = chi phí cố định + hệ số × số triệu dòng

| du_lieu | chi_phi_co_dinh_s | s_moi_trieu_dong | r2 |
|---|---|---|---|
| CSV gốc | 0.39 | 1.34 | 1.00 |
| Parquet | 0.32 | 0.07 | 0.99 |


## CSV so với Parquet trên dữ liệu cùng một năm

| dinh_dang | size_mb | rows | best_s |
|---|---|---|---|
| CSV 12 tháng (gốc) | 1,185.20 | 9,555,071 | 13.22 |
| Parquet ×1 (đã làm sạch) | 22.90 | 9,048,108 | 1.43 |


## C. Số nhân: local[1] so với local[2]

| du_lieu | rows | local_1_s | local_2_s | speed_up | hieu_suat_song_song_pct |
|---|---|---|---|---|---|
| CSV 12 tháng | 9,555,071 | 20.51 | 13.22 | 1.55 | 77.60 |
| Parquet ×8 | 72,384,864 | 9.35 | 5.23 | 1.79 | 89.40 |

`input_mb`: dữ liệu Spark thực sự đọc từ đĩa. `shuffle_mb`: dữ liệu trao đổi giữa các stage. `tasks`: số task của stage tốn bộ nhớ nhất. `peak_mem_moi_task_mb`: bộ nhớ thực thi đỉnh trung bình mỗi task của stage đó (chủ yếu là bảng băm của groupBy). Heap của driver được cấu hình 2 GB cho mọi kích thước dữ liệu.
