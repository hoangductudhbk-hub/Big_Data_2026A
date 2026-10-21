# Project Development Plan

## 1. Project Overview

**Project:** Big Data Integration and Statistical Analysis System for Urban Traffic Data

### Main Goal

Xây dựng hệ thống tích hợp và phân tích dữ liệu giao thông đô thị từ nhiều nguồn dữ liệu khác nhau.

Project tập trung vào:

- Data Integration
- Data Cleaning
- Schema Alignment
- Record Linkage
- Big Data Processing với PySpark
- Query Processing
- Approximate / Scalable Processing
- Statistical Analysis
- Simple Anomaly Detection
- Data Storage và API

Không triển khai AI/ML, Kafka, Kubernetes hoặc hệ thống phân tán phức tạp.

---

# 2. Overall Architecture

```text
Traffic Data ──────┐
Weather Data ──────┼──→ Data Profiling
Road Data ─────────┘          ↓
                         Data Cleaning
                              ↓
                       Schema Alignment
                              ↓
                    Record Linkage + Blocking
                              ↓
                     Unified Dataset
                              ↓
                    integrated_traffic
                              ↓
                         PySpark
                              ↓
                ┌─────────────┼─────────────┐
                ↓             ↓             ↓
         Query Processing  Approximate   Statistical
                           Processing     Analysis
                │             │             │
                └─────────────┼─────────────┘
                              ↓
                     Anomaly Detection
                              ↓
                       Processed Data
                              ↓
                         PostgreSQL
                              ↓
                           FastAPI
                              ↓
                         Dashboard
```

---

# 3. Phase Structure

Project được chia thành 3 phase chính:

```text
Phase 0
Project Setup
     ↓
Phase 1
Data Integration
     ↓
Phase 2
Big Data Processing & Analysis
     ↓
Phase 3
Backend Integration & Visualization
```

Trong đó:

- **Phase 1:** Người 2 phụ trách chính.
- **Phase 2:** Người 3 phụ trách chính.
- **Phase 3:** Người 1 phụ trách chính, phối hợp với Người 2 và Người 3.

Người 3 **không cần chờ Phase 1 hoàn thành hoàn toàn** mới bắt đầu. Người 3 có thể dùng mock dataset theo schema chuẩn để phát triển PySpark.

---

# 4. Phase 0 — Project Setup

## Mục tiêu

Chuẩn bị môi trường và thống nhất data contract trước khi chia việc.

## Công việc

### Project

- Tạo Git repository.
- Thống nhất cấu trúc project.
- Thống nhất Python version.
- Tạo `.env.example`.
- Tạo README cơ bản.

### Data Contract

Xác định schema chuẩn mà Phase 1 phải cung cấp cho Phase 2.

Ví dụ:

```text
road_id
timestamp
vehicle_count
avg_speed
temperature
rainfall
weather_condition
district
```

Đây là **interface giữa Phase 1 và Phase 2**.

Người 3 có thể tạo mock dataset theo schema này để bắt đầu phát triển PySpark.

## Output

```text
Git repository
Data contract
Project structure
Mock integrated dataset
```

---

# 5. Phase 1 — Data Integration

## Người phụ trách chính

**Người 2**

## Mục tiêu

Biến dữ liệu từ nhiều nguồn khác nhau thành một dataset có schema thống nhất để Phase 2 xử lý.

```text
Raw Data
   ↓
Profiling
   ↓
Cleaning
   ↓
Schema Alignment
   ↓
Record Linkage
   ↓
Unified Dataset
```

---

## Phase 1A — Data Acquisition & Data Quality

### 1. Data Collection

Thu thập các nguồn dữ liệu:

- Traffic
- Weather
- Road

Nguồn dữ liệu có thể:

- Dataset có sẵn trên Internet
- CSV
- JSON
- API nếu phù hợp

Không yêu cầu tự xây dựng hệ thống crawling phức tạp.

### 2. Data Profiling

Phân tích:

- Schema
- Data types
- Missing values
- Duplicate records
- Invalid values
- Record count
- Basic statistics

Ví dụ:

