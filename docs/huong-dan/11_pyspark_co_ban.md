# 11. PySpark: thiết lập và xử lý cơ bản

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026, chạy trên dữ liệu thật.
> Báo cáo: `docs/bao-cao/11_spark_basic.md` · Đầu ra: `data/processed/analytics/hourly_profile.parquet`

## 1. Mục tiêu

- Dựng môi trường PySpark chạy được và lặp lại được.
- Viết module dùng chung cho mọi job Spark của Phase 2.
- Minh họa và đo các phép xử lý cơ bản mà plan yêu cầu (mục 9.2): **filter, select, join, groupBy, aggregation, sort**, cùng hai khái niệm cốt lõi của Spark là **lazy evaluation** và **cache**.

## 2. Môi trường đã chạy thực tế

| Thành phần | Phiên bản |
|---|---|
| Hệ điều hành | Ubuntu 22.04 (máy ảo Linux trên laptop Dell của nhóm) |
| CPU / RAM cho Spark | 2 nhân · 3,9 GB (driver dùng 2 GB) |
| Java | OpenJDK 11 |
| Python | 3.10 |
| PySpark | **3.5.3** |

Code cũng đã chạy được với PySpark 4.0.1 + Java 21 (môi trường phát triển). Thực tế chỉ dùng các API có ở cả hai phiên bản.

**Vì sao không cài thẳng lên Windows?** Windows của nhóm đang dùng Python 3.14, mới hơn các phiên bản PySpark hỗ trợ chính thức, và Spark trên Windows còn cần thêm `winutils.exe`. Có 3 cách:

| Cách | Lệnh | Ghi chú |
|---|---|---|
| **WSL2 / Ubuntu** (khuyên dùng) | `bash scripts/setup_spark_linux.sh` rồi `python -m spark_jobs.s11_basic` | Giống môi trường đã chạy thực tế |
| **Docker** | `docker build -f Dockerfile.spark -t bigdata-spark .` rồi `docker run --rm -v "${PWD}":/app bigdata-spark python -m spark_jobs.s11_basic` | Không phải cài Java lên Windows. *Dockerfile chưa được chạy thử trong quá trình làm, nhóm cần chạy thử lần đầu* |
| Windows thuần | Cài Python 3.11/3.12 + Java 17 + winutils (hướng dẫn 01, mục 3.2) + `pip install -r requirements-spark.txt` | Nhiều bước, dễ lỗi |

**Lỗi gặp phải khi dựng môi trường:** Spark không khởi động, báo `UnknownHostException: <hostname>: Temporary failure in name resolution`. Nguyên nhân là máy ảo không phân giải được tên máy của chính nó. Cách xử lý: đặt `SPARK_LOCAL_HOSTNAME=localhost`. `get_spark()` trong `spark_jobs/common.py` đã tự đặt biến này nên nhóm không phải làm thủ công.

## 3. Module dùng chung `spark_jobs/common.py`

| Thành phần | Vai trò |
|---|---|
| `get_spark(app)` | Tạo SparkSession thống nhất: `local[*]`, driver 2 GB, **múi giờ America/New_York**, `spark.sql.shuffle.partitions = 8` |
| `PATHS` | Đường dẫn dữ liệu. Đổi sang mock bằng biến môi trường `INTEGRATED_PATH=data/mock/integrated_traffic` |
| `best_of(fn, n)` | Chạy n lần, lấy thời gian **nhỏ nhất**, để giảm nhiễu do khởi động JVM và cache hệ điều hành |
| `Report` | Ghi báo cáo `.md` và `.json` kèm thông tin môi trường (phiên bản Spark, số nhân) |
| `save_analytics(df, name)` | Ghi kết quả nhỏ ra `data/processed/analytics/` để Phase 3 nạp vào PostgreSQL |

**Vì sao `shuffle.partitions = 8`?** Mặc định là 200, phù hợp với cluster lớn. Với một máy 2 nhân, 200 partition nhỏ chỉ làm tốn thời gian lập lịch task.

## 4. Thực hiện

```bash
python -m spark_jobs.s11_basic
```

Toàn bộ job chạy khoảng **40 giây** (kể cả khởi động JVM và các lần đo lặp).

## 5. Kết quả và giải thích

### 5.1. Lazy evaluation

| Thao tác | Thời gian |
|---|---|
| Khai báo `filter → withColumn → groupBy` (transformation) | **136 ms** |
| Gọi `collect()` (action) | **2,63 s** |

Transformation chỉ dựng **kế hoạch thực thi**. Spark chỉ đọc dữ liệu khi gặp action. Nhờ vậy bộ tối ưu Catalyst nhìn thấy cả chuỗi phép tính và tối ưu tổng thể: đẩy filter xuống, chỉ đọc các cột cần dùng...

### 5.2. select + filter, và predicate pushdown xuống Parquet

Lọc BQE giờ cao điểm sáng ngày thường: còn **3.951 / 805.780** dòng, tốc độ trung bình **40,4 km/h** trên 7 tuyến.

Physical plan cho thấy điều kiện lọc được **đẩy xuống lớp đọc file** (`PushedFilters: [IsNotNull(road_name), StringStartsWith(road_name, BROOKLYN QUEENS EXPRESSWA...)]`), và `ReadSchema` chỉ gồm 5 cột cần dùng (**column pruning**). Parquet lưu thống kê min/max cho từng khối dữ liệu, nên những khối chắc chắn không thỏa điều kiện sẽ được bỏ qua mà không phải đọc. Bước 12 sẽ đo hiệu quả này.

### 5.3. join: 9.048.108 bản ghi tốc độ ⨝ 125 tuyến

