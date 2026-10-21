"""
Bước 16 — Tác động của thời tiết lên giao thông.

    python -m spark_jobs.s16_weather_impact

Vấn đề: so sánh thô "tốc độ lúc mưa" với "tốc độ lúc nắng" bị NHIỄU, vì mưa/tuyết không rơi đều
theo giờ, ngày, đường (vd tuyết hay rơi ban đêm/cuối tuần lúc đường vốn vắng).

Cách làm — so sánh có kiểm soát (controlled comparison):
  1. Baseline = tốc độ trung bình của CÙNG đường, CÙNG giờ, CÙNG loại ngày trong các giờ KHÔ (không mưa, không tuyết).
  2. Chỉ số tốc độ tương đối  idx = avg_speed / baseline   (idx = 0,9 nghĩa là chậm hơn bình thường 10%).
  3. Nhóm idx theo điều kiện thời tiết / lượng mưa / lượng tuyết / nhiệt độ → % thay đổi so với bình thường.
  Như vậy mỗi bản ghi mưa được so với chính nó lúc khô → loại bỏ ảnh hưởng của giờ, ngày, đường.
Bỏ các ngày mất dữ liệu (bước 07) để tránh ngày chỉ có vài giờ đêm làm lệch kết quả.

Đầu ra: data/processed/analytics/weather_impact.parquet (cho dashboard)
"""
from __future__ import annotations

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from spark_jobs.common import PATHS, Report, get_spark, save_analytics

KEYS = ["road_id", "hour", "day_type"]
MIN_BASELINE = 10          # baseline phải có ≥ 10 giờ khô, nếu không thì bỏ ô (đường, giờ, loại ngày) đó
KEYS_M = KEYS + ["month"]  # kiểm soát thêm MÙA: so với cùng tháng (tháng 1 vốn vắng xe hơn tháng 6)
MIN_BASELINE_VOL = 5       # lưu lượng: đếm theo đợt ngắn
MIN_BASELINE_M = 5         # mỗi tháng chỉ có ~8 ngày cuối tuần → ngưỡng thấp hơn
PEAK_HOURS = (7, 8, 9, 16, 17, 18)
# Ngày lễ liên bang Mỹ 2024 + các ngày nghỉ phổ biến: giao thông giống cuối tuần → xếp vào "weekend"
HOLIDAYS_2024 = ("2024-01-01", "2024-01-15", "2024-02-19", "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02",
                 "2024-10-14", "2024-11-11", "2024-11-28", "2024-11-29", "2024-12-24", "2024-12-25", "2024-12-31")


def load(spark) -> DataFrame:
    cov = (spark.read.parquet(str(PATHS["coverage"]))
                .select(F.to_date("date").alias("date"), F.col("is_outage").cast("boolean").alias("is_outage")))
    df = (spark.read.parquet(str(PATHS["integrated"]))
               .withColumn("hour", F.hour("timestamp"))
               .withColumn("date", F.to_date("timestamp"))
               .withColumn("day_type", F.when(F.dayofweek("timestamp").isin(1, 7)
                                              | F.col("date").cast("string").isin(*HOLIDAYS_2024), "weekend")
                                        .otherwise("weekday"))
               .withColumn("dry", (F.col("rainfall") == 0) & (F.col("snowfall") == 0))
               .withColumn("period", F.when(F.col("day_type").eqNullSafe("weekday") & F.col("hour").isin(*PEAK_HOURS),
                                            "Cao điểm ngày thường").otherwise("Ngoài cao điểm")))
    return df.join(F.broadcast(cov), "date", "left").filter(~F.coalesce(F.col("is_outage"), F.lit(False)))


def baseline(df: DataFrame, metric: str, keys: list[str], min_n: int, name: str) -> DataFrame:
    """TB của metric trong các giờ KHÔ, theo `keys`; bỏ ô có < min_n giờ khô."""
    return (df.filter(F.col("dry") & F.col(metric).isNotNull()).groupBy(*keys)
              .agg(F.avg(metric).alias(name), F.count(metric).alias(name + "_n"))
              .filter((F.col(name + "_n") >= min_n) & (F.col(name) > 0)).drop(name + "_n"))