```text
Dataset A
- Records: 100,000
- Missing: 2.3%
- Duplicate: 150
- Timestamp format: ...
```

### 3. Data Cleaning

Xử lý:

- Missing values
- Duplicate
- Invalid records
- Timestamp
- Units
- Text normalization

Ví dụ:

```text
"2026/10/01 08:00"
"01-10-2026 08:00"
        ↓
2026-10-01 08:00:00
```

## Output Phase 1A

```text
Cleaned Traffic Data
Cleaned Weather Data
Cleaned Road Data
Data Profiling Report
Cleaning Report
```

---

# 6. Phase 1B — Schema Alignment & Record Linkage

## 6.1 Schema Alignment

Xác định correspondence giữa các schema khác nhau.

Ví dụ:

### Source A

```text
sensor_id
recorded_at
vehicle_count
speed
```

### Source B

```text
sensor
timestamp
vehicles
avg_velocity
```

### Unified Schema

```text
road_id
timestamp
vehicle_count
avg_speed
```

Mapping:

```python
SCHEMA_MAPPING = {
    "sensor_id": "road_id",
    "recorded_at": "timestamp",
    "vehicle_count": "vehicle_count",
    "speed": "avg_speed"
}
```

---

## 6.2 Record Linkage

Mục tiêu:

Xác định các record từ những nguồn khác nhau có đại diện cho cùng một road/entity hay không.

Ví dụ:

```text
"Nguyen Trai"
"Nguyen Trai Street"
"Duong Nguyen Trai"
```

có thể cùng đại diện cho một road.

### Blocking

Không so sánh toàn bộ record với nhau.

Có thể blocking theo:

- District
- Prefix
- Một số thuộc tính đơn giản khác

### Similarity

Sử dụng phương pháp đơn giản:

- Levenshtein similarity

Ví dụ:

```text
similarity >= 0.8
        ↓
      Match
```

Không triển khai LSH, TF-IDF hoặc các phương pháp record linkage phức tạp.

---

# 7. Phase 1C — Create Unified Dataset

Sau khi:

```text
Cleaning
   +
Schema Alignment
   +
Record Linkage
```

tạo ra:

```text
Unified Dataset
```

Ví dụ:

| road_id | timestamp | vehicle_count | avg_speed | temperature | rainfall | weather_condition | district |
|---|---|---:|---:|---:|---:|---|---|
| R001 | 2026-10-01 08:00 | 1250 | 32.5 | 28 | 0 | Clear | Cau Giay |
| R002 | 2026-10-01 08:00 | 980 | 25.2 | 27 | 2.5 | Rain | Thanh Xuan |

Dataset này được lưu dưới dạng:

```text
integrated_traffic
```

Có thể:

- lưu thành bảng PostgreSQL;
- hoặc export thành Parquet để PySpark xử lý.

Khuyến nghị sử dụng **Parquet cho PySpark** và PostgreSQL cho phần application/backend.

## Output chính của Phase 1

```text
integrated_traffic
```

Đây là dataset đầu vào chính của Phase 2.

---

# 8. Phase 2 — Big Data Processing & Analysis

## Người phụ trách chính

**Người 3**

## Mục tiêu

Sử dụng `integrated_traffic` để thực hiện Big Data Processing và phân tích dữ liệu.

```text
integrated_traffic
        ↓
      PySpark
        ↓
Query Processing
        ↓
Approximate / Scalable Processing
        ↓
Statistical Analysis
        ↓
Anomaly Detection
```

---

# 9. Phase 2A — PySpark & Query Processing

## 9.1 PySpark Setup

Thiết lập:

- PySpark
- SparkSession
- DataFrame
- Parquet input

Ví dụ:

```python
df = spark.read.parquet("integrated_traffic.parquet")
```

---

## 9.2 Basic Data Processing

Thực hiện:

- Filter
- Select
- Join
- GroupBy
- Aggregation
- Sort

Ví dụ:

```python
df.filter(df.vehicle_count > 1000)
```

---

## 9.3 Query Processing

Thực hiện một benchmark đơn giản để minh họa query processing.

### Query 1

```text
Join
  ↓
Filter
```

