"""
Bước 08 — Schema alignment: data/interim/*_clean → data/interim/aligned/

    python -m data_integration.alignment.run

Đầu ra (data/interim/aligned/):
    speeds_hourly/month=YYYY-MM/part-0.parquet   link_id, timestamp, avg_speed (km/h), n_readings
    volume_hourly.parquet                        segmentid, timestamp, vehicle_count, n_dirs, any_outlier
    weather_hourly.parquet                       weather_station_id, district, timestamp, temperature, ...
    roads_speeds.parquet                         link_id, main_road, direction, endpoints, district, tọa độ
    roads_volume.parquet                         segmentid, street, main_road, endpoints, district, tọa độ
Báo cáo: docs/bao-cao/08_alignment.md + .json
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime

import pandas as pd

from data_integration import config
from data_integration.alignment import aggregate
from data_integration.alignment.mapping import GAV_MAPPING
from data_integration.alignment.names import ROAD_ACRONYMS
from data_integration.alignment.schema_matching import run_experiment
from data_integration.cleaning.common import to_parquet_us

log = logging.getLogger("alignment")


def run() -> dict:
    src, out = config.INTERIM_DIR, config.INTERIM_DIR / "aligned"
    out.mkdir(parents=True, exist_ok=True)
    r: dict = {"generated": f"{datetime.now():%Y-%m-%d %H:%M}"}

    r["schema_matching"] = run_experiment()

    t0 = time.time()
    rows_in = rows_out = 0
    for part in sorted((src / "speeds_clean").glob("month=*")):
        m = pd.read_parquet(part)
        h = aggregate.speeds_hourly(m)
        d = out / "speeds_hourly" / part.name
        d.mkdir(parents=True, exist_ok=True)
        to_parquet_us(h, d / "part-0.parquet")
        rows_in += len(m)
        rows_out += len(h)
    r["speeds"] = {"readings": rows_in, "link_hours": rows_out, "seconds": round(time.time() - t0, 1)}
    log.info("speeds: %s bản ghi → %s (link, giờ)", f"{rows_in:,}", f"{rows_out:,}")

    v = pd.read_parquet(src / "volume_clean.parquet")
    vh, vstats = aggregate.volume_hourly(v)
    to_parquet_us(vh, out / "volume_hourly.parquet")
    r["volume"] = {"rows_15min": len(v), **vstats}
    log.info("volume: %s khung 15' → %s (đoạn, giờ) đầy đủ", f"{len(v):,}", f"{vstats['complete']:,}")

    w = aggregate.weather_hourly(pd.read_parquet(src / "weather_clean.parquet"))
    to_parquet_us(w, out / "weather_hourly.parquet")
    r["weather"] = {"rows": len(w)}

    links = pd.read_parquet(src / "links_clean.parquet")
    rs = aggregate.roads_from_links(links)
    to_parquet_us(rs, out / "roads_speeds.parquet")
    rv = aggregate.roads_from_volume(v)
    to_parquet_us(rv, out / "roads_volume.parquet")
    r["roads"] = {
        "speeds_links": len(rs), "speeds_main_roads": int(rs["main_road"].nunique()),
        "volume_segments": len(rv), "volume_streets": int(rv["main_road"].nunique()),
        "acronyms_expanded_speeds": int(links["link_name"].str.split().str[0].isin(ROAD_ACRONYMS).sum()),
        "names_changed_volume": int((rv["main_road"] != rv["street"]).sum()),
        "examples_speeds": rs[["link_name", "main_road", "direction", "endpoints"]].head(12).to_dict("records"),
        "examples_volume": rv.loc[rv["main_road"] != rv["street"], ["street", "main_road"]].head(12).to_dict("records"),
        "top_main_roads": rs["main_road"].value_counts().head(15).to_dict(),
    }
    write_report(r)
    return r


def _md(rows, cols):
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] +
                     ["| " + " | ".join(str(x.get(c, "")) for c in cols) + " |" for x in rows])


def write_report(r: dict) -> None:
    sm = r["schema_matching"]
    exp_rows = [{"matcher": k, "nguong": th, **v} for k in ("name", "name+synonym") for th, v in sm[k].items()]
    md = ["# Báo cáo Schema Alignment (bước 08)", "", f"Sinh tự động lúc {r['generated']}.", "",
          "## 1. Thử nghiệm schema matching tự động", "",
          _md(exp_rows, ["matcher", "nguong", "predicted", "correct", "ground_truth", "precision", "recall", "f1"]),
          "", "Kết quả chi tiết (ngưỡng 0,5) — chỉ dùng tên:", "",
          _md([{"cot_nguon": k, "cot_dich": v[0], "diem": v[1]} for k, v in sm["detail_name_0.5"].items()],
              ["cot_nguon", "cot_dich", "diem"]),
          "", "## 2. Ánh xạ GAV", "", _md(GAV_MAPPING, ["target", "speeds", "volume", "weather", "note"]),
          "", "## 3. Quy đổi về đường × giờ", "",
          "| Nguồn | Vào | Ra |", "|---|---|---|",
          f"| Tốc độ | {r['speeds']['readings']:,} bản ghi (~5 phút) | {r['speeds']['link_hours']:,} (link, giờ) |",
          f"| Lưu lượng | {r['volume']['rows_15min']:,} khung 15' | {r['volume']['complete']:,} (đoạn, giờ) đầy đủ; "
          f"loại {r['volume']['dropped_incomplete']:,} giờ thiếu khung/hướng |",
          f"| Thời tiết | {r['weather']['rows']:,} | {r['weather']['rows']:,} (trạm, giờ) |",
          "", "## 4. Chuẩn hóa tên đường", "",
          f"- Nguồn tốc độ: {r['roads']['speeds_links']} tuyến → {r['roads']['speeds_main_roads']} đường chính sau chuẩn hóa; "
          f"{r['roads']['acronyms_expanded_speeds']} tuyến có tên đường viết tắt được mở rộng",
          f"- Nguồn lưu lượng: {r['roads']['volume_segments']} đoạn → {r['roads']['volume_streets']} tên phố; "
          f"{r['roads']['names_changed_volume']} đoạn có tên bị thay đổi khi chuẩn hóa", "",
          _md(r["roads"]["examples_speeds"], ["link_name", "main_road", "direction", "endpoints"]), "",
          _md(r["roads"]["examples_volume"], ["street", "main_road"]), "",
          "Đường chính phổ biến (nguồn tốc độ): " + ", ".join(f"{k} ({v})" for k, v in r["roads"]["top_main_roads"].items())]
    (config.REPORT_DIR / "08_alignment.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (config.REPORT_DIR / "08_alignment.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str),
                                                         encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    log.info("Xong. Báo cáo: docs/bao-cao/08_alignment.md")
