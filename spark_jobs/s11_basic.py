"""
Bước 11 — PySpark: các phép xử lý cơ bản trên dữ liệu thật.

    python -m spark_jobs.s11_basic

Minh họa và đo thời gian: lazy evaluation · select/filter · join (broadcast vs sort-merge) ·
groupBy/aggregation · sort · Spark SQL · cache.
Đầu ra: docs/bao-cao/11_spark_basic.md, data/processed/analytics/hourly_profile.parquet
"""
from __future__ import annotations

import time

from pyspark.sql import functions as F

from spark_jobs.common import PATHS, Report, get_spark, measure, save_analytics


def plan_text(df) -> str:
    """Lấy physical plan (rút gọn) để đưa vào báo cáo."""
    return df._jdf.queryExecution().executedPlan().toString()


def main() -> None:
    spark = get_spark("s11_basic")
    rep = Report("11_spark_basic", "Báo cáo bước 11 — PySpark cơ bản", spark)
    it = spark.read.parquet(str(PATHS["integrated"]))
    sp = spark.read.parquet(str(PATHS["speeds_clean"]))
    links = spark.read.parquet(str(PATHS["links_clean"]))

    # 1. Lazy evaluation: transformation không chạy gì, chỉ action mới thực thi
    t0 = time.perf_counter()
    q = it.filter(F.col("avg_speed").isNotNull()).withColumn("hour", F.hour("timestamp")).groupBy("hour").count()
    t_define = time.perf_counter() - t0
    t0 = time.perf_counter()
    q.collect()
    t_action = time.perf_counter() - t0
    rep.h("1. Lazy evaluation")
    rep.p(f"Khai báo filter → withColumn → groupBy (transformation): **{t_define * 1000:.1f} ms** — Spark chỉ dựng kế hoạch.")
    rep.p(f"Gọi `collect()` (action): **{t_action:.2f} s** — lúc này Spark mới đọc dữ liệu và tính.")
    rep.data["lazy"] = {"define_ms": round(t_define * 1000, 1), "action_s": round(t_action, 3)}

    # 2. select + filter: BQE giờ cao điểm sáng ngày thường
    bqe = (it.select("road_id", "road_name", "timestamp", "avg_speed", "weather_condition")
             .filter(F.col("road_name").startswith("BROOKLYN QUEENS EXPRESSWAY"))
             .filter(F.hour("timestamp").between(7, 9) & F.dayofweek("timestamp").between(2, 6))
             .filter(F.col("avg_speed").isNotNull()))
    n_total, n_bqe = it.count(), bqe.count()
    res = bqe.agg(F.round(F.avg("avg_speed"), 1).alias("toc_do_tb_kmh"), F.countDistinct("road_id").alias("so_tuyen"))
    rep.h("2. select + filter")
    rep.p(f"BQE, 7–9h ngày thường: {n_bqe:,} / {n_total:,} dòng sau filter.")
    rep.table(res.toPandas(), "bqe_peak")
    rep.p("Filter trên cột của Parquet được đẩy xuống lớp đọc file (`PushedFilters` trong plan):")
    rep.code("\n".join(l for l in plan_text(bqe).splitlines() if "PushedFilters" in l or "FileScan" in l)[:900])

    # 3. join: 9 triệu bản ghi tốc độ ⨝ 125 tuyến (để lấy quận) — broadcast vs sort-merge
    def build_join():
        return sp.join(links.select("link_id", "district"), "link_id").groupBy("district").agg(
            F.count("*").alias("so_ban_ghi"), F.round(F.avg("speed_kmh"), 1).alias("toc_do_tb_kmh"))
    joined = build_join()
    bc_plan = "BroadcastHashJoin" if "BroadcastHashJoin" in plan_text(joined) else "?"
    m_bc = measure(build_join)
    spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")          # tắt broadcast → sort-merge join
    smj_plan = "SortMergeJoin" if "SortMergeJoin" in plan_text(build_join()) else "?"
    m_smj = measure(build_join)
    spark.conf.unset("spark.sql.autoBroadcastJoinThreshold")
    t_bc, t_smj = m_bc["best_s"], m_smj["best_s"]
    rep.h("3. join (9.048.108 bản ghi tốc độ ⨝ 125 tuyến)")
    rep.table(joined.orderBy("district").toPandas(), "join_by_district")
    rep.p(f"| Chiến lược | Plan | Lần đầu | Tốt nhất / 3 lần |\n|---|---|---|---|\n"
          f"| Broadcast (mặc định: bảng nhỏ < 10 MB) | {bc_plan} | {m_bc['first_s']:.2f} s | {t_bc:.2f} s |\n"
          f"| Sort-merge (tắt broadcast) | {smj_plan} | {m_smj['first_s']:.2f} s | {t_smj:.2f} s |")
    rep.data["join"] = {"broadcast": m_bc, "sortmerge": m_smj, "speedup": round(t_smj / t_bc, 2)}

    # 4. groupBy + aggregation: hồ sơ giao thông theo giờ trong ngày
    hourly = (it.withColumn("hour", F.hour("timestamp"))
                .withColumn("loai_ngay", F.when(F.dayofweek("timestamp").isin(1, 7), "cuối tuần").otherwise("ngày thường"))
                .groupBy("loai_ngay", "hour")
                .agg(F.round(F.avg("avg_speed"), 1).alias("toc_do_tb_kmh"),
                     F.round(F.avg("vehicle_count"), 0).alias("luu_luong_tb"),
                     F.count("avg_speed").alias("n_toc_do"), F.count("vehicle_count").alias("n_luu_luong"))
                .orderBy("loai_ngay", "hour"))
    save_analytics(hourly, "hourly_profile")
    hp = hourly.toPandas()
    rep.h("4. groupBy + aggregation: hồ sơ theo giờ")
    rep.table(hp[hp["hour"].isin([3, 6, 8, 12, 17, 20, 23])], "hourly_sample")

    # 5. sort: 10 tuyến chậm nhất giờ cao điểm chiều (16–19h ngày thường), tối thiểu 200 giờ dữ liệu
    slow = (it.filter(F.hour("timestamp").between(16, 18) & F.dayofweek("timestamp").between(2, 6)
                      & F.col("avg_speed").isNotNull())
              .groupBy("road_id", "road_name", "district")
              .agg(F.round(F.avg("avg_speed"), 1).alias("toc_do_tb_kmh"), F.count("*").alias("so_gio"))
              .filter("so_gio >= 200").orderBy("toc_do_tb_kmh").limit(10))
    rep.h("5. sort: 10 tuyến chậm nhất giờ cao điểm chiều")
    rep.table(slow.toPandas(), "slowest_roads")

    # 6. Spark SQL: cùng truy vấn bước 4 viết bằng SQL → kết quả phải trùng
    it.createOrReplaceTempView("integrated_traffic")
    sql = spark.sql("""
        SELECT CASE WHEN dayofweek(timestamp) IN (1, 7) THEN 'cuối tuần' ELSE 'ngày thường' END AS loai_ngay,
               hour(timestamp) AS hour, ROUND(AVG(avg_speed), 1) AS toc_do_tb_kmh
        FROM integrated_traffic GROUP BY 1, 2 ORDER BY 1, 2""").toPandas()
    same = (sql["toc_do_tb_kmh"].values == hp["toc_do_tb_kmh"].values).all()
    rep.h("6. Spark SQL")
    rep.p(f"Truy vấn bước 4 viết bằng SQL cho kết quả **{'trùng khớp' if same else 'KHÁC'}** với DataFrame API "
          f"({len(sql)} dòng) — cả hai cùng đi qua bộ tối ưu Catalyst.")
    rep.data["sql_equal"] = bool(same)

    # 7. cache
    def build_slow():
        return sp.filter(F.col("speed_kmh") < 30).groupBy("link_id").count()
    t_nc = measure(build_slow)["best_s"]
    cached = sp.filter(F.col("speed_kmh") < 30).cache()
    cached.count()
    t_c = measure(lambda: cached.groupBy("link_id").count())["best_s"]
    cached.unpersist()
    rep.h("7. cache")
    rep.p(f"| Truy vấn: đếm bản ghi < 30 km/h theo tuyến | Thời gian (tốt nhất / 3 lần, DataFrame dựng mới mỗi lần) |\n|---|---|\n"
          f"| Không cache (mỗi lần đọc lại Parquet và lọc) | {t_nc:.2f} s |\n"
          f"| Phần đã lọc được cache trong bộ nhớ | {t_c:.2f} s |")
    rep.data["cache"] = {"no_cache_s": t_nc, "cache_s": t_c}

    rep.save()
    spark.stop()
    print("Xong: docs/bao-cao/11_spark_basic.md")


if __name__ == "__main__":
    main()