### Query 2

```text
Filter
  ↓
Join
```

So sánh:

- Execution time
- Number of records processed
- Final result

Mục tiêu là minh họa ý tưởng **predicate pushdown / giảm dữ liệu trước khi join**.

Không xây dựng query optimizer riêng.

---

# 10. Phase 2B — Approximate / Scalable Processing

## 10.1 Exact Processing

Xử lý toàn bộ dataset:

```text
Full Dataset
     ↓
Exact Aggregation
     ↓
Exact Result
```

## 10.2 Approximate Processing

Lấy sample:

```text
Full Dataset
     ↓
Sampling
     ↓
Approximate Aggregation
     ↓
Approximate Result
```

Sau đó so sánh:

```text
Exact Result
vs
Approximate Result
```

Đánh giá:

- Execution time
- Exact value
- Approximate value
- Relative error

---

## 10.3 Scalability Benchmark

Chạy cùng một processing job trên dataset có kích thước khác nhau.

Ví dụ:

```text
100 MB
500 MB
1 GB
5 GB
```

Tùy khả năng máy có thể điều chỉnh kích thước.

Đo:

- Dataset size
- Number of records
- Execution time
- Memory nếu có thể đo

Mục tiêu:

```text
Dataset Size
     ↓
Processing Time
```

để thể hiện khả năng scalable processing.

---

# 11. Phase 2C — Statistical Analysis

Thực hiện các thống kê cơ bản:

```text
Count
Mean
Min
Max
Standard Deviation
Median (nếu phù hợp)
```

## Grouped Analysis

Phân tích theo:

- Hour
- Day
- Road
- District
- Weather condition

Ví dụ:

```text
Average vehicle count by hour
Average speed by district
Traffic volume by weather condition
```

---

# 12. Phase 2D — Weather vs Traffic Analysis

Phân tích mối quan hệ giữa thời tiết và giao thông.

Ví dụ:

```text
Rainfall
   ↓
Vehicle Count
```

hoặc:

```text
Weather Condition
   ↓
Average Speed
```

Kết quả có thể sử dụng:

- Grouped statistics
- Correlation đơn giản nếu phù hợp

Không yêu cầu Machine Learning.

---

# 13. Phase 2E — Simple Anomaly Detection

Sử dụng Z-score:

```text
z = (x - mean) / std
```

Có thể đánh dấu:

```text
abs(z) > 3
```

là anomaly.

Ví dụ:

```text
Average traffic = 1000
Normal range ≈ ...
Record = 5000
        ↓
     Anomaly
```

Output:

```text
road_id
timestamp
vehicle_count
z_score
is_anomaly
```

---

# 14. Phase 3 — Backend Integration & Visualization

## Người phụ trách chính

**Người 1**

Người 1 xây dựng application/backend và kết nối output của Phase 2.

## Backend Stack

```text
Python
FastAPI
PostgreSQL
SQLAlchemy
Alembic
Docker
```

---

## 14.1 Database

Các bảng chính:

```text
roads
traffic_records
weather_records
integrated_traffic
processed_traffic_records
statistics
anomalies
```

Không bắt buộc tất cả phải là bảng riêng nếu thiết kế cuối cùng có lý do phù hợp.

---

## 14.2 FastAPI

API cơ bản:

```text
GET  /health

GET  /traffic
GET  /traffic/{id}

GET  /weather
GET  /roads

GET  /statistics
GET  /anomalies

POST /import/traffic
POST /import/weather
```

---

## 14.3 Integration

Kết nối:

```text
Phase 1
   ↓
integrated_traffic
   ↓
Phase 2
   ↓
Processed Results
   ↓
PostgreSQL
   ↓
FastAPI
```

---

# 15. Dependency Between Members

Dependency được thiết kế theo hướng **không để Người 3 phải chờ Người 2**.

```text
                Phase 1
              Người 2
                 │
                 │
        integrated_traffic
                 │
                 ↓
              Phase 2
              Người 3
```

Tuy nhiên trong quá trình development:

