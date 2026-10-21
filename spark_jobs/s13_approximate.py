"""
Bước 13 — Exact vs Approximate processing.

    python -m spark_jobs.s13_approximate

Dữ liệu: speeds_clean (9.048.108 bản ghi) gắn quận qua broadcast join.
  A. Trung bình tốc độ theo quận: exact vs sample 0,1% … 30%, mỗi tỉ lệ 5 seed
     → relative error, khoảng tin cậy 95% (định lý giới hạn trung tâm) có chứa giá trị đúng không, thời gian
  B. Thời gian: sample "tại chỗ" (vẫn phải quét toàn bộ) vs mẫu dựng sẵn (đã lưu/cached)
  C. Đếm phần tử khác nhau: countDistinct (chính xác) vs approx_count_distinct (HyperLogLog++)
  D. Trung vị: percentile (chính xác) vs percentile_approx (thuật toán Greenwald–Khanna)
"""
from __future__ import annotations

import math
import time

import pandas as pd
from pyspark.sql import functions as F

from spark_jobs.common import PATHS, Report, get_spark, measure

FRACTIONS = [0.001, 0.01, 0.05, 0.1, 0.3]
SEEDS = [1, 2, 3, 4, 5]


def base(spark):
    sp = spark.read.parquet(str(PATHS["speeds_clean"])).select("link_id", "timestamp", "speed_kmh")
    links = spark.read.parquet(str(PATHS["links_clean"])).select("link_id", "district")
    return sp.join(F.broadcast(links), "link_id")


def by_district(df):
    return df.groupBy("district").agg(F.count("*").alias("n"), F.avg("speed_kmh").alias("mean"),
                                      F.stddev("speed_kmh").alias("std"))


