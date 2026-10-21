"""
Bước 15 — Statistical analysis trên integrated_traffic.

    python -m spark_jobs.s15_statistics

Theo plan (mục 11): count, mean, min, max, standard deviation, median
theo giờ, ngày, đường, quận, điều kiện thời tiết — cho hai chỉ số avg_speed (km/h) và vehicle_count (xe/giờ).

Đầu ra (data/processed/analytics/, để Phase 3 nạp vào PostgreSQL):
  statistics.parquet    bảng DÀI: dimension, group_key, metric, n, mean, std, min, max, median
                        → một bảng duy nhất phục vụ mọi biểu đồ thống kê trên dashboard
  daily_stats.parquet   chuỗi theo ngày (kèm cờ is_outage của ngày mất dữ liệu) cho biểu đồ thời gian
  road_stats.parquet    thống kê theo từng đường kèm tên, quận, tọa độ (cho bản đồ)
"""
from __future__ import annotations

from functools import reduce

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from spark_jobs.common import PATHS, Report, get_spark, save_analytics

METRICS = ("avg_speed", "vehicle_count")
DOW_NAMES = {1: "CN", 2: "T2", 3: "T3", 4: "T4", 5: "T5", 6: "T6", 7: "T7"}


def load(spark) -> DataFrame:
    df = spark.read.parquet(str(PATHS["integrated"]))
    return (df.withColumn("hour", F.hour("timestamp"))
              .withColumn("dow", F.dayofweek("timestamp"))                       # 1 = Chủ nhật … 7 = Thứ bảy
              .withColumn("day_type", F.when(F.col("dow").isin(1, 7), "Cuối tuần").otherwise("Ngày thường"))
              .withColumn("date", F.to_date("timestamp"))
              .withColumn("month_str", F.date_format("timestamp", "yyyy-MM")))


def describe(df: DataFrame, keys: list[str], metric: str) -> DataFrame:
    """count, mean, std, min, max, median của `metric` theo `keys`. Bỏ giá trị null (đúng nghĩa 'không đo')."""
    return (df.filter(F.col(metric).isNotNull()).groupBy(*keys)
              .agg(F.count(metric).alias("n"),
                   F.avg(metric).alias("mean"),
                   F.stddev_samp(metric).alias("std"),
                   F.min(metric).cast("double").alias("min"),
                   F.max(metric).cast("double").alias("max"),
                   F.expr(f"percentile({metric}, 0.5)").alias("median")))


def dimensions() -> dict:
    """Các chiều phân tích: tên → (cột nhóm, biểu thức tạo group_key dạng chuỗi).
    Là hàm (không phải hằng cấp module) vì F.lit/F.col cần SparkSession đang chạy."""
    return {
        "overall": ([], F.lit("Tất cả")),
        "hour": (["hour"], F.format_string("%02dh", "hour")),
        "hour_daytype": (["day_type", "hour"], F.format_string("%s %02dh", "day_type", "hour")),
        "day_of_week": (["dow"], F.concat(F.col("dow").cast("string"), F.lit("-"),
                                          F.element_at(F.create_map(*[x for k, v in DOW_NAMES.items()
                                                                      for x in (F.lit(k), F.lit(v))]), F.col("dow")))),
        "day_type": (["day_type"], F.col("day_type")),
        "month": (["month_str"], F.col("month_str")),
        "district": (["district"], F.col("district")),
        "road": (["road_id"], F.col("road_id")),
        "weather_condition": (["weather_condition"], F.col("weather_condition")),
    }


def long_table(df: DataFrame) -> DataFrame:
    parts = []
    for dim, (keys, key_expr) in dimensions().items():
        for m in METRICS:
            s = describe(df, keys, m)
            parts.append(s.select(F.lit(dim).alias("dimension"), key_expr.alias("group_key"), F.lit(m).alias("metric"),
                                  "n", F.round("mean", 3).alias("mean"), F.round("std", 3).alias("std"),
                                  "min", "max", F.round("median", 3).alias("median")))
    return reduce(DataFrame.unionByName, parts)