```text
Phase 1:
Person 2 ────────────────→ Real Dataset
                              │
                              ↓
Phase 2:
Person 3 ──→ Mock Dataset ──→ Real Dataset
```

Người 3 bắt đầu bằng mock dataset có **đúng schema của `integrated_traffic`**.

Khi Người 2 hoàn thành Phase 1:

```text
Mock Dataset
     ↓
Replace
     ↓
Real integrated_traffic
```

Không cần viết lại logic PySpark.

---

# 16. Responsibility Summary

## Người 1 — Backend / System Integration

```text
FastAPI
PostgreSQL
SQLAlchemy
Alembic
Docker
API
Backend Integration
Final System Integration
```

## Người 2 — Data Integration

```text
Data Collection
Data Profiling
Data Cleaning
Schema Alignment
Record Linkage
Blocking
Unified Dataset
Data Documentation
```

## Người 3 — Big Data Processing

```text
PySpark
DataFrame Processing
Query Processing
Predicate Pushdown Experiment
Approximate Processing
Scalability Benchmark
Statistical Analysis
Weather-Traffic Analysis
Anomaly Detection
```

---

# 17. Final Data Flow

```text
                  RAW DATA
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
    Traffic       Weather        Road
       │             │             │
       └─────────────┼─────────────┘
                     ↓
              Data Profiling
                     ↓
               Data Cleaning
                     ↓
              Schema Alignment
                     ↓
           Record Linkage + Blocking
                     ↓
              Unified Dataset
                     ↓
            integrated_traffic
                     │
                     ↓
                  PySpark
                     │
       ┌─────────────┼──────────────┐
       ↓             ↓              ↓
 Query Processing  Approximate   Statistical
                   Processing     Analysis
       │             │              │
       └─────────────┼──────────────┘
                     ↓
             Anomaly Detection
                     ↓
              Processed Results
                     ↓
                PostgreSQL
                     ↓
                  FastAPI
                     ↓
                Dashboard
```

---

# 18. Expected Final Results

Project cần thể hiện được:

### Data Integration

- Nhiều nguồn dữ liệu.
- Heterogeneous schemas.
- Schema Alignment.
- Record Linkage.
- Unified Dataset.

### Big Data Processing

- PySpark.
- DataFrame processing.
- Join / Filter / Aggregation.
- Query Processing.
- Predicate Pushdown experiment.

### Approximate / Scalable Processing

- Exact vs Approximate.
- Sampling.
- Relative error.
- Dataset scaling benchmark.

### Statistical Analysis

- Descriptive statistics.
- Grouped statistics.
- Weather vs Traffic analysis.
- Z-score anomaly detection.

### System

- PostgreSQL.
- FastAPI.
- API.
- Docker.
- Dashboard / visualization.

---

# 19. Scope Control

## Không làm

```text
AI / Machine Learning
Kafka
Kubernetes
Microservices
HDFS Cluster
Complex Streaming
Adaptive Query Processing
Eddy
RippleJoin
XJoin
LSH
TF-IDF Record Linkage
Custom Query Optimizer
Complex Data Warehouse
```

## Tập trung

```text
Data Integration
       +
PySpark
       +
Query Processing
       +
Approximate / Scalable Processing
       +
Statistical Analysis
```

---

# 20. Definition of Done

Project được xem là hoàn thành khi:

- [ ] Có ít nhất 2–3 nguồn dữ liệu khác nhau.
- [ ] Có Data Profiling.
- [ ] Có Data Cleaning.
- [ ] Có Schema Alignment.
- [ ] Có Record Linkage + Blocking.
- [ ] Tạo được `integrated_traffic`.
- [ ] PySpark đọc và xử lý được dataset.
- [ ] Có Query Processing experiment.
- [ ] Có Exact vs Approximate Processing.
- [ ] Có Scalability Benchmark.
- [ ] Có Statistical Analysis.
- [ ] Có Simple Anomaly Detection.
- [ ] Kết quả được lưu vào PostgreSQL.
- [ ] Có FastAPI.
- [ ] Có Docker.
- [ ] Có tài liệu mô tả pipeline.
- [ ] Có benchmark/result thực tế thay vì số liệu giả.