def main() -> None:
    spark = get_spark("s13_approximate")
    rep = Report("13_approximate", "Báo cáo bước 13 — Exact vs Approximate processing", spark)
    full = base(spark).cache()
    N = full.count()

    # A. Độ chính xác của trung bình theo quận
    exact = by_district(full).toPandas().set_index("district")
    rows = []
    for f in FRACTIONS:
        for seed in SEEDS:
            est = by_district(full.sample(fraction=f, seed=seed)).toPandas().set_index("district")
            for d in exact.index:
                e = est.loc[d]
                true = exact.loc[d, "mean"]
                half = 1.96 * e["std"] / math.sqrt(e["n"])
                rows.append({"fraction": f, "seed": seed, "district": d, "n_sample": int(e["n"]),
                             "rel_err_pct": 100 * abs(e["mean"] - true) / true,
                             "ci_covers": (e["mean"] - half) <= true <= (e["mean"] + half)})
    acc = pd.DataFrame(rows)
    summary = (acc.groupby("fraction")
               .agg(mau_tb=("n_sample", "mean"), sai_so_tb_pct=("rel_err_pct", "mean"),
                    sai_so_max_pct=("rel_err_pct", "max"), ci95_chua_gia_tri_dung_pct=("ci_covers", "mean"))
               .reset_index())
    summary["ci95_chua_gia_tri_dung_pct"] *= 100
    summary["mau_tb"] = summary["mau_tb"].round().astype(int)
    summary.insert(0, "ti_le_mau", summary["fraction"].map(lambda f: f"{100 * f:g}%"))
    rep.h("A. Trung bình tốc độ theo quận: sai số theo tỉ lệ mẫu")
    rep.p(f"Giá trị đúng (exact) tính trên toàn bộ {N:,} bản ghi:")
    rep.table(exact.reset_index()[["district", "n", "mean"]].rename(columns={"mean": "toc_do_tb_kmh"}), "exact")
    rep.p(f"Mỗi tỉ lệ chạy {len(SEEDS)} seed × 5 quận = {len(SEEDS) * 5} ước lượng:")
    rep.table(summary.drop(columns="fraction"), "accuracy")
    # Kiểm chứng sai số ~ 1/√n: nhân 10 lần cỡ mẫu → sai số giảm ~√10 ≈ 3,16 lần
    e1 = summary.set_index("fraction")["sai_so_tb_pct"]
    rep.p(f"Tỉ số sai số 0,1% / 1% = {e1[0.001] / e1[0.01]:.2f} và 1% / 10% = {e1[0.01] / e1[0.1]:.2f} "
          f"(lý thuyết √10 ≈ 3,16).")
    rep.data["err_ratio"] = [round(e1[0.001] / e1[0.01], 2), round(e1[0.01] / e1[0.1], 2)]
    worst = acc[acc.fraction == 0.001].groupby("district")["rel_err_pct"].mean().sort_values(ascending=False)
    rep.p("Sai số trung bình ở mẫu 0,1% theo từng quận (quận ít dữ liệu sai số lớn hơn): "
          + ", ".join(f"{d} {v:.2f}%" for d, v in worst.items()))

    # B. Thời gian
    m_exact = measure(lambda: by_district(base(spark)))
    m_otf = measure(lambda: by_district(base(spark).sample(fraction=0.01, seed=1)))
    sample_df = full.sample(fraction=0.01, seed=1).cache()
    sample_df.count()
    m_pre = measure(lambda: by_district(sample_df))
    m_full_cached = measure(lambda: by_district(full))
    tdf = pd.DataFrame([
        {"cach": "Exact: đọc Parquet + tính trên 100%", **m_exact},
        {"cach": "Sample 1% tại chỗ: đọc Parquet + lấy mẫu + tính", **m_otf},
        {"cach": "Exact trên dữ liệu đã cache (100%)", **m_full_cached},
        {"cach": "Mẫu 1% dựng sẵn (cached)", **m_pre},
    ])
    rep.h("B. Thời gian: lấy mẫu tại chỗ vs mẫu dựng sẵn")
    rep.table(tdf, "timing")

    # C. Đếm phần tử khác nhau: số cặp (tuyến, giờ) có dữ liệu
    key = F.concat_ws("|", "link_id", F.date_trunc("hour", "timestamp").cast("string"))
    t0 = time.perf_counter()
    exact_cd = full.select(F.countDistinct(key)).collect()[0][0]
    t_exact_cd = time.perf_counter() - t0
    crow = [{"phuong_phap": "countDistinct (chính xác)", "ket_qua": exact_cd, "sai_so_pct": 0.0,
             "thoi_gian_s": round(t_exact_cd, 3)}]
    for rsd in (0.05, 0.01):
        t0 = time.perf_counter()
        v = full.select(F.approx_count_distinct(key, rsd=rsd)).collect()[0][0]
        crow.append({"phuong_phap": f"approx_count_distinct (HyperLogLog++, rsd={rsd})", "ket_qua": v,
                     "sai_so_pct": round(100 * abs(v - exact_cd) / exact_cd, 3),
                     "thoi_gian_s": round(time.perf_counter() - t0, 3)})
    rep.h("C. Đếm số cặp (tuyến, giờ) khác nhau")
    rep.table(pd.DataFrame(crow), "count_distinct")

    # D. Trung vị tốc độ theo quận
    t0 = time.perf_counter()
    med_exact = full.groupBy("district").agg(F.expr("percentile(speed_kmh, 0.5)").alias("median")).toPandas()
    t_med = time.perf_counter() - t0
    drow = [{"phuong_phap": "percentile (chính xác)", "thoi_gian_s": round(t_med, 3), "sai_so_max_pct": 0.0}]
    med_exact = med_exact.set_index("district")["median"]
    for acc_param in (100, 10000):
        t0 = time.perf_counter()
        m = full.groupBy("district").agg(F.percentile_approx("speed_kmh", 0.5, acc_param).alias("median")).toPandas()
        dt = time.perf_counter() - t0
        err = (100 * (m.set_index("district")["median"] - med_exact).abs() / med_exact).max()
        drow.append({"phuong_phap": f"percentile_approx(accuracy={acc_param})", "thoi_gian_s": round(dt, 3),
                     "sai_so_max_pct": round(float(err), 3)})
    rep.h("D. Trung vị tốc độ theo quận")
    rep.p("Trung vị chính xác: " + ", ".join(f"{d} {v:.1f} km/h" for d, v in med_exact.items()))
    rep.table(pd.DataFrame(drow), "median")

    full.unpersist()
    rep.save()
    spark.stop()
    print("Xong: docs/bao-cao/13_approximate.md")


if __name__ == "__main__":
    main()
