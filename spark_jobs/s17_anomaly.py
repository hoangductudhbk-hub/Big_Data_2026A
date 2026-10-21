"""
Bước 17 — Anomaly detection bằng Z-score.

    python -m spark_jobs.s17_anomaly                         # dữ liệu thật
    INTEGRATED_PATH=data/mock/integrated_traffic python -m spark_jobs.s17_anomaly --validate
                                                             # kiểm chứng trên mock có bất thường cài sẵn

z = (x − mean) / std,  |z| > 3 → anomaly   (plan, mục 13)

Hai cách chọn "mean, std":
  1. Z-score TOÀN CỤC theo đường: mean/std của đường đó cả năm.
     → giờ cao điểm (tắc nghẽn bình thường, ngày nào cũng có) bị báo là bất thường.
  2. Z-score THEO NGỮ CẢNH: mean/std của CÙNG đường, CÙNG giờ, CÙNG loại ngày (ngày thường/cuối tuần+lễ).
     → chỉ báo những gì khác với "bình thường của đúng thời điểm đó". Đây là cách được chọn.
Áp dụng cho avg_speed (tốc độ) và vehicle_count (lưu lượng).

Đầu ra:
  data/processed/analytics/anomalies.parquet       các bản ghi |z| > 3 (đúng các cột plan yêu cầu + ngữ cảnh)
  data/processed/analytics/anomaly_daily.parquet   số bất thường theo ngày (phát hiện "ngày bất thường" của cả thành phố)
"""
from __future__ import annotations

import argparse

import pandas as pd
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from spark_jobs.common import PATHS, Report, get_spark, save_analytics
from spark_jobs.s16_weather_impact import HOLIDAYS_2024

Z_THRESHOLD = 3.0
# Số quan sát tối thiểu của một ô để std đáng tin. Lưu lượng đếm theo đợt 1–2 tuần → ô chỉ có ~5–10 giờ.
MIN_N = {"avg_speed": 20, "vehicle_count": 6}
CONTEXT = ["road_id", "hour", "day_type"]


def load(spark) -> DataFrame:
    df = spark.read.parquet(str(PATHS["integrated"]))
    return (df.withColumn("hour", F.hour("timestamp"))
              .withColumn("date", F.to_date("timestamp"))
              .withColumn("day_type", F.when(F.dayofweek("timestamp").isin(1, 7)
                                             | F.col("date").cast("string").isin(*HOLIDAYS_2024), "weekend")
                                       .otherwise("weekday")))


def zscore(df: DataFrame, metric: str, keys: list[str], min_n: int, loo: bool = False) -> DataFrame:
    """Thêm expected/std/z theo `keys` bằng window function (không cần join).

    loo=False: mean/std tính trên CẢ ô, gồm chính điểm đang xét (công thức gốc của plan).
    loo=True : leave-one-out — mean/std tính trên các điểm KHÁC trong ô. Lý do: với ô có n điểm, z thường
               bị chặn |z| ≤ (n−1)/√n (n = 10 → 2,85), nên ô nhỏ KHÔNG BAO GIỜ đạt |z| > 3 dù giá trị lạ đến đâu;
               ngoài ra chính điểm bất thường làm std phình ra và "che" mình đi (masking).
    Ô có < min_n điểm (không kể điểm đang xét khi loo) → z = null."""
    w = Window.partitionBy(*keys)
    x = F.col(metric).cast("double")
    d = (df.filter(F.col(metric).isNotNull())
           .withColumn("_n", F.count(metric).over(w))
           .withColumn("_s", F.sum(x).over(w))
           .withColumn("_q", F.sum(x * x).over(w)))
    if loo:
        m = F.col("_n") - 1                                          # số điểm còn lại
        mean = (F.col("_s") - x) / m
        var = (F.col("_q") - x * x - m * mean * mean) / (m - 1)      # phương sai mẫu của các điểm còn lại
    else:
        m = F.col("_n")
        mean = F.col("_s") / m
        var = (F.col("_q") - m * mean * mean) / (m - 1)
    d = (d.withColumn("cell_n", m)
          .withColumn("expected", F.when(m >= 1, mean))
          .withColumn("std", F.when(m >= 2, F.sqrt(F.greatest(var, F.lit(0.0))))))
    return (d.withColumn("z_score", F.when((F.col("cell_n") >= min_n) & (F.col("std") > 1e-9),
                                           (x - F.col("expected")) / F.col("std")))
             .drop("_n", "_s", "_q"))


