"""
Bước 06 — Data profiling cho 3 nguồn raw.

    python -m data_integration.profiling.run                  # cả 3 nguồn
    python -m data_integration.profiling.run --source volume  # chỉ 1 nguồn

Đầu ra:
    docs/bao-cao/06_profiling.md     Báo cáo đọc được
    docs/bao-cao/06_profiling.json   Số liệu đầy đủ (để các bước sau dùng lại)
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime

from data_integration import config
from data_integration.profiling.core import checks_table, columns_table
from data_integration.profiling.sources import profile_speeds, profile_volume, profile_weather

log = logging.getLogger("profiling")

TITLES = {
    "weather": "Nguồn 3 — Thời tiết (Open-Meteo)",
    "volume": "Nguồn 2 — Lưu lượng (Automated Traffic Volume Counts)",
    "speeds": "Nguồn 1 — Tốc độ (DOT Traffic Speeds)",
}


def run_source(name: str) -> dict:
    raw = config.RAW_DIR
    t0 = time.time()
    if name == "weather":
        path = raw / "weather" / f"open_meteo_{config.STUDY_START}_{config.STUDY_END}.csv"
        res = profile_weather(path, config.STUDY_START, config.STUDY_END)
        res["files"] = [path.name]
    elif name == "volume":
        files = sorted((raw / "volume").glob("volume_*.csv"))
        res = profile_volume(files[0])
        res["files"] = [f.name for f in files]
    else:
        res = profile_speeds(raw / "speeds")
    res["seconds"] = round(time.time() - t0, 1)
    log.info("%s: %s dòng, %.1fs", name, f"{res['rows']:,}", res["seconds"])
    return res


def to_markdown(results: dict) -> str:
    out = [
        "# Báo cáo Data Profiling (bước 06)",
        "",
        f"Sinh tự động bởi `python -m data_integration.profiling.run` lúc {datetime.now():%Y-%m-%d %H:%M}.",
        f"Phạm vi: {config.STUDY_START} → {config.STUDY_END}.",
        "",
        "| Nguồn | File | Số dòng | Thời gian chạy |",
        "|---|---|---|---|",
    ]
    for k, r in results.items():
        files = ", ".join(r.get("files", []))
        if len(files) > 60:
            files = files[:60] + "…"
        out.append(f"| {TITLES[k]} | {files} | {r['rows']:,} | {r['seconds']}s |")
    for k, r in results.items():
        out += ["", f"## {TITLES[k]}", "", "### Kiểm tra chất lượng", "", checks_table(r["checks"])]
        if r.get("columns"):
            out += ["", "### Mô tả từng cột", "", columns_table(r["columns"])]
        for title, table in r.get("tables", {}).items():
            out += ["", f"### {title}", "", table]
    return "\n".join(out) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=["all", "weather", "volume", "speeds"], default="all")
    a = p.parse_args()
    sources = ["weather", "volume", "speeds"] if a.source == "all" else [a.source]

    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = config.REPORT_DIR / "06_profiling.json"
    results = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}
    for s in sources:
        results[s] = run_source(s)
    results = {k: results[k] for k in ("weather", "volume", "speeds") if k in results}

    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (config.REPORT_DIR / "06_profiling.md").write_text(to_markdown(results), encoding="utf-8")
    log.info("Đã ghi %s và 06_profiling.md", json_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