| Quận | Số bản ghi | Tốc độ TB |
|---|---|---|
| Staten Island | 1.676.570 | **79,6 km/h** |
| Queens | 3.368.987 | 62,4 km/h |
| Bronx | 1.910.929 | 62,1 km/h |
| Brooklyn | 622.966 | 54,8 km/h |
| Manhattan | 1.468.656 | **40,8 km/h** |

| Chiến lược join | Plan | Lần đầu | Tốt nhất / 3 lần |
|---|---|---|---|
| Broadcast (mặc định, vì bảng tuyến < 10 MB) | `BroadcastHashJoin` | 1,68 s | **1,27 s** |
| Sort-merge (tắt broadcast) | `SortMergeJoin` | 5,63 s | **4,19 s** |

**Broadcast join nhanh hơn 3,3 lần.** Broadcast join gửi bảng nhỏ (125 tuyến) tới mọi executor, nên **không cần shuffle** 9 triệu dòng của bảng lớn. Sort-merge join phải shuffle rồi sắp xếp cả hai bảng theo `link_id`. Trên cluster nhiều máy, chi phí shuffle qua mạng còn lớn hơn, nên khoảng cách sẽ rộng hơn nữa.

### 5.4. groupBy: hồ sơ giao thông theo giờ

| Loại ngày | Giờ | Tốc độ TB | Lưu lượng TB |
|---|---|---|---|
| Ngày thường | 3h | 78,3 km/h | 111 xe/giờ |
| Ngày thường | 8h | 52,4 | 758 |
| Ngày thường | **17h** | **44,2** | **824** |
| Ngày thường | 20h | 62,5 | 620 |
| Cuối tuần | 8h | 72,2 | 393 |
| Cuối tuần | 17h | 50,8 | 653 |

Giờ cao điểm chiều ngày thường vừa **chậm nhất** vừa **đông xe nhất**. Cuối tuần thì 8h sáng đường vắng hẳn (393 so với 758 xe/giờ). Đúng như mẫu hình được giả định khi tạo mock dataset ở bước 04, nay đã được kiểm chứng trên dữ liệu thật. Kết quả đầy đủ 48 dòng được lưu ở `analytics/hourly_profile.parquet` cho dashboard.

### 5.5. sort: 10 tuyến chậm nhất giờ cao điểm chiều (16–19h ngày thường)

Đứng đầu là **11th Avenue và 12th Avenue** ở Manhattan (khoảng 5 km/h), tiếp theo là BQE đoạn qua Manhattan (6,8 km/h), Gowanus Expressway (8,8 km/h), Major Deegan, Belt Parkway, Cross Bronx Expressway (12–16 km/h). Đây là những trục nổi tiếng hay kẹt xe ở New York, cho thấy dữ liệu sau tích hợp phản ánh đúng thực tế.

### 5.6. Spark SQL

Cùng truy vấn ở mục 5.4 viết bằng SQL cho **kết quả trùng khớp 48/48 dòng**. DataFrame API và SQL chỉ là hai cách viết, cùng được Catalyst biên dịch ra một kế hoạch thực thi.

### 5.7. cache

| Truy vấn: đếm bản ghi < 30 km/h theo tuyến | Tốt nhất / 3 lần |
|---|---|
| Không cache (mỗi lần đọc lại Parquet và lọc) | 0,52 s |
| Phần đã lọc được `cache()` trong bộ nhớ | 0,18 s (nhanh hơn 2,9 lần) |

Nên cache khi một DataFrame được dùng lại nhiều lần, như trong bước 13 và 16. Không nên cache dữ liệu chỉ dùng một lần, vì tốn bộ nhớ.

## 6. Vấn đề gặp phải: một lỗi đo lường đáng nhớ

Lần chạy đầu cho kết quả **broadcast 0,05 s, sort-merge 0,10 s** trên 9 triệu dòng. Con số này nhanh đến mức vô lý. Khi làm bước 12 thì lỗi lộ rõ: một phép sort-merge join 9 triệu dòng chỉ mất 0,03 s.

**Nguyên nhân:** hàm đo gọi `collect()` lặp lại trên **cùng một đối tượng DataFrame**. Spark giữ lại kết quả shuffle của lần chạy đầu, nên ở các lần sau nó **bỏ qua các stage đã tính** (skipped stages). Thời gian đo được gần như chỉ còn là thời gian gom kết quả.

**Cách sửa:** hàm `measure(build)` trong `common.py` **dựng DataFrame mới mỗi lần đo**, và báo cáo cả thời gian lần đầu (lạnh) lẫn tốt nhất (ấm). Mọi số liệu thời gian trong các bước 11–17 đều được đo theo cách này.

> Bài học: **benchmark sai còn tệ hơn không benchmark.** Luôn kiểm tra xem con số có hợp lý với khối lượng dữ liệu không. Ở đây 9 triệu dòng mà chỉ mất vài chục mili giây là dấu hiệu bất thường.

| Vấn đề khác | Cách xử lý |
|---|---|
| `UnknownHostException` khi khởi động Spark | `SPARK_LOCAL_HOSTNAME=localhost` (đã đưa vào `get_spark`) |
| Spark 3.5 báo `Illegal Parquet type: INT64 (TIMESTAMP(NANOS,false))` khi đọc `weather_clean.parquet` | pandas mặc định ghi timestamp nano giây. Thêm `to_parquet_us()`, mọi file của Phase 1 ghi ở micro giây, rồi chạy lại bước 07–10 (kết quả không đổi: 805.780 dòng) |

## 7. Kiểm tra

- [x] `python -m spark_jobs.s11_basic` chạy hết, sinh `docs/bao-cao/11_spark_basic.md`
- [x] Tổng số bản ghi theo quận ở mục 5.3 = 9.048.108, đúng bằng số dòng sau làm sạch (bước 07)
- [x] Kết quả SQL trùng với DataFrame API