def with_index(df: DataFrame, metric: str, out: str, min_n: int = MIN_BASELINE) -> DataFrame:
    """Chỉ số tương đối = metric / baseline.
    `out`   : baseline theo đường × giờ × loại ngày (cả năm)            — bắt buộc có
    `out_m` : baseline theo đường × giờ × loại ngày × THÁNG (kiểm soát mùa) — null nếu ô tháng đó thiếu dữ liệu"""
    b1 = baseline(df, metric, KEYS, min_n, "baseline")
    b2 = baseline(df, metric, KEYS_M, MIN_BASELINE_M, "baseline_m")
    return (df.filter(F.col(metric).isNotNull()).join(b1, KEYS).join(b2, KEYS_M, "left")
              .withColumn(out, F.col(metric) / F.col("baseline"))
              .withColumn(out + "_m", F.col(metric) / F.col("baseline_m")))


def bins(df: DataFrame) -> DataFrame:
    r, s, t = F.col("rainfall"), F.col("snowfall"), F.col("temperature")
    return (df.withColumn("rain_bin", F.when(r == 0, "0. Không mưa").when(r <= 0.5, "1. 0–0,5 mm/h (rất nhẹ)")
                          .when(r <= 2, "2. 0,5–2 mm/h (nhẹ)").when(r <= 5, "3. 2–5 mm/h (vừa)")
                          .otherwise("4. > 5 mm/h (to)"))
              .withColumn("snow_bin", F.when(s == 0, "0. Không tuyết").when(s <= 0.5, "1. 0–0,5 cm/h")
                          .when(s <= 1, "2. 0,5–1 cm/h").otherwise("3. > 1 cm/h"))
              .withColumn("temp_bin", F.when(t < 0, "1. < 0 °C").when(t < 10, "2. 0–10 °C").when(t < 20, "3. 10–20 °C")
                          .when(t < 30, "4. 20–30 °C").otherwise("5. ≥ 30 °C")))


def effect_table(df: DataFrame, by: str, metric: str, idx: str) -> pd.DataFrame:
    """So sánh thô và có kiểm soát cho từng nhóm `by`."""
    g = (df.groupBy(by)
           .agg(F.count("*").alias("n"), F.countDistinct("date").alias("so_ngay"),
                F.avg(metric).alias("tb_tho"), F.avg(idx).alias("idx_tb"), F.stddev(idx).alias("idx_std"),
                F.avg(idx + "_m").alias("idx_m_tb"))
           .toPandas().sort_values(by).reset_index(drop=True))
    return g


def finish(g: pd.DataFrame, by: str, ref: str) -> pd.DataFrame:
    """% thay đổi: thô (so với nhóm tham chiếu `ref`) và có kiểm soát (so với baseline của chính nó)."""
    ref_raw = g.loc[g[by] == ref, "tb_tho"].iloc[0]
    out = pd.DataFrame({
        by: g[by], "n": g["n"].astype(int), "so_ngay": g["so_ngay"].astype(int),
        "tb_tho": g["tb_tho"].round(2),
        "thay_doi_tho_pct": (100 * (g["tb_tho"] / ref_raw - 1)).round(2),
        "thay_doi_kiem_soat_pct": (100 * (g["idx_tb"] - 1)).round(2),
        "kiem_soat_them_thang_pct": (100 * (g["idx_m_tb"] - 1)).round(2),
        # KTC 95% theo bản ghi — HẸP hơn thực tế vì các giờ trong cùng một trận mưa không độc lập
        "ktc95_pct": (100 * 1.96 * g["idx_std"] / g["n"] ** 0.5).round(2),
    })
    return out


