"""
Bước 12 — Query processing: Join→Filter so với Filter→Join (predicate pushdown).

    python -m spark_jobs.s12_query_processing

Truy vấn mẫu: "Tốc độ trung bình các tuyến ở QUEENS trong những giờ TRỜI MƯA của THÁNG 3/2024"
  speeds_clean (9 triệu bản ghi) ⨝ links (125 tuyến, lấy quận) ⨝ weather (43.915 trạm × giờ)

Thí nghiệm:
  A. Catalyst bật (mặc định)        : Q1 (join rồi filter) và Q2 (filter rồi join)
  B. Tắt quy tắc PushDownPredicates : Spark phải làm đúng thứ tự đã viết → đo chênh lệch thật
  C. Đọc Parquet: partition pruning, filter pushdown, và lỗi kiểu dữ liệu làm mất pushdown
Join dùng sort-merge (tắt broadcast) để chi phí join tỉ lệ với số dòng đi vào join — như trên cluster.
Mỗi lần đo dựng DataFrame MỚI (xem common.measure) để Spark không dùng lại kết quả shuffle cũ.
"""
from __future__ import annotations

import re

import pandas as pd
from pyspark.sql import functions as F

from spark_jobs.common import PATHS, Report, get_spark, measure

# Catalyst có NHIỀU quy tắc chồng lớp cùng đẩy filter xuống; tắt 1 quy tắc thì quy tắc khác vẫn đẩy được
# một phần (đã thử: chỉ tắt PushDownPredicates → filter vẫn bị đẩy xuống dưới join đầu tiên).
_O = "org.apache.spark.sql.catalyst.optimizer."
PUSHDOWN_RULE = ",".join(_O + r for r in ("PushDownPredicates", "PushPredicateThroughJoin",
                                          "PushPredicateThroughNonJoin", "CombineFilters",
                                          "InferFiltersFromConstraints"))



def inputs(spark):
    sp = (spark.read.parquet(str(PATHS["speeds_clean"]))
          .withColumn("hour_ts", F.date_trunc("hour", "timestamp").cast("timestamp_ntz"))
          .select("link_id", "hour_ts", "speed_kmh"))
    links = spark.read.parquet(str(PATHS["links_clean"])).select("link_id", "district")
    w = (spark.read.parquet(str(PATHS["weather_clean"]))
         .select("district", F.col("timestamp").alias("hour_ts"), "weather_condition"))
    return sp, links, w


def in_march(col):
    """Hằng TIMESTAMP_NTZ đúng kiểu với cột (tạo lúc dùng vì F.expr cần SparkSession đang chạy)."""
    start, end = F.expr("TIMESTAMP_NTZ'2024-03-01 00:00:00'"), F.expr("TIMESTAMP_NTZ'2024-04-01 00:00:00'")
    return (F.col(col) >= start) & (F.col(col) < end)


def q1_join_then_filter(spark):
    sp, links, w = inputs(spark)
    j = sp.join(links, "link_id").join(w, ["district", "hour_ts"])
    return (j.filter((F.col("district") == "Queens") & (F.col("weather_condition") == "Rain") & in_march("hour_ts"))
             .agg(F.count("*").alias("n"), F.round(F.avg("speed_kmh"), 3).alias("avg_kmh")))


def q2_filter_then_join(spark):
    sp, links, w = inputs(spark)
    sp_f = sp.filter(in_march("hour_ts"))
    links_f = links.filter(F.col("district") == "Queens")
    w_f = w.filter((F.col("district") == "Queens") & (F.col("weather_condition") == "Rain") & in_march("hour_ts"))
    return sp_f.join(links_f, "link_id").join(w_f, ["district", "hour_ts"]).agg(
        F.count("*").alias("n"), F.round(F.avg("speed_kmh"), 3).alias("avg_kmh"))


def filter_position(df) -> str:
    """Trong optimized plan: điều kiện lọc 'Rain' nằm TRÊN phép Join hay đã được đẩy XUỐNG dưới Join?"""
    lines = df._jdf.queryExecution().optimizedPlan().toString().splitlines()
    first_join = next(i for i, l in enumerate(lines) if "Join" in l)
    rain = next(i for i, l in enumerate(lines) if "Rain" in l)
    return "trên Join (lọc SAU khi join)" if rain < first_join else "dưới Join (lọc TRƯỚC khi join)"


