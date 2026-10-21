"""
Record linkage giữa ĐOẠN ĐẾM LƯU LƯỢNG (volume segment) và TUYẾN ĐO TỐC ĐỘ (speed link).

Hai bản ghi là cùng một đoạn đường khi:
  1. Tên đường chính giống nhau: max(edit similarity, "tên ngắn là PHẦN ĐẦU của tên dài") ≥ 0,8
     (phần đầu, không phải "chứa từ": tránh ghép nhầm BROOKLYN BRIDGE MANHATTAN SIDE với MANHATTAN BRIDGE)
  2. Điểm đếm nằm gần đường gấp khúc của tuyến: ≤ MAX_DIST_M mét
Blocking: chỉ so các cặp cùng quận.
Tuyến chiều ngược lại ("twin": cùng đường chính, điểm đầu/cuối đảo nhau) được nối theo.
"""
from __future__ import annotations

import time

import pandas as pd

from common.textsim import edit_similarity
from data_integration.linkage.geo import point_polyline_distance

NAME_THRESHOLD = 0.8
MAX_DIST_M = 300


def name_score(a: str, b: str) -> float:
    ta, tb = a.split(), b.split()
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    prefix = 1.0 if len(short) >= 2 and long_[:len(short)] == short else 0.0
    return max(edit_similarity(a, b), prefix)


def compare(links: pd.DataFrame, segs: pd.DataFrame, polylines: dict, block: bool) -> tuple[pd.DataFrame, int, float]:
    t0 = time.perf_counter()
    rows, n = [], 0
    for _, s in links.iterrows():
        cand = segs[segs["district"] == s["district"]] if block else segs
        for _, v in cand.iterrows():
            n += 1
            ns = name_score(s["main_road"], v["main_road"])
            if ns < NAME_THRESHOLD:
                continue
            d = point_polyline_distance(v["latitude"], v["longitude"], polylines.get(s["link_id"], []))
            if d <= MAX_DIST_M:
                rows.append({"segmentid": v["segmentid"], "link_id": s["link_id"], "name_score": round(ns, 3),
                             "distance_m": round(d, 1), "rule": "direct"})
    return pd.DataFrame(rows), n, time.perf_counter() - t0


GENERIC = {"STREET", "AVENUE", "ROAD", "BOULEVARD", "PLACE", "DRIVE", "PARKWAY", "EXPRESSWAY"}


def _core(endpoint: str) -> str:
    """Bỏ từ chung chung để '63' và '63 STREET' được coi là một điểm."""
    return " ".join(t for t in endpoint.split() if t not in GENERIC)


def add_twins(matches: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """Tuyến chiều ngược lại: cùng main_road, tập điểm đầu/cuối giống nhau nhưng thứ tự đảo."""
    if matches.empty:
        return matches
    info = links.set_index("link_id")
    extra = []
    for _, m in matches.iterrows():
        me = info.loc[m["link_id"]]
        ends = [_core(e) for e in me["endpoints"].split(";") if e.strip()]
        for lid, other in info.iterrows():
            if lid == m["link_id"] or other["main_road"] != me["main_road"]:
                continue
            o_ends = [_core(e) for e in other["endpoints"].split(";") if e.strip()]
            if len(ends) == 2 and o_ends == ends[::-1]:
                extra.append({"segmentid": m["segmentid"], "link_id": lid, "name_score": m["name_score"],
                              "distance_m": None, "rule": "twin (chiều ngược lại)"})
    return pd.concat([matches, pd.DataFrame(extra)], ignore_index=True)


def build_registry(links: pd.DataFrame, segs: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """
    Bảng đường thống nhất. road_id = 'L<link_id>' cho mọi tuyến tốc độ; đoạn đếm đã nối được dùng road_id
    của tuyến nối TRỰC TIẾP (gần nhất); đoạn không nối được có road_id riêng 'S<segmentid>'.
    """
    direct = matches[matches["rule"] == "direct"].sort_values("distance_m").drop_duplicates("segmentid")
    seg_to_link = dict(zip(direct["segmentid"], direct["link_id"]))
    r_links = pd.DataFrame({
        "road_id": "L" + links["link_id"], "road_name": links["main_road"], "district": links["district"],
        "latitude": links["latitude"], "longitude": links["longitude"],
        "link_id": links["link_id"], "segmentid": links["link_id"].map({v: k for k, v in seg_to_link.items()}),
        "description": links["link_name"],
    })
    unmatched = segs[~segs["segmentid"].isin(seg_to_link)]
    r_segs = pd.DataFrame({
        "road_id": "S" + unmatched["segmentid"], "road_name": unmatched["main_road"],
        "district": unmatched["district"], "latitude": unmatched["latitude"], "longitude": unmatched["longitude"],
        "link_id": pd.Series(pd.NA, index=unmatched.index, dtype="string"), "segmentid": unmatched["segmentid"],
        "description": unmatched["street"] + " (" + unmatched["endpoints"] + ")",
    })
    reg = pd.concat([r_links, r_segs], ignore_index=True)
    reg["has_speed"] = reg["link_id"].notna()
    reg["has_volume"] = reg["segmentid"].notna()
    return reg
