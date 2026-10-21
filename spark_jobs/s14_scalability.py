"""
Bước 14 — Scalability benchmark: cùng MỘT job, chạy trên dữ liệu có kích thước tăng dần.

    python -m spark_jobs.s14_scalability            # chạy đủ (khoảng 10–15 phút trên máy 2 nhân)
    python -m spark_jobs.s14_scalability --quick    # bản rút gọn để thử (1–3 tháng, ×1–×4)
    python -m spark_jobs.s14_scalability --part A   # chỉ chạy một phần: prepare | A | B | C | report

Job chuẩn (giống nhau ở mọi kích thước): tốc độ trung bình, nhỏ nhất, lớn nhất, số bản ghi
theo (tuyến × giờ trong ngày × ngày thường/cuối tuần) — đúng dạng thống kê mà bước 15 dùng.

  A. CSV gốc (dữ liệu thật tải về ở bước 05): 1 / 3 / 6 / 12 tháng  ≈ 100 MB → 1,2 GB
  B. Parquet đã làm sạch, nhân bản ×1 / ×2 / ×4 / ×8 / ×16          ≈ 9 triệu → 145 triệu bản ghi
     Mỗi bản sao đổi link_id (link_id × 100 + i) nên số nhóm cũng tăng theo, như thêm tuyến đường mới.
     Các bản sao được GHI RA ĐĨA thật (không union trong bộ nhớ) để Spark phải đọc đúng khối lượng đó.
  C. Số nhân: local[1] so với local[2] (speed-up, hiệu suất song song)
  D. Dữ liệu đọc vào, dữ liệu shuffle và bộ nhớ thực thi đỉnh mỗi task (REST API của Spark UI)

Đường dẫn có thể đổi bằng biến môi trường:
  RAW_SPEEDS_PATH  thư mục CSV gốc (mặc định data/raw/speeds)
  BENCH_DIR        nơi ghi dữ liệu nhân bản (mặc định data/bench, đã có trong .gitignore)
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql import types as T

from spark_jobs.common import PATHS, ROOT, Report, get_spark

RAW = Path(os.getenv("RAW_SPEEDS_PATH", PATHS["raw_speeds"]))
BENCH = Path(os.getenv("BENCH_DIR", ROOT / "data" / "bench"))
MONTHS = [f"2024-{m:02d}" for m in range(1, 13)]
MPH_TO_KMH = 1.609344

RAW_SCHEMA = T.StructType([
    T.StructField("id", T.LongType()), T.StructField("speed", T.DoubleType()),
    T.StructField("travel_time", T.DoubleType()), T.StructField("status", T.IntegerType()),
    T.StructField("data_as_of", T.StringType()), T.StructField("link_id", T.LongType()),
    T.StructField("borough", T.StringType()), T.StructField("link_name", T.StringType()),
])


# ---------------------------------------------------------------- job chuẩn
def standard_job(df):
    """df có cột link_id, timestamp, speed_kmh. Trả về bảng thống kê (tuyến × giờ × loại ngày)."""
    return (df.withColumn("hour", F.hour("timestamp"))
              .withColumn("weekend", F.dayofweek("timestamp").isin(1, 7))
              .groupBy("link_id", "hour", "weekend")
              .agg(F.count("*").alias("n"), F.avg("speed_kmh").alias("mean"),
                   F.min("speed_kmh").alias("min"), F.max("speed_kmh").alias("max")))


def read_raw_csv(spark, months):
    files = [str(RAW / f"speeds_{m}.csv") for m in months]
    df = spark.read.csv(files, header=True, schema=RAW_SCHEMA)
    return (df.filter(F.col("speed") > 0)   # cùng quy tắc cơ bản của bước 07: bỏ tốc độ 0/âm
              .select("link_id",
                      F.to_timestamp("data_as_of", "yyyy-MM-dd'T'HH:mm:ss.SSS").cast("timestamp_ntz").alias("timestamp"),
                      (F.col("speed") * MPH_TO_KMH).alias("speed_kmh")))


def read_bench(spark, k):
    return (spark.read.parquet(str(BENCH / "speeds_x16"))
                 .filter(F.col("rep") < k).select("link_id", "timestamp", "speed_kmh"))


# ---------------------------------------------------------------- đo đạc
def stage_metrics(spark, group: str) -> dict:
    """Đọc chỉ số của các stage thuộc job group từ REST API của Spark UI:
    dữ liệu đọc vào, dữ liệu shuffle, bộ nhớ thực thi lớn nhất (peak execution memory, tổng các task)."""
    import json
    import urllib.request
    sc = spark.sparkContext
    url = sc.uiWebUrl
    if not url:
        return {}
    base = f"{url}/api/v1/applications/{sc.applicationId}"
    try:
        jobs = json.load(urllib.request.urlopen(f"{base}/jobs", timeout=10))
        stage_ids = {sid for j in jobs if j.get("jobGroup") == group for sid in j["stageIds"]}
        inp = shuf = peak = tasks = 0
        for sid in stage_ids:
            for st in json.load(urllib.request.urlopen(f"{base}/stages/{sid}", timeout=10)):
                if st.get("status") != "COMPLETE":
                    continue
                inp += st.get("inputBytes", 0)
                shuf += st.get("shuffleWriteBytes", 0)
                # peakExecutionMemory của stage = TỔNG đỉnh bộ nhớ của các task → chia cho số task
                n = max(st.get("numCompleteTasks", 1), 1)
                if st.get("peakExecutionMemory", 0) / n > peak:
                    peak, tasks = st["peakExecutionMemory"] / n, n
        return {"input_mb": round(inp / 1e6, 1), "shuffle_mb": round(shuf / 1e6, 2), "tasks": tasks,
                "peak_mem_moi_task_mb": round(peak / 1e6, 1)}
    except Exception as e:  # noqa: BLE001 — không có UI/REST: vẫn trả thời gian
        print("  (không đọc được chỉ số stage:", e, ")")
        return {}


_run_id = 0


def run(spark, build, repeat):
    """Dựng DataFrame MỚI mỗi lần (tránh skipped stages, xem hướng dẫn 11 mục 6).
    Chỉ số stage (input/shuffle/bộ nhớ) lấy từ lần chạy cuối."""
    global _run_id
    sc = spark.sparkContext
    times = []
    for _ in range(repeat):
        _run_id += 1
        group = f"bench-{_run_id}"
        sc.setJobGroup(group, group)
        df = standard_job(build())
        t0 = time.perf_counter()
        res = df.agg(F.count("*").alias("groups"), F.sum("n").alias("rows")).collect()[0]
        times.append(time.perf_counter() - t0)
    time.sleep(1)  # chờ listener của UI cập nhật xong stage
    return {"rows": int(res["rows"]), "groups": int(res["groups"]), "first_s": round(times[0], 2),
            "best_s": round(min(times), 2), **stage_metrics(spark, group)}


def dir_size_mb(paths) -> float:
    total = 0
    for p in paths:
        p = Path(p)
        total += p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return round(total / 1e6, 1)


def fit_linear(x, y):
    """y ≈ a + b·x, trả về (a, b, R²): thời gian có tăng TUYẾN TÍNH theo kích thước không?"""
    x, y = np.asarray(x, float), np.asarray(y, float)
    b, a = np.polyfit(x, y, 1)
    r2 = 1 - ((y - (a + b * x)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return a, b, r2


def prepare_bench(spark, copies):
    """Ghi speeds_clean nhân bản `copies` lần vào BENCH/speeds_x16, partition theo rep (bỏ qua nếu đã có)."""
    out = BENCH / "speeds_x16"
    marker = out / f"_DONE_{copies}"
    if any(int(m.name.split("_")[-1]) >= copies for m in out.glob("_DONE_*")):
        return out   # đã có đủ số bản sao từ lần chạy trước
    src = spark.read.parquet(str(PATHS["speeds_clean"])).select("link_id", "timestamp", "speed_kmh")
    src = src.withColumn("link_id", F.col("link_id").cast("long"))
    reps = spark.range(copies).withColumnRenamed("id", "rep").withColumn("rep", F.col("rep").cast("int"))
    big = (src.crossJoin(F.broadcast(reps))
              .withColumn("link_id", F.col("link_id") * 100 + F.col("rep")))
    t0 = time.perf_counter()
    big.repartition("rep").write.mode("overwrite").partitionBy("rep").parquet(str(out))
    print(f"  đã ghi {copies} bản sao vào {out} trong {time.perf_counter() - t0:.0f} s")
    marker.touch()
    return out


# ---------------------------------------------------------------- main
# Job được chia thành các phần chạy độc lập (mỗi phần 1–3 phút), kết quả trung gian lưu ở BENCH/results_*.json.
# Lý do: môi trường chạy thử giới hạn mỗi lệnh 3 phút; chia phần cũng giúp chạy lại một phần khi bị lỗi.
PARTS = ("prepare", "A", "B", "C", "report")


def sizes(quick: bool):
    return ([1, 3] if quick else [1, 3, 6, 12]), ([1, 2, 4] if quick else [1, 2, 4, 8, 16])


def save_part(name, rows):
    (BENCH / f"results_{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def load_part(name):
    return json.loads((BENCH / f"results_{name}.json").read_text(encoding="utf-8"))


def part_A(spark, csv_sizes, repeat):
    rows = []
    for k in csv_sizes:
        months = MONTHS[:k]
        print(f"A. CSV {k} tháng …", flush=True)
        r = run(spark, lambda: read_raw_csv(spark, months), repeat)
        rows.append({"du_lieu": f"CSV {k} tháng", "size_mb": dir_size_mb(RAW / f"speeds_{m}.csv" for m in months), **r})
    save_part("A", rows)


def part_B(spark, copies, repeat):
    rows = []
    for k in copies:
        print(f"B. Parquet ×{k} …", flush=True)
        r = run(spark, lambda: read_bench(spark, k), repeat)
        rows.append({"du_lieu": f"Parquet ×{k}",
                     "size_mb": dir_size_mb(BENCH / "speeds_x16" / f"rep={i}" for i in range(k)), **r})
    save_part("B", rows)


def part_C(csv_k, pq_k):
    """Chạy lại trường hợp lớn với local[1]; so với kết quả local[*] của phần A/B."""
    spark1 = get_spark("s14_scalability_1core", cores="1")
    rows = []
    for name, build in ((f"CSV {csv_k} tháng", lambda: read_raw_csv(spark1, MONTHS[:csv_k])),
                        (f"Parquet ×{pq_k}", lambda: read_bench(spark1, pq_k))):
        print(f"C. local[1] {name} …", flush=True)
        rows.append({"du_lieu": name, **run(spark1, build, 2)})
    spark1.stop()
    save_part("C", rows)


def part_report(spark, quick):
    rep = Report("14_scalability", "Báo cáo bước 14 — Scalability benchmark", spark)
    parallelism = spark.sparkContext.defaultParallelism
    a, b = pd.DataFrame(load_part("A")), pd.DataFrame(load_part("B"))
    for d in (a, b):
        d["trieu_dong_moi_s"] = (d["rows"] / d["best_s"] / 1e6).round(2)
    rep.p(f"Job chuẩn: thống kê count/mean/min/max tốc độ theo (tuyến × giờ × ngày thường/cuối tuần). "
          f"Mỗi kích thước chạy nhiều lần, mỗi lần dựng DataFrame mới; `best_s` là lần nhanh nhất.")
    rep.h("A. CSV gốc: 1 → 12 tháng")
    rep.table(a, "csv")
    rep.h("B. Parquet đã làm sạch, nhân bản")
    rep.table(b, "parquet")

    fits = {}
    for name, d in (("CSV gốc", a), ("Parquet", b)):
        if len(d) >= 3:
            a0, b1, r2 = fit_linear(d["rows"] / 1e6, d["best_s"])
            fits[name] = {"chi_phi_co_dinh_s": round(a0, 2), "s_moi_trieu_dong": round(b1, 3), "r2": round(r2, 4)}
    rep.h("Hồi quy tuyến tính: thời gian = chi phí cố định + hệ số × số triệu dòng")
    rep.table(pd.DataFrame([{"du_lieu": k, **v} for k, v in fits.items()]), "linear_fit")

    if not quick:
        ca, pb = a.iloc[-1], b.iloc[0]
        cmp = pd.DataFrame([
            {"dinh_dang": f"{ca.du_lieu} (gốc)", "size_mb": ca.size_mb, "rows": int(ca.rows), "best_s": ca.best_s},
            {"dinh_dang": "Parquet ×1 (đã làm sạch)", "size_mb": pb.size_mb, "rows": int(pb.rows), "best_s": pb.best_s}])
        rep.h("CSV so với Parquet trên dữ liệu cùng một năm")
        rep.table(cmp, "format")

    c_rows = []
    for r1 in load_part("C"):
        ref = pd.concat([a, b]).set_index("du_lieu").loc[r1["du_lieu"]]
        c_rows.append({"du_lieu": r1["du_lieu"], "rows": r1["rows"], "local_1_s": r1["best_s"],
                       f"local_{parallelism}_s": ref["best_s"],
                       "speed_up": round(r1["best_s"] / ref["best_s"], 2),
                       "hieu_suat_song_song_pct": round(100 * r1["best_s"] / ref["best_s"] / parallelism, 1)})
    rep.h(f"C. Số nhân: local[1] so với local[{parallelism}]")
    rep.table(pd.DataFrame(c_rows), "cores")
    rep.p("`input_mb`: dữ liệu Spark thực sự đọc từ đĩa. `shuffle_mb`: dữ liệu trao đổi giữa các stage. "
          "`tasks`: số task của stage tốn bộ nhớ nhất. `peak_mem_moi_task_mb`: bộ nhớ thực thi đỉnh trung bình mỗi task "
          "của stage đó (chủ yếu là bảng băm của groupBy). "
          "Heap của driver được cấu hình 2 GB cho mọi kích thước dữ liệu.")
    rep.save()
    print("Xong: docs/bao-cao/14_scalability.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="bản rút gọn: CSV 1–3 tháng, Parquet ×1–×4")
    ap.add_argument("--part", choices=PARTS + ("all",), default="all")
    args = ap.parse_args()
    csv_sizes, copies = sizes(args.quick)
    parts = PARTS if args.part == "all" else (args.part,)
    BENCH.mkdir(parents=True, exist_ok=True)
    for part in parts:
        if part == "C":
            part_C(csv_sizes[-1], copies[-1] if args.quick else 8)
            continue
        spark = get_spark(f"s14_scalability_{part}")
        if part == "prepare":
            prepare_bench(spark, max(copies))
        elif part == "A":
            part_A(spark, csv_sizes, 3)
        elif part == "B":
            part_B(spark, copies, 3)
        elif part == "report":
            part_report(spark, args.quick)
        spark.stop()


if __name__ == "__main__":
    main()
