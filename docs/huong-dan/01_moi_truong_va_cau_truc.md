# 01. Môi trường và cấu trúc project

## 1. Mục tiêu

- Cài đặt các công cụ cần cho cả 3 phase: Python, Java (để chạy Spark), PySpark, Docker (để chạy PostgreSQL).
- Thống nhất cấu trúc thư mục để mỗi thành viên biết code và dữ liệu của mình nằm ở đâu.

## 2. Giải trình

- **Java:** Spark được viết bằng Scala và chạy trên JVM. PySpark chỉ là lớp Python điều khiển JVM qua thư viện Py4J, nên máy bắt buộc phải có Java.
- **PySpark 4.0.1:** bản ổn định mới, hỗ trợ Java 17/21 và Python 3.9–3.13. Cả nhóm dùng **chung một phiên bản** để tránh lỗi "máy em chạy được, máy anh không".
- **Parquet:** định dạng lưu trữ cột (columnar), có nén và lưu kèm schema. Spark đọc Parquet nhanh hơn CSV nhiều lần nhờ *column pruning* (chỉ đọc các cột cần dùng) và *predicate pushdown* (lọc ngay khi đọc file). Bước 12 sẽ đo hiệu quả này.
- **Tách dữ liệu theo tầng** (`raw → interim → processed`): dữ liệu gốc không bao giờ bị sửa. Nếu bước làm sạch sai, chỉ cần chạy lại từ `raw`. Đây là nguyên tắc cơ bản của data pipeline và giúp truy vết được nguồn gốc dữ liệu (data lineage).
- **Không đưa dữ liệu lên Git:** dữ liệu nặng hàng GB, nên Git chỉ lưu *script tải dữ liệu*. Ai cũng tải lại được đúng bộ dữ liệu đó.

## 3. Thực hiện

### 3.1. Cài phần mềm nền

| Phần mềm | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.12 (hoặc 3.11) | Backend yêu cầu 3.12+ |
| Java JDK | 17 (Eclipse Temurin) | Tải tại adoptium.net. Spark 4 cũng chạy được với Java 21 |
| Docker Desktop | bản mới | Để chạy PostgreSQL |
| Git | bản mới | |
| PyCharm | Community hoặc Professional | |

Kiểm tra sau khi cài:

```bash
python --version      # Python 3.12.x
java -version         # openjdk version "17..."
docker --version
```

**Thiết lập JAVA_HOME:**

- *Windows:* vào System Properties → Environment Variables, tạo biến `JAVA_HOME = C:\Program Files\Eclipse Adoptium\jdk-17...`, rồi thêm `%JAVA_HOME%\bin` vào `Path`.
- *macOS/Linux:* thêm `export JAVA_HOME=$(/usr/libexec/java_home -v 17)` (macOS) hoặc đường dẫn JDK tương ứng (Linux) vào file `~/.zshrc` hoặc `~/.bashrc`.

### 3.2. Lưu ý riêng cho Windows

Spark chạy trên Windows cần thêm `winutils.exe` thì mới ghi được file. Có 2 cách:

- **Cách 1 (khuyên dùng): WSL2 + Ubuntu.** Chạy lệnh `wsl --install`, rồi làm toàn bộ Phase 1–2 trong Ubuntu. Không cần winutils và tránh được hầu hết lỗi đường dẫn. PyCharm Professional kết nối được trực tiếp với interpreter trong WSL.
- **Cách 2: Windows thuần.**
  1. Tải `winutils.exe` và `hadoop.dll` bản Hadoop 3.3.x (repo GitHub `cdarlint/winutils`) vào thư mục `C:\hadoop\bin`.
  2. Đặt biến môi trường `HADOOP_HOME=C:\hadoop` và thêm `%HADOOP_HOME%\bin` vào `Path`.
  3. Khởi động lại PyCharm để nhận biến mới.

### 3.3. Tạo môi trường ảo và cài thư viện

Tại thư mục gốc project:

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
python -m pip install -U pip setuptools wheel
pip install -r requirements-data.txt          # Phase 1 + 2
pip install -r backend/requirements.txt       # Phase 3
```

> **Vì sao phải nâng cấp `setuptools` trước?** PySpark được phát hành dưới dạng mã nguồn (sdist), nên pip phải build trên máy. Khi chạy thử, lần cài đầu thất bại với lỗi `Building wheel for pyspark ... error` do `setuptools 68` quá cũ so với Python 3.13. Sau khi nâng cấp `setuptools`, việc cài đặt thành công.

### 3.4. Kiểm tra Spark chạy được

```bash
python -c "from pyspark.sql import SparkSession; s=SparkSession.builder.master('local[*]').getOrCreate(); print(s.version, s.range(5).count()); s.stop()"
```

Kết quả mong đợi là in ra `4.0.1 5`. Các dòng `WARN ... NativeCodeLoader` có thể bỏ qua.

## 4. Cấu trúc project

```text
Big_Data_2026A/
├── docs/
│   ├── huong-dan/              # File hướng dẫn từng bước (bộ tài liệu này)
│   ├── bao-cao/                # Báo cáo sinh ra từ pipeline (profiling, cleaning, benchmark...)
│   └── data_contract.md        # Schema chuẩn của integrated_traffic
├── common/                     # Code dùng chung giữa các phase (contract.py)
├── data/                       # KHÔNG đưa lên Git
│   ├── raw/                    # Dữ liệu gốc tải về, không sửa
│   │   ├── speeds/             #   NYC Traffic Speeds
│   │   ├── volume/             #   NYC Traffic Volume Counts
│   │   └── weather/            #   Open-Meteo
│   ├── interim/                # Dữ liệu đã làm sạch hoặc chuẩn hóa
│   ├── processed/              # integrated_traffic và kết quả phân tích
│   └── mock/                   # Mock dataset cho Phase 2 khi chưa có dữ liệu thật
├── data_integration/           # Phase 1
│   ├── collect/                #   05 Thu thập
│   ├── profiling/              #   06 Profiling
│   ├── cleaning/               #   07 Cleaning
│   ├── alignment/              #   08 Schema alignment
│   └── linkage/                #   09 Record linkage + blocking
├── spark_jobs/                 # Phase 2
├── backend/                    # Phase 3: FastAPI + PostgreSQL
├── dashboard/                  # Phase 3: Dashboard
├── scripts/                    # Script tiện ích (sinh mock data...)
├── requirements-data.txt
└── .gitignore
```

## 5. Kết quả

- Đã tạo cấu trúc thư mục như trên. Mỗi thư mục dữ liệu có file `.gitkeep` để Git vẫn giữ thư mục rỗng.
- File `.gitignore` loại trừ dữ liệu, `.env`, môi trường ảo và các file tạm của Spark.
- Đã kiểm tra trên môi trường thử nghiệm (Linux, Python 3.13, Java 21): PySpark 4.0.1 khởi động, ghi và đọc Parquet thành công.

## 6. Kiểm tra

- [ ] `java -version` chạy được.
- [ ] Lệnh ở mục 3.4 in ra `4.0.1 5`.
- [ ] `git status` không liệt kê file nào trong `data/` ngoài các file `.gitkeep`.

## 7. Vấn đề gặp phải

| Vấn đề | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Building wheel for pyspark ... error` | `setuptools` cũ không tương thích Python 3.13 | Tạo venv và chạy `pip install -U pip setuptools wheel` trước |
| `JAVA_HOME is not set` | Chưa khai báo biến môi trường | Xem mục 3.1 |
| Windows: `java.io.FileNotFoundException ... winutils.exe` | Thiếu Hadoop native trên Windows | Xem mục 3.2 |
