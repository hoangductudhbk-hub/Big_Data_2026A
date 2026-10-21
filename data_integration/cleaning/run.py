"""
Bước 07 — Làm sạch dữ liệu: data/raw → data/interim (Parquet).

    python -m data_integration.cleaning.run

Đầu ra:
    data/interim/weather_clean.parquet
    data/interim/volume_clean.parquet
    data/interim/links_clean.parquet
    data/interim/speeds_clean/month=YYYY-MM/part-0.parquet
    data/interim/speeds_coverage_daily.parquet
    docs/bao-cao/07_cleaning.md  +  07_cleaning.json
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime

import pandas as pd

from data_integration import config
from data_integration.cleaning.common import CleaningLog, to_parquet_us
from data_integration.cleaning.speeds import clean_links, clean_speeds_month, coverage_flags
from data_integration.cleaning.volume import clean_volume
from data_integration.cleaning.weather import clean_weather

log = logging.getLogger("cleaning")


def _read_raw(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _steps_md(lg: dict) -> str:
    lines = [f"Số dòng vào: **{lg['rows_in']:,}** → số dòng ra: **{lg['rows_out']:,}**", "",
             "| # | Quy tắc | Số dòng bị ảnh hưởng | % so với đầu vào | Xử lý | Ghi chú |", "|---|---|---|---|---|---|"]
    for i, s in enumerate(lg["steps"], 1):
        pct = 100 * s["affected"] / lg["rows_in"] if lg["rows_in"] else 0
        lines.append(f"| {i} | {s['rule']} | {s['affected']:,} | {pct:.2f}% | {s['action']} | {s['note']} |")
    return "\n".join(lines)


def run() -> dict:
    raw, interim = config.RAW_DIR, config.INTERIM_DIR
    interim.mkdir(parents=True, exist_ok=True)
    result: dict = {"generated": f"{datetime.now():%Y-%m-%d %H:%M}"}

    # 1. Thời tiết
    t0 = time.time()
    w_raw = _read_raw(raw / "weather" / f"open_meteo_{config.STUDY_START}_{config.STUDY_END}.csv")
    w, wlog = clean_weather(w_raw)
    to_parquet_us(w, interim / "weather_clean.parquet")
    result["weather"] = {**wlog.as_dict(), "seconds": round(time.time() - t0, 1)}
    log.info("weather: %s → %s dòng", f"{wlog.rows_in:,}", f"{wlog.rows_out:,}")

    # 2. Lưu lượng
    t0 = time.time()
    v_raw = pd.concat([_read_raw(f) for f in sorted((raw / "volume").glob("volume_*.csv"))], ignore_index=True)
    v, vlog = clean_volume(v_raw)
    to_parquet_us(v, interim / "volume_clean.parquet")
    result["volume"] = {**vlog.as_dict(), "seconds": round(time.time() - t0, 1),
                        "vol_stats": v["vol"].describe().round(1).to_dict()}
    log.info("volume: %s → %s dòng", f"{vlog.rows_in:,}", f"{vlog.rows_out:,}")

    # 3. Tốc độ (từng tháng để tiết kiệm bộ nhớ)
    t0 = time.time()
    out_dir = interim / "speeds_clean"          # ghi đè từng file tháng (không xóa thư mục cũ)
    slog = CleaningLog("speeds")
    seen, hours, monthly = [], [], []
    for f in sorted((raw / "speeds").glob("speeds_*.csv")):
        month = f.stem.replace("speeds_", "")
        raw_m = _read_raw(f)
        before_in, before_out = slog.rows_in, slog.rows_out
        clean_m = clean_speeds_month(raw_m, slog)
        part = out_dir / f"month={month}"
        part.mkdir(parents=True, exist_ok=True)
        to_parquet_us(clean_m, part / "part-0.parquet")
        seen.append(raw_m[["link_id", "link_name", "borough"]].drop_duplicates("link_id"))
        hours.append(clean_m.assign(timestamp=clean_m["timestamp"].dt.floor("h"))[["link_id", "timestamp"]]
                     .drop_duplicates())
        n_in, n_out = slog.rows_in - before_in, slog.rows_out - before_out
        monthly.append({"thang": month, "vao": n_in, "ra": n_out, "giu_lai_%": round(100 * n_out / n_in, 1),
                        "toc_do_tb_kmh": round(float(clean_m["speed_kmh"].mean()), 1)})
        log.info("speeds %s: %s → %s", month, f"{n_in:,}", f"{n_out:,}")
    result["speeds"] = {**slog.as_dict(), "seconds": round(time.time() - t0, 1), "monthly": monthly}

    # 4. Danh mục tuyến
    t0 = time.time()
    links_raw = _read_raw(raw / "speeds" / "links.csv")
    seen_df = pd.concat(seen).drop_duplicates("link_id")
    links, llog = clean_links(links_raw, seen_df)
    to_parquet_us(links, interim / "links_clean.parquet")
    result["links"] = {**llog.as_dict(), "seconds": round(time.time() - t0, 1)}

    # 5. Độ phủ theo ngày và các đợt mất dữ liệu
    cov = coverage_flags(pd.concat(hours, ignore_index=True))
    to_parquet_us(cov, interim / "speeds_coverage_daily.parquet")
    out_days = cov[cov["is_outage"]]
    result["coverage"] = {"days": len(cov), "outage_days": int(len(out_days)),
                          "outage_dates": [d.strftime("%Y-%m-%d") for d in out_days["date"]]}

    write_report(result, links)
    return result


def write_report(r: dict, links: pd.DataFrame) -> None:
    sp = r["speeds"]
    md = [
        "# Báo cáo Data Cleaning (bước 07)", "",
        f"Sinh tự động bởi `python -m data_integration.cleaning.run` lúc {r['generated']}.", "",
        "## Tổng quan", "",
        "| Nguồn | Vào | Ra | Giữ lại | Thời gian |", "|---|---|---|---|---|",
    ]
    for k in ("weather", "volume", "speeds", "links"):
        x = r[k]
        md.append(f"| {k} | {x['rows_in']:,} | {x['rows_out']:,} | "
                  f"{100 * x['rows_out'] / x['rows_in']:.1f}% | {x.get('seconds', '')}s |")
    md += ["", "## Thời tiết", "", _steps_md(r["weather"]),
           "", "## Lưu lượng", "", _steps_md(r["volume"]),
           "", "Thống kê `vol` sau làm sạch (xe/15 phút): " +
           ", ".join(f"{k}={v:,}" for k, v in r["volume"]["vol_stats"].items()),
           "", "## Tốc độ", "", _steps_md(sp), "", "### Theo tháng", "",
           "| Tháng | Vào | Ra | Giữ lại | Tốc độ TB (km/h) |", "|---|---|---|---|---|"]
    md += [f"| {m['thang']} | {m['vao']:,} | {m['ra']:,} | {m['giu_lai_%']}% | {m['toc_do_tb_kmh']} |" for m in sp["monthly"]]
    cov = r["coverage"]
    md += ["", "### Ngày mất dữ liệu (độ phủ giờ < 50%)", "",
           f"{cov['outage_days']} / {cov['days']} ngày: " + ", ".join(cov["outage_dates"]),
           "", "Các ngày này **không bị xóa hay nội suy**. Chúng được đánh dấu trong "
           "`data/interim/speeds_coverage_daily.parquet` để các bước phân tích loại trừ khi cần.",
           "", "## Danh mục tuyến", "", _steps_md(r["links"]), "",
           "| Chỉ số | Giá trị |", "|---|---|",
           f"| Số tuyến | {len(links)} |",
           f"| Có tọa độ | {int(links['latitude'].notna().sum())} |",
           f"| Số điểm tọa độ trung bình mỗi tuyến | {links['n_points'].mean():.1f} |",
           f"| Phân bố theo quận | {links['district'].value_counts().to_dict()} |"]
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (config.REPORT_DIR / "07_cleaning.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (config.REPORT_DIR / "07_cleaning.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    log.info("Xong. Báo cáo: docs/bao-cao/07_cleaning.md")