def summarize(d: DataFrame, metric: str, method: str) -> dict:
    r = (d.agg(F.count("*").alias("n"), F.count("z_score").alias("n_scored"),
               F.sum((F.abs("z_score") > Z_THRESHOLD).cast("int")).alias("n_anom"),
               F.sum((F.col("z_score") < -Z_THRESHOLD).cast("int")).alias("n_low"),
               F.sum((F.col("z_score") > Z_THRESHOLD).cast("int")).alias("n_high"),
               F.sum(((F.abs("z_score") > Z_THRESHOLD) & F.col("hour").isin(7, 8, 9, 16, 17, 18)
                      & (F.col("day_type") == "weekday")).cast("int")).alias("n_peak"))
          .collect()[0].asDict())
    return {"metric": metric, "phuong_phap": method, "ban_ghi": r["n"], "duoc_cham_z": r["n_scored"],
            "bat_thuong": r["n_anom"], "ti_le_pct": round(100 * r["n_anom"] / max(r["n_scored"], 1), 3),
            "thap_bat_thuong": r["n_low"], "cao_bat_thuong": r["n_high"],
            "trong_gio_cao_diem_pct": round(100 * r["n_peak"] / max(r["n_anom"], 1), 1)}


def validate(spark, rep: Report, ctx: dict) -> None:
    """So với đáp án đã cài trong mock (scripts/generate_mock_integrated.py): precision, recall."""
    labels_path = PATHS["integrated"].parent / "injected_anomalies.parquet"
    if not labels_path.exists():
        rep.p(f"Không có {labels_path}: chạy lại scripts/generate_mock_integrated.py để sinh đáp án.")
        return
    truth = spark.read.parquet(str(labels_path)).select("road_id", "timestamp", F.lit(True).alias("injected"))
    rows, sweep = [], []
    for metric, d in ctx.items():
        for method, dd in d.items():
            j = (dd.filter(F.col("z_score").isNotNull())
                   .join(F.broadcast(truth), ["road_id", "timestamp"], "left")
                   .withColumn("injected", F.coalesce("injected", F.lit(False)))
                   .withColumn("wet", (F.col("rainfall") > 0) | (F.col("snowfall") > 0)))
            thresholds = (3.0, 4.0, 5.0) if method.startswith("Theo ngữ cảnh") else (Z_THRESHOLD,)
            for t in thresholds:
                pred = F.abs("z_score") > t
                c = j.agg(F.sum((pred & F.col("injected")).cast("int")).alias("tp"),
                          F.sum((pred & ~F.col("injected")).cast("int")).alias("fp"),
                          F.sum((~pred & F.col("injected")).cast("int")).alias("fn"),
                          F.sum((pred & ~F.col("injected") & F.col("wet")).cast("int")).alias("fp_wet")).collect()[0]
                tp, fp, fn = c["tp"], c["fp"], c["fn"]
                p = tp / (tp + fp) if tp + fp else 0.0
                r = tp / (tp + fn) if tp + fn else 0.0
                row = {"metric": metric, "phuong_phap": method, "nguong": t, "cai_san": tp + fn, "bao": tp + fp,
                       "dung": tp, "precision": round(p, 3), "recall": round(r, 3),
                       "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
                       "bao_thua_luc_mua_tuyet_pct": round(100 * c["fp_wet"] / fp, 1) if fp else 0.0}
                (rows if t == Z_THRESHOLD else sweep).append(row)
    rep.h("Kiểm chứng trên mock: so với bất thường đã cài sẵn")
    rep.table(pd.DataFrame(rows), "validation")
    rep.p("`bao_thua_luc_mua_tuyet_pct`: trong các bản ghi bị báo nhưng KHÔNG phải bất thường cài sẵn, bao nhiêu % "
          "rơi vào giờ có mưa/tuyết (mock cố ý làm xe chậm khi mưa/tuyết, xem bước 04).")
    rep.p("**Tăng ngưỡng |z| (cách theo ngữ cảnh):**")
    rep.table(pd.DataFrame([r for r in rows if r["phuong_phap"].startswith("Theo ngữ cảnh")] + sweep)
              .sort_values(["metric", "nguong"]), "threshold_sweep")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="đo precision/recall với đáp án của mock")
    args = ap.parse_args()
    spark = get_spark("s17_anomaly")
    step = "17_anomaly_mock" if args.validate else "17_anomaly"
    rep = Report(step, "Báo cáo bước 17 — Anomaly detection bằng Z-score" + (" (mock)" if args.validate else ""), spark)
    df = load(spark).cache()

    ctx, summary = {}, []
    for metric in ("avg_speed", "vehicle_count"):
        g = zscore(df, metric, ["road_id"], MIN_N[metric]).cache()
        c = zscore(df, metric, CONTEXT, MIN_N[metric], loo=True).cache()
        ctx[metric] = {"Toàn cục theo đường": g, "Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày)": c}
        summary += [summarize(g, metric, "Toàn cục theo đường"),
                    summarize(c, metric, "Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày)")]
    rep.h("So sánh hai cách tính Z-score")
    rep.p(f"Ngưỡng |z| > {Z_THRESHOLD:g}. Nếu dữ liệu phân phối chuẩn, tỉ lệ kỳ vọng là 0,27%. "
          f"`trong_gio_cao_diem_pct`: % bất thường rơi vào 7–9h, 16–18h ngày thường.")
    rep.table(pd.DataFrame(summary), "methods")

    if args.validate:
        validate(spark, rep, ctx)

    # Kết quả chính: Z-score theo ngữ cảnh
    road_info = df.select("road_id", "road_name", "district").dropDuplicates(["road_id"])
    anomalies = None
    for metric in ("avg_speed", "vehicle_count"):
        a = (ctx[metric]["Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày)"]
             .filter(F.abs("z_score") > Z_THRESHOLD)
             .select("road_id", "timestamp", F.lit(metric).alias("metric"),
                     F.col(metric).cast("double").alias("value"),
                     F.round("expected", 2).alias("expected"), F.round("std", 2).alias("std"),
                     F.round("z_score", 2).alias("z_score"), F.lit(True).alias("is_anomaly"),
                     F.when(F.col("z_score") < 0, "thấp bất thường").otherwise("cao bất thường").alias("direction"),
                     "vehicle_count", "avg_speed", "weather_condition", "rainfall", "snowfall", "date"))
        anomalies = a if anomalies is None else anomalies.unionByName(a)
    anomalies = anomalies.join(F.broadcast(road_info), "road_id").cache()
    n_anom = anomalies.count()
    save_analytics(anomalies.drop("date").orderBy("timestamp"), "anomalies" + ("_mock" if args.validate else ""))
    rep.data["n_anomalies"] = n_anom

    cols = ["road_id", "road_name", "district", "timestamp", "value", "expected", "z_score", "weather_condition"]
    for metric, label in (("avg_speed", "tốc độ (km/h)"), ("vehicle_count", "lưu lượng (xe/giờ)")):
        top = anomalies.filter(F.col("metric") == metric).orderBy(F.asc("z_score") if metric == "avg_speed"
                                                                  else F.desc("z_score")).limit(10).toPandas()
        top["timestamp"] = top["timestamp"].astype(str)
        rep.h(f"10 bất thường {label} mạnh nhất")
        rep.table(top[cols], f"top_{metric}")

    # Ngày bất thường của cả thành phố: nhiều đường cùng bất thường một lúc → sự kiện chung (thời tiết, lễ, sự cố lớn)
    speed_rows = ctx["avg_speed"]["Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày)"].filter(F.col("z_score").isNotNull())
    daily = (speed_rows.groupBy("date")
             .agg(F.count("*").alias("ban_ghi"),
                  F.sum((F.col("z_score") < -Z_THRESHOLD).cast("int")).alias("cham_bat_thuong"),
                  F.sum((F.col("z_score") > Z_THRESHOLD).cast("int")).alias("nhanh_bat_thuong"),
                  F.round(F.avg("z_score"), 3).alias("z_tb"),
                  F.round(F.avg("rainfall") * 24, 1).alias("mua_mm_ngay"),
                  F.round(F.sum("snowfall") / F.countDistinct("road_id"), 1).alias("tuyet_cm_ngay"),
                  F.first("day_type").alias("day_type"))
             .withColumn("ti_le_bat_thuong_pct",
                         F.round(100 * (F.col("cham_bat_thuong") + F.col("nhanh_bat_thuong")) / F.col("ban_ghi"), 2))
             .orderBy("date"))
    if PATHS["coverage"].exists():   # cờ ngày mất dữ liệu (bước 07): ngày thiếu dữ liệu cũng hay "bất thường"
        cov = spark.read.parquet(str(PATHS["coverage"])).select(F.to_date("date").alias("date"),
                                                                 F.col("coverage_pct").alias("do_phu_pct"))
        daily = daily.join(F.broadcast(cov), "date", "left").orderBy("date")
    save_analytics(daily, "anomaly_daily" + ("_mock" if args.validate else ""))
    dp = daily.toPandas()
    dp["date"] = dp["date"].astype(str)
    show = ["date", "day_type", "ban_ghi", "cham_bat_thuong", "nhanh_bat_thuong", "ti_le_bat_thuong_pct", "z_tb",
            "mua_mm_ngay", "tuyet_cm_ngay"] + (["do_phu_pct"] if PATHS["coverage"].exists() else [])
    rep.h("Những ngày bất thường của cả thành phố (tốc độ)")
    rep.p("**10 ngày có tỉ lệ CHẬM bất thường cao nhất**")
    rep.table(dp.assign(r=dp.cham_bat_thuong / dp.ban_ghi).nlargest(10, "r")[show], "slow_days")
    rep.p("**10 ngày có tỉ lệ NHANH bất thường cao nhất**")
    rep.table(dp.assign(r=dp.nhanh_bat_thuong / dp.ban_ghi).nlargest(10, "r")[show], "fast_days")

    # Đường hay bất thường nhất
    by_road = (anomalies.filter(F.col("metric") == "avg_speed").groupBy("road_id", "road_name", "district")
               .agg(F.count("*").alias("so_bat_thuong"), F.sum((F.col("z_score") < 0).cast("int")).alias("cham"),
                    F.round(F.min("z_score"), 2).alias("z_min"))
               .orderBy(F.desc("so_bat_thuong")).limit(10).toPandas())
    rep.h("10 đường có nhiều bất thường tốc độ nhất")
    rep.table(by_road, "by_road")

    rep.save()
    spark.stop()
    print(f"Xong: docs/bao-cao/{step}.md")


if __name__ == "__main__":
    main()
