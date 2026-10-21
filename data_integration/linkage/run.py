"""
Bước 09 — Record linkage + blocking.

    python -m data_integration.linkage.run

Đầu ra:
    data/interim/linkage/road_links.parquet     Cặp (segmentid, link_id) đã nối + điểm + khoảng cách
    data/interim/linkage/name_variants.parquet  Cụm biến thể tên đường
    data/processed/roads.parquet                Bảng đường thống nhất (road_id dùng cho integrated_traffic)
    docs/bao-cao/09_linkage.md + .json
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

import pandas as pd

from data_integration import config
from data_integration.alignment.names import normalize_name
from data_integration.cleaning.common import parse_link_points, to_parquet_us
from data_integration.linkage import name_variants as nv
from data_integration.linkage import road_linkage as rl
from data_integration.linkage.labels import TRUE_ROAD_LINKS

log = logging.getLogger("linkage")


def all_names(rs: pd.DataFrame, rv: pd.DataFrame) -> list[str]:
    names = set(rs["main_road"]) | set(rv["main_road"])
    for e in rs["endpoints"]:
        names |= {x.strip() for x in e.split(";") if x.strip()}
    for c in ("fromst", "tost"):
        names |= {normalize_name(x) for x in rv[c]}
    return sorted(n for n in names if n)


def _md(rows: list[dict]) -> str:
    if not rows:
        return "(không có)"
    cols = list(rows[0])
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] +
                     ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows])


def run() -> dict:
    al, out = config.INTERIM_DIR / "aligned", config.INTERIM_DIR / "linkage"
    out.mkdir(parents=True, exist_ok=True)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    rs = pd.read_parquet(al / "roads_speeds.parquet")
    rv = pd.read_parquet(al / "roads_volume.parquet")
    raw_links = pd.read_csv(config.RAW_DIR / "speeds" / "links.csv", dtype=str, keep_default_na=False)
    polylines = {r.link_id: parse_link_points(r.link_points) for r in raw_links.itertuples()}
    r: dict = {"generated": f"{datetime.now():%Y-%m-%d %H:%M}"}

    # A. Biến thể tên đường
    names = all_names(rs, rv)
    r["names"] = len(names)
    r["name_rules"] = nv.evaluate_rules(names)
    r["name_blocking"] = nv.evaluate_blocking(names)
    clusters = nv.variant_clusters(names)
    to_parquet_us(clusters, out / "name_variants.parquet")
    r["name_clusters"] = clusters.to_dict("records")
    log.info("Tên đường: %d tên, %d cụm biến thể", len(names), len(clusters))

    # B. Nối đoạn đếm ↔ tuyến tốc độ, có và không có blocking
    full, n_full, t_full = rl.compare(rs, rv, polylines, block=False)
    blk, n_blk, t_blk = rl.compare(rs, rv, polylines, block=True)
    key = lambda df: set(zip(df.get("segmentid", []), df.get("link_id", [])))
    truth = set(TRUE_ROAD_LINKS)
    r["road_blocking"] = [
        {"cach": "Không blocking", "so_cap": n_full, "reduction_ratio": 0.0, "pair_completeness": 1.0,
         "thoi_gian_s": round(t_full, 2), "so_cap_noi": len(full)},
        {"cach": "Blocking theo quận", "so_cap": n_blk, "reduction_ratio": round(1 - n_blk / n_full, 4),
         "pair_completeness": round(len(key(blk) & key(full)) / len(key(full)), 3) if len(full) else 1.0,
         "thoi_gian_s": round(t_blk, 2), "so_cap_noi": len(blk)},
    ]
    tp = len(key(blk) & truth)
    r["road_eval"] = {"predicted": len(blk), "true": len(truth), "correct": tp,
                      "precision": round(tp / len(blk), 3) if len(blk) else 0.0,
                      "recall": round(tp / len(truth), 3)}
    matches = rl.add_twins(blk, rs)
    to_parquet_us(matches, out / "road_links.parquet")
    info = rs.set_index("link_id")["link_name"]
    segname = rv.set_index("segmentid")["street"]
    r["road_matches"] = [{**m, "link_name": info.get(m["link_id"]), "street": segname.get(m["segmentid"])}
                         for m in matches.to_dict("records")]

    reg = rl.build_registry(rs, rv, matches)
    to_parquet_us(reg, config.PROCESSED_DIR / "roads.parquet")
    r["registry"] = {"roads": len(reg), "speed_only": int((reg.has_speed & ~reg.has_volume).sum()),
                     "volume_only": int((~reg.has_speed & reg.has_volume).sum()),
                     "both": int((reg.has_speed & reg.has_volume).sum()),
                     "by_district": reg["district"].value_counts().to_dict()}
    log.info("Đường thống nhất: %s", r["registry"])
    write_report(r)
    return r


def write_report(r: dict) -> None:
    md = ["# Báo cáo Record Linkage (bước 09)", "", f"Sinh tự động lúc {r['generated']}.", "",
          f"## A. Biến thể tên đường ({r['names']} tên của cả 2 nguồn, {r['names'] * (r['names'] - 1) // 2:,} cặp)", "",
          "### Luật quyết định (so mọi cặp, đánh giá bằng nhãn kiểm tra tay)", "", _md(r["name_rules"]), "",
          "### Blocking (với luật C)", "", _md(r["name_blocking"]), "",
          "### Cụm biến thể tìm được (luật C, blocking theo chữ cái đầu)", "",
          _md([{k: v for k, v in c.items()} for c in r["name_clusters"]]), "",
          "## B. Nối đoạn đếm lưu lượng ↔ tuyến đo tốc độ", "",
          "### Blocking", "", _md(r["road_blocking"]), "",
          "### Kết quả so với nhãn", "", _md([r["road_eval"]]), "",
          "### Các cặp đã nối", "", _md(r["road_matches"]), "",
          "## C. Bảng đường thống nhất (data/processed/roads.parquet)", "", _md([r["registry"]])]
    (config.REPORT_DIR / "09_linkage.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (config.REPORT_DIR / "09_linkage.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str),
                                                       encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    log.info("Xong. Báo cáo: docs/bao-cao/09_linkage.md")
