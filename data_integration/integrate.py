"""
Bước 10 — Tạo bảng tích hợp integrated_traffic (đầu ra của Phase 1, đầu vào của Phase 2).

    python -m data_integration.integrate

  T_speed  (link, giờ)  ┐
                        ├─ FULL OUTER JOIN theo (road_id, timestamp) ─┐
  T_volume (đoạn, giờ)  ┘   (road_id từ bảng roads của bước 09)       ├─ LEFT JOIN thời tiết theo (district, timestamp)
                                                                      ┘
Đầu ra:
    data/processed/integrated_traffic/year=YYYY/month=M/*.parquet   (đúng data contract)
    data/processed/coverage_daily.parquet                           (ngày mất dữ liệu tốc độ, cho Phase 2)
    docs/bao-cao/10_integrated.md + .json
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from common.contract import COLUMN_NAMES, CONTRACT_VERSION, arrow_schema, validate_pandas
from data_integration import config

log = logging.getLogger("integrate")


def build(speeds_h: pd.DataFrame, volume_h: pd.DataFrame, weather_h: pd.DataFrame,
          roads: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    st: dict = {}
    # 1. Gán road_id
    sp = speeds_h.assign(road_id="L" + speeds_h["link_id"].astype(str))[["road_id", "timestamp", "avg_speed"]]
    seg2road = roads.dropna(subset=["segmentid"]).set_index("segmentid")["road_id"].to_dict()
    vo = volume_h.assign(road_id=volume_h["segmentid"].astype(str).map(seg2road))
    st["volume_rows_without_road"] = int(vo["road_id"].isna().sum())
    vo = vo.dropna(subset=["road_id"])[["road_id", "timestamp", "vehicle_count"]]

    # 2. Ghép 2 nguồn giao thông: FULL OUTER JOIN (giữ cả dòng chỉ có 1 nguồn)
    t = sp.merge(vo, on=["road_id", "timestamp"], how="outer", indicator=True)
    t["source"] = t["_merge"].map({"left_only": "speeds", "right_only": "volume", "both": "speeds+volume"})
    t = t.drop(columns="_merge")
    st["rows_by_source"] = t["source"].value_counts().to_dict()

    # 3. Thuộc tính đường (tên, quận, tọa độ) từ bảng đường thống nhất
    attrs = roads[["road_id", "road_name", "district", "latitude", "longitude"]]
    t = t.merge(attrs, on="road_id", how="left")
    no_coord = t["latitude"].isna() | t["longitude"].isna() | t["district"].isna()
    st["rows_dropped_no_coordinates"] = int(no_coord.sum())
    t = t[~no_coord]

    # 4. Ghép thời tiết theo (quận, giờ) — LEFT JOIN: dòng giao thông vẫn giữ nếu thiếu thời tiết
    w = weather_h[["district", "timestamp", "temperature", "rainfall", "snowfall",
                   "weather_condition", "weather_station_id"]]
    t = t.merge(w, on=["district", "timestamp"], how="left")
    # Giờ KHÔNG TỒN TẠI do chuyển sang giờ mùa hè (02:00 ngày 10/03): máy đếm vẫn ghi theo giờ chuẩn,
    # 02:xx giờ chuẩn = 03:xx giờ mùa hè → lấy thời tiết của giờ kế tiếp.
    miss = t["temperature"].isna()
    st["rows_weather_from_next_hour"] = int(miss.sum())
    if miss.any():
        fb = t.loc[miss, ["district", "timestamp"]].assign(timestamp=lambda x: x["timestamp"] + pd.Timedelta(hours=1))
        fb = fb.reset_index().merge(w, on=["district", "timestamp"], how="left").set_index("index")
        for c in w.columns.drop(["district", "timestamp"]):
            t.loc[miss, c] = fb[c]
    st["rows_without_weather"] = int(t["temperature"].isna().sum())

    t["vehicle_count"] = t["vehicle_count"].astype("Int64")
    for c in ("road_id", "road_name", "district", "weather_condition", "weather_station_id", "source"):
        t[c] = t[c].astype("string")
    t["timestamp"] = pd.to_datetime(t["timestamp"]).astype("datetime64[us]")
    t = t[list(COLUMN_NAMES)].sort_values(["road_id", "timestamp"]).reset_index(drop=True)
    st["rows"] = len(t)
    return t, st


def write_partitioned(df: pd.DataFrame, out_dir) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, schema=arrow_schema(), preserve_index=False)
    table = table.append_column("year", pa.array(df["timestamp"].dt.year.astype("int32")))
    table = table.append_column("month", pa.array(df["timestamp"].dt.month.astype("int32")))
    # existing_data_behavior: ghi đè file cùng tên trong partition, không cần xóa thư mục (ổ D: không cho xóa)
    pq.write_to_dataset(table, root_path=str(out_dir), partition_cols=["year", "month"],
                        basename_template="part-{i}.parquet", existing_data_behavior="overwrite_or_ignore")


def summarize(df: pd.DataFrame, st: dict, errors: list[str]) -> dict:
    by_month = df.groupby(df["timestamp"].dt.strftime("%Y-%m")).agg(
        dong=("road_id", "size"), duong=("road_id", "nunique"),
        toc_do_tb=("avg_speed", "mean"), luu_luong_tb=("vehicle_count", "mean"),
        nhiet_do_tb=("temperature", "mean")).round(1).reset_index(names="thang")
    nulls = {c: int(df[c].isna().sum()) for c in df.columns}
    return {
        "generated": f"{datetime.now():%Y-%m-%d %H:%M}", "contract_version": CONTRACT_VERSION,
        **st, "contract_errors": errors,
        "roads": int(df["road_id"].nunique()), "time_min": str(df["timestamp"].min()),
        "time_max": str(df["timestamp"].max()),
        "by_district": df["district"].value_counts().to_dict(),
        "by_weather": df["weather_condition"].fillna("(thiếu)").value_counts().to_dict(),
        "nulls": nulls, "by_month": by_month.to_dict("records"),
    }


def write_report(r: dict) -> None:
    def tbl(rows):
        cols = list(rows[0])
        return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] +
                         ["| " + " | ".join(str(x[c]) for c in cols) + " |" for x in rows])
    md = ["# Báo cáo bảng tích hợp integrated_traffic (bước 10)", "",
          f"Sinh tự động lúc {r['generated']} · data contract v{r['contract_version']}", "",
          "## Tổng quan", "",
          f"- Số dòng: **{r['rows']:,}** · số đường: {r['roads']} · thời gian: {r['time_min']} → {r['time_max']}",
          f"- Theo nguồn: {r['rows_by_source']}",
          f"- Dòng bị loại vì đường không có tọa độ: {r['rows_dropped_no_coordinates']}",
          f"- Dòng lưu lượng không gán được road_id: {r['volume_rows_without_road']}",
          f"- Dòng lấy thời tiết của giờ kế tiếp (giờ không tồn tại 02:00 ngày 10/03): {r['rows_weather_from_next_hour']}",
          f"- Dòng không ghép được thời tiết: {r['rows_without_weather']}",
          f"- Kiểm tra data contract: {'ĐẠT (0 lỗi)' if not r['contract_errors'] else r['contract_errors']}", "",
          "## Theo quận", "", tbl([{"quan": k, "dong": v} for k, v in r["by_district"].items()]), "",
          "## Theo thời tiết", "", tbl([{"thoi_tiet": k, "dong": v} for k, v in r["by_weather"].items()]), "",
          "## Theo tháng", "", tbl(r["by_month"]), "",
          "## Số giá trị null theo cột", "", tbl([{"cot": k, "null": v} for k, v in r["nulls"].items()])]
    (config.REPORT_DIR / "10_integrated.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (config.REPORT_DIR / "10_integrated.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str),
                                                          encoding="utf-8")


def run() -> dict:
    al = config.INTERIM_DIR / "aligned"
    df, st = build(pd.read_parquet(al / "speeds_hourly"), pd.read_parquet(al / "volume_hourly.parquet"),
                   pd.read_parquet(al / "weather_hourly.parquet"),
                   pd.read_parquet(config.PROCESSED_DIR / "roads.parquet"))
    errors = validate_pandas(df)
    if errors:
        raise SystemExit("integrated_traffic KHÔNG đạt contract:\n- " + "\n- ".join(errors))
    write_partitioned(df, config.PROCESSED_DIR / "integrated_traffic")
    shutil.copyfile(config.INTERIM_DIR / "speeds_coverage_daily.parquet", config.PROCESSED_DIR / "coverage_daily.parquet")
    r = summarize(df, st, errors)
    write_report(r)
    log.info("integrated_traffic: %s dòng, %s đường, nguồn %s", f"{r['rows']:,}", r["roads"], r["rows_by_source"])
    return r


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