def main() -> None:
    spark = get_spark("s16_weather_impact")
    rep = Report("16_weather_impact", "Báo cáo bước 16 — Tác động của thời tiết lên giao thông", spark)
    df = bins(load(spark)).cache()
    sp = with_index(df, "avg_speed", "speed_idx").cache()
    n_sp = sp.count()
    rep.p(f"Bản ghi tốc độ dùng để phân tích: {n_sp:,} (đã bỏ ngày mất dữ liệu và các ô đường × giờ × loại ngày "
          f"có < {MIN_BASELINE} giờ khô).")
    rep.data["n_speed_records"] = n_sp
    saved = []

    # A. Theo điều kiện thời tiết: thô vs có kiểm soát
    a = finish(effect_table(sp, "weather_condition", "avg_speed", "speed_idx"), "weather_condition", "Clear")
    rep.h("A. Tốc độ theo điều kiện thời tiết: so sánh thô và có kiểm soát")
    rep.p("`thay_doi_tho_pct`: so với trung bình nhóm Clear (cách so sánh ở bước 15). "
          "`thay_doi_kiem_soat_pct`: so với chính đường đó, cùng giờ, cùng loại ngày, lúc khô ráo (baseline cả năm). "
          "`kiem_soat_them_thang_pct`: như trên nhưng baseline lấy trong CÙNG THÁNG (kiểm soát thêm mùa). "
          "Ngày lễ được xếp vào loại ngày cuối tuần.")
    rep.table(a, "by_condition")
    saved.append(a.rename(columns={"weather_condition": "nhom"}).assign(chieu="weather_condition"))

    # B. Theo lượng mưa (liều – đáp ứng)
    rain = sp.filter(F.col("snowfall") == 0)
    b = finish(effect_table(rain, "rain_bin", "avg_speed", "speed_idx"), "rain_bin", "0. Không mưa")
    rep.h("B. Tốc độ theo lượng mưa (giờ không có tuyết)")
    rep.table(b, "by_rain")
    saved.append(b.rename(columns={"rain_bin": "nhom"}).assign(chieu="rainfall"))

    # C. Mưa trong giờ cao điểm và ngoài cao điểm
    c = (rain.withColumn("is_rain", F.when(F.col("rainfall") > 0.5, "Mưa > 0,5 mm/h").otherwise("Không mưa / mưa rất nhẹ"))
             .groupBy("period", "is_rain").agg(F.count("*").alias("n"), F.avg("speed_idx").alias("idx"),
                                               F.avg("speed_idx_m").alias("idx_m"))
             .toPandas().sort_values(["period", "is_rain"]))
    c["thay_doi_kiem_soat_pct"] = (100 * (c["idx"] - 1)).round(2)
    c["kiem_soat_them_thang_pct"] = (100 * (c["idx_m"] - 1)).round(2)
    rep.h("C. Mưa trong giờ cao điểm và ngoài cao điểm")
    rep.table(c.drop(columns=["idx", "idx_m"]), "rain_by_period")

    # D. Tuyết, và vì sao so sánh thô bị nhiễu
    d = finish(effect_table(sp, "snow_bin", "avg_speed", "speed_idx"), "snow_bin", "0. Không tuyết")
    rep.h("D. Tốc độ theo lượng tuyết")
    rep.table(d, "by_snow")
    saved.append(d.rename(columns={"snow_bin": "nhom"}).assign(chieu="snowfall"))
    mix = (sp.withColumn("grp", F.when(F.col("snowfall") > 0, "Giờ có tuyết").otherwise("Mọi giờ khác"))
             .groupBy("grp")
             .agg(F.count("*").alias("n"),
                  F.round(100 * F.avg((F.col("hour") < 6).cast("int")), 1).alias("pct_0h_6h"),
                  F.round(100 * F.avg((F.col("day_type") == "weekend").cast("int")), 1).alias("pct_cuoi_tuan"),
                  F.round(100 * F.avg(F.col("period").startswith("Cao").cast("int")), 1).alias("pct_cao_diem"),
                  F.round(100 * F.avg((F.col("district") == "Staten Island").cast("int")), 1).alias("pct_staten_island"),
                  F.round(100 * F.avg((F.col("district") == "Manhattan").cast("int")), 1).alias("pct_manhattan"),
                  F.round(F.avg("baseline"), 2).alias("baseline_tb"))
             .toPandas())
    rep.p("**Các giờ có tuyết rơi vào lúc nào, ở đâu?** (so với mọi giờ khác). `baseline_tb` là tốc độ "
          "bình thường của đúng các ô (đường × giờ × loại ngày) đó lúc khô ráo:")
    rep.table(mix, "snow_mix")
    snow_days = (sp.groupBy("date").agg(F.round(F.sum("snowfall") / F.countDistinct("road_id"), 1).alias("tuyet_cm_ngay"),
                                        F.round(F.max("snowfall"), 2).alias("tuyet_max_cm_h"),
                                        F.first("day_type").alias("day_type"),
                                        F.round(100 * (F.avg("speed_idx") - 1), 2).alias("toc_do_ca_ngay_pct"),
                                        F.round(100 * (F.avg("speed_idx_m") - 1), 2).alias("kiem_soat_them_thang_pct"))
                   .filter(F.col("tuyet_cm_ngay") >= 1).orderBy(F.desc("tuyet_cm_ngay")).toPandas())
    snow_days["date"] = snow_days["date"].astype(str)
    rep.p("**Các ngày có tuyết ≥ 1 cm** (tổng lượng tuyết cả ngày, trung bình theo đường):")
    rep.table(snow_days, "snow_days")

    # E. Nhiệt độ
    e = finish(effect_table(sp, "temp_bin", "avg_speed", "speed_idx"), "temp_bin", "3. 10–20 °C")
    rep.h("E. Tốc độ theo nhiệt độ")
    rep.table(e, "by_temperature")
    saved.append(e.rename(columns={"temp_bin": "nhom"}).assign(chieu="temperature"))

    # F. Lưu lượng xe theo thời tiết (dữ liệu đếm theo đợt → ít, chỉ tham khảo)
    # Mỗi đợt đếm chỉ 1–2 tuần → mỗi ô (điểm đếm, giờ, loại ngày) chỉ có ~5–10 giờ: dùng ngưỡng 5
    vol = with_index(df, "vehicle_count", "vol_idx", min_n=MIN_BASELINE_VOL).cache()
    f = finish(effect_table(vol.filter(F.col("snowfall") == 0), "rain_bin", "vehicle_count", "vol_idx"),
               "rain_bin", "0. Không mưa")
    rep.h("F. Lưu lượng xe theo lượng mưa")
    rep.p(f"Chỉ {vol.count():,} giờ đếm có baseline đủ {MIN_BASELINE_VOL} giờ khô. Các điểm đếm chỉ hoạt động vài ngày, "
          f"nên số trận mưa quan sát được rất ít, xem cột `so_ngay`.")
    rep.table(f, "volume_by_rain")
    saved.append(f.rename(columns={"rain_bin": "nhom"}).assign(chieu="rainfall_volume"))

    # G. Tương quan
    city = (sp.groupBy("timestamp").agg(F.avg("speed_idx").alias("idx"), F.avg("avg_speed").alias("spd"),
                                        F.avg("rainfall").alias("rain"), F.avg("snowfall").alias("snow"),
                                        F.avg("temperature").alias("temp"), F.count("*").alias("k"))
              .filter(F.col("k") >= 50))
    corr = pd.DataFrame([
        {"cap_bien": "rainfall – avg_speed (từng bản ghi, thô)", "pearson": sp.stat.corr("rainfall", "avg_speed")},
        {"cap_bien": "rainfall – speed_idx (từng bản ghi, có kiểm soát)", "pearson": sp.stat.corr("rainfall", "speed_idx")},
        {"cap_bien": "rainfall – speed_idx (TB toàn thành phố mỗi giờ)", "pearson": city.stat.corr("rain", "idx")},
        {"cap_bien": "snowfall – speed_idx (TB toàn thành phố mỗi giờ)", "pearson": city.stat.corr("snow", "idx")},
        {"cap_bien": "temperature – speed_idx (TB toàn thành phố mỗi giờ)", "pearson": city.stat.corr("temp", "idx")},
    ])
    corr["pearson"] = corr["pearson"].round(3)
    rep.h("G. Hệ số tương quan Pearson")
    rep.table(corr, "correlation")
    rep.data["city_hours"] = city.count()

    # H. Những trận mưa lớn nhất
    storms = (sp.groupBy("date").agg(F.round(F.avg("rainfall") * 24, 1).alias("mua_mm_ngay"),
                                     F.round(F.max("rainfall"), 1).alias("mua_max_mm_h"),
                                     F.first("day_type").alias("day_type"),
                                     F.round(100 * (F.avg("speed_idx") - 1), 2).alias("thay_doi_toc_do_ca_ngay_pct"),
                                     F.round(100 * (F.avg("speed_idx_m") - 1), 2).alias("kiem_soat_them_thang_pct"),
                                     F.count("*").alias("n"))
                .orderBy(F.desc("mua_mm_ngay")).limit(8).toPandas())
    storms["date"] = storms["date"].astype(str)
    rep.h("H. 8 ngày mưa nhiều nhất")
    rep.table(storms, "storm_days")

    out = pd.concat(saved, ignore_index=True)[["chieu", "nhom", "n", "so_ngay", "tb_tho", "thay_doi_tho_pct",
                                              "thay_doi_kiem_soat_pct", "kiem_soat_them_thang_pct", "ktc95_pct"]]
    save_analytics(spark.createDataFrame(out), "weather_impact")
    for x in (vol, sp, df):
        x.unpersist()
    rep.save()
    spark.stop()
    print("Xong: docs/bao-cao/16_weather_impact.md")


if __name__ == "__main__":
    main()