def scan_info(df) -> dict:
    plan = df._jdf.queryExecution().executedPlan().toString()
    part = re.search(r"PartitionFilters: \[([^\]]*)\]", plan)
    push = re.search(r"PushedFilters: \[([^\]]*)\]", plan)
    return {"PartitionFilters": (part.group(1)[:55] if part and part.group(1) else "—"),
            "PushedFilters": (push.group(1)[:75] if push and push.group(1) else "—")}


def main() -> None:
    spark = get_spark("s12_query_processing", extra={"spark.sql.autoBroadcastJoinThreshold": "-1"})
    rep = Report("12_query_processing", "Báo cáo bước 12 — Query processing: Join→Filter vs Filter→Join", spark)
    sp, _, _ = inputs(spark)
    rows_all, rows_march = sp.count(), sp.filter(in_march("hour_ts")).count()

    rows = []
    for exp, excluded in (("A. Catalyst bật", None), ("B. Tắt 5 quy tắc đẩy filter", PUSHDOWN_RULE)):
        if excluded:
            spark.conf.set("spark.sql.optimizer.excludedRules", excluded)
        for name, build in (("Q1: Join → Filter", q1_join_then_filter), ("Q2: Filter → Join", q2_filter_then_join)):
            df = build(spark)
            r = df.collect()[0]
            pos = filter_position(df)
            m = measure(lambda: build(spark))
            rows.append({"thi_nghiem": exp, "truy_van": name, "vi_tri_dieu_kien_loc": pos,
                         "dong_toc_do_vao_join": rows_all if pos.startswith("trên") else rows_march,
                         "lan_dau_s": m["first_s"], "tot_nhat_s": m["best_s"], "n": r["n"], "avg_kmh": r["avg_kmh"]})
        spark.conf.unset("spark.sql.optimizer.excludedRules")
    res = pd.DataFrame(rows)
    same = res[["n", "avg_kmh"]].nunique().eq(1).all()
    b = res[res.thi_nghiem.str.startswith("B")].set_index("truy_van")["tot_nhat_s"]
    a = res[res.thi_nghiem.str.startswith("A")].set_index("truy_van")["tot_nhat_s"]
    rep.h("Thí nghiệm A và B")
    rep.table(res, "experiments")
    rep.p(f"- Kết quả 4 lần chạy **{'giống hệt nhau' if same else 'KHÁC NHAU'}**: "
          f"{int(res.n.iloc[0]):,} bản ghi, {res.avg_kmh.iloc[0]} km/h.")
    rep.p(f"- A (Catalyst bật): Q1/Q2 = {a.iloc[0] / a.iloc[1]:.2f} lần.")
    rep.p(f"- B (tắt pushdown): Q1 chậm hơn Q2 **{b.iloc[0] / b.iloc[1]:.1f} lần**.")
    rep.data.update({"rows_all": rows_all, "rows_march": rows_march, "results_equal": bool(same),
                     "ratio_A": round(a.iloc[0] / a.iloc[1], 2), "ratio_B": round(b.iloc[0] / b.iloc[1], 2)})

    # C. Đọc Parquet
    base = lambda: spark.read.parquet(str(PATHS["speeds_clean"]))
    agg = lambda df: df.agg(F.count("*").alias("n"), F.avg("speed_kmh").alias("avg"))
    cases = [
        ("Không lọc", lambda: agg(base()), None),
        ("Cột partition: month = '2024-03'", lambda: agg(base().filter(F.col("month") == "2024-03")), None),
        ("Cột timestamp, so với hằng TIMESTAMP_NTZ (đúng kiểu)", lambda: agg(base().filter(in_march("timestamp"))), None),
        ("Cột timestamp, so với CHUỖI '2024-03-01' (sai kiểu)",
         lambda: agg(base().filter((F.col("timestamp") >= "2024-03-01") & (F.col("timestamp") < "2024-04-01"))), None),
        ("Cột timestamp đúng kiểu, TẮT Parquet pushdown", lambda: agg(base().filter(in_march("timestamp"))),
         ("spark.sql.parquet.filterPushdown", "false")),
    ]
    crow = []
    for name, build, conf in cases:
        if conf:
            spark.conf.set(*conf)
        df = build()
        n = df.collect()[0]["n"]
        crow.append({"cach_doc": name, "so_dong": n, **measure(build), **scan_info(df)})
        if conf:
            spark.conf.unset(conf[0])
    rep.h("Thí nghiệm C — Đọc Parquet: partition pruning và filter pushdown")
    rep.table(pd.DataFrame(crow), "parquet_read")

    rep.save()
    spark.stop()
    print("Xong: docs/bao-cao/12_query_processing.md")


if __name__ == "__main__":
    main()