def view(stats: pd.DataFrame, dim: str, metric: str, sort: str = "group_key") -> pd.DataFrame:
    v = stats[(stats.dimension == dim) & (stats.metric == metric)].drop(columns=["dimension", "metric"])
    return v.sort_values(sort).reset_index(drop=True)


def main() -> None:
    spark = get_spark("s15_statistics")
    rep = Report("15_statistics", "Báo cáo bước 15 — Statistical analysis", spark)
    df = load(spark).cache()
    total = df.count()

    stats_sdf = long_table(df)
    stats = stats_sdf.toPandas()
    save_analytics(stats_sdf, "statistics")
    rep.data["statistics_rows"] = len(stats)

    # --- Tổng quan
    rep.h("Tổng quan")
    rep.p(f"Bảng `integrated_traffic`: {total:,} dòng. Thống kê bỏ qua giá trị null: `avg_speed` chỉ có ở nguồn tốc độ, "
          f"`vehicle_count` chỉ có ở nguồn lưu lượng.")
    rep.table(stats[stats.dimension == "overall"].drop(columns=["dimension", "group_key"]), "overall")

    # --- Theo giờ × loại ngày
    rep.h("Theo giờ trong ngày (ngày thường / cuối tuần)")
    hd = stats[(stats.dimension == "hour_daytype")].copy()
    hd["day_type"] = hd.group_key.str[:-4]
    hd["hour"] = hd.group_key.str[-3:-1].astype(int)
    piv = hd.pivot_table(index="hour", columns=["metric", "day_type"], values="mean").round(1)
    piv.columns = [f"{m}_{d}" for m, d in piv.columns]
    rep.table(piv.reset_index(), "hour_daytype")
    wk = hd[(hd.day_type == "Ngày thường") & (hd.metric == "avg_speed")].set_index("hour")["mean"]
    vk = hd[(hd.day_type == "Ngày thường") & (hd.metric == "vehicle_count")].set_index("hour")["mean"]
    rep.p(f"Ngày thường: tốc độ thấp nhất lúc {wk.idxmin()}h ({wk.min():.1f} km/h), cao nhất lúc {wk.idxmax()}h "
          f"({wk.max():.1f} km/h). Lưu lượng cao nhất lúc {vk.idxmax()}h ({vk.max():.0f} xe/giờ).")
    rep.data["weekday_speed_min_hour"], rep.data["weekday_volume_max_hour"] = int(wk.idxmin()), int(vk.idxmax())

    for dim, title in (("day_of_week", "Theo thứ trong tuần"), ("month", "Theo tháng"),
                       ("district", "Theo quận"), ("weather_condition", "Theo điều kiện thời tiết")):
        rep.h(title)
        for m in METRICS:
            rep.p(f"**{m}**")
            rep.table(view(stats, dim, m), f"{dim}_{m}")

    # --- Theo đường: kèm tên/quận, lưu cho bản đồ
    roads = (df.groupBy("road_id", "road_name", "district")
               .agg(F.first("latitude").alias("latitude"), F.first("longitude").alias("longitude"),
                    F.count("avg_speed").alias("n_speed"), F.round(F.avg("avg_speed"), 2).alias("mean_speed"),
                    F.round(F.stddev_samp("avg_speed"), 2).alias("std_speed"),
                    F.count("vehicle_count").alias("n_volume"), F.round(F.avg("vehicle_count"), 1).alias("mean_volume"),
                    F.max("vehicle_count").alias("max_volume")))
    save_analytics(roads, "road_stats")
    rp = roads.toPandas()
    sp = rp[rp.n_speed >= 1000]
    cols = ["road_id", "road_name", "district", "n_speed", "mean_speed", "std_speed"]
    rep.h("Theo đường")
    rep.p(f"{len(rp)} đường: {int((rp.n_speed > 0).sum())} có dữ liệu tốc độ, {int((rp.n_volume > 0).sum())} có lưu lượng. "
          f"Chỉ xếp hạng tốc độ các đường có ≥ 1.000 giờ dữ liệu ({len(sp)} đường).")
    rep.p("**10 đường chậm nhất (tốc độ trung bình cả năm)**")
    rep.table(sp.nsmallest(10, "mean_speed")[cols], "slowest_roads")
    rep.p("**10 đường nhanh nhất**")
    rep.table(sp.nlargest(10, "mean_speed")[cols], "fastest_roads")
    rep.p("**10 đường biến động tốc độ lớn nhất (độ lệch chuẩn)**: đường hay tắc theo giờ")
    rep.table(sp.nlargest(10, "std_speed")[cols], "most_variable_roads")
    vp = rp[rp.n_volume >= 24]
    rep.p(f"**10 điểm đếm có lưu lượng trung bình cao nhất** (trong {len(vp)} đường có ≥ 24 giờ đếm)")
    rep.table(vp.nlargest(10, "mean_volume")[["road_id", "road_name", "district", "n_volume", "mean_volume", "max_volume"]],
              "busiest_roads")

    # --- Theo ngày: chuỗi thời gian, đánh dấu ngày mất dữ liệu
    cov = spark.read.parquet(str(PATHS["coverage"])).select(F.to_date("date").alias("date"), "coverage_pct", "is_outage")
    daily = (df.groupBy("date")
               .agg(F.count("avg_speed").alias("n_speed"), F.round(F.avg("avg_speed"), 2).alias("mean_speed"),
                    F.count("vehicle_count").alias("n_volume"), F.round(F.avg("vehicle_count"), 1).alias("mean_volume"),
                    F.round(F.avg("temperature"), 1).alias("temperature"), F.round(F.avg("rainfall") * 24, 1).alias("rain_mm_per_day"),     # TB theo các bản ghi
                    F.round(F.avg("snowfall") * 24, 1).alias("snow_cm_per_day"))
               .join(cov, "date", "left").orderBy("date"))
    save_analytics(daily, "daily_stats")
    dp = daily.toPandas()
    ok = dp[~dp.is_outage.fillna(False).astype(bool)]
    rep.h("Theo ngày")
    rep.p(f"{len(dp)} ngày có dữ liệu, {int(dp.is_outage.fillna(False).astype(bool).sum())} ngày bị đánh dấu mất dữ liệu "
          f"(độ phủ < 50%, bước 07). Trên {len(ok)} ngày còn lại:")
    rep.table(pd.DataFrame([{"chi_so": "Tốc độ TB của ngày (km/h)", "mean": ok.mean_speed.mean(),
                             "std": ok.mean_speed.std(), "min": ok.mean_speed.min(), "max": ok.mean_speed.max(),
                             "ngay_cham_nhat": str(ok.loc[ok.mean_speed.idxmin(), "date"]),
                             "ngay_nhanh_nhat": str(ok.loc[ok.mean_speed.idxmax(), "date"])}]), "daily_summary")
    rep.p("**5 ngày chậm nhất**")
    rep.table(ok.nsmallest(5, "mean_speed")[["date", "mean_speed", "n_speed", "temperature", "rain_mm_per_day",
                                             "snow_cm_per_day"]].astype({"date": str}), "slowest_days")

    # --- Tự kiểm tra: tính lại 1 nhóm bằng pandas (độc lập với Spark)
    q = df.filter(F.col("district") == "Manhattan").select("avg_speed").dropna().toPandas()["avg_speed"]
    s = view(stats, "district", "avg_speed").set_index("group_key").loc["Manhattan"]
    check = {"n": (len(q), int(s.n)), "mean": (round(q.mean(), 3), s["mean"]), "std": (round(q.std(), 3), s["std"]),
             "median": (round(q.median(), 3), s["median"])}
    rep.h("Tự kiểm tra: Manhattan / avg_speed tính lại bằng pandas")
    rep.table(pd.DataFrame([{"chi_so": k, "pandas": v[0], "spark": v[1], "khop": abs(v[0] - v[1]) < 1e-3}
                            for k, v in check.items()]), "self_check")

    df.unpersist()
    rep.save()
    spark.stop()
    print("Xong: docs/bao-cao/15_statistics.md")


if __name__ == "__main__":
    main()
