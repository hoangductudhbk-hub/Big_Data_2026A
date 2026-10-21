"""
Thử nghiệm SCHEMA MATCHING tự động: tìm thuộc tính tương ứng giữa lược đồ nguồn và lược đồ trung gian.

Hai bộ so khớp (matcher) theo bài giảng:
  1. Name-based matcher : chỉ dùng tên thuộc tính — max(Jaccard trên token, độ tương đồng edit distance)
  2. Name + synonym     : thêm từ điển đồng nghĩa của miền giao thông/thời tiết (tri thức chuyên gia)

Kết quả được so với ÁNH XẠ CHUẨN (ground truth) do con người xác định để tính precision / recall / F1.
Mục đích: chứng minh định lượng vì sao không thể chỉ dựa vào so khớp tên, cần ánh xạ GAV viết tay (mapping.py).
"""
from __future__ import annotations

from common.contract import COLUMN_NAMES
from common.textsim import edit_similarity, jaccard, tokens

# Lược đồ nguồn (tên cột gốc trong dữ liệu raw)
SOURCE_SCHEMAS: dict[str, list[str]] = {
    "speeds": ["id", "speed", "travel_time", "status", "data_as_of", "link_id", "link_points", "borough", "link_name"],
    "volume": ["requestid", "boro", "yr", "m", "d", "hh", "mm", "vol", "segmentid", "wktgeom",
               "street", "fromst", "tost", "direction"],
    "weather": ["station_id", "time_local", "temperature_2m", "precipitation", "rain", "snowfall",
                "weather_code", "district", "grid_latitude", "grid_longitude"],
}

# Lược đồ trung gian = data contract (bỏ cột suy diễn 'source')
TARGET = [c for c in COLUMN_NAMES if c != "source"]

# Ánh xạ chuẩn do con người xác định: (nguồn, cột nguồn) → cột đích. Cột không có trong đây = không ánh xạ.
GROUND_TRUTH: dict[tuple[str, str], str] = {
    ("speeds", "speed"): "avg_speed", ("speeds", "data_as_of"): "timestamp",
    ("speeds", "link_id"): "road_id", ("speeds", "link_name"): "road_name",
    ("speeds", "borough"): "district", ("speeds", "link_points"): "latitude",   # cũng → longitude (1:n)
    ("volume", "boro"): "district", ("volume", "yr"): "timestamp", ("volume", "m"): "timestamp",
    ("volume", "d"): "timestamp", ("volume", "hh"): "timestamp", ("volume", "mm"): "timestamp",
    ("volume", "vol"): "vehicle_count", ("volume", "segmentid"): "road_id", ("volume", "wktgeom"): "latitude",
    ("volume", "street"): "road_name",
    ("weather", "time_local"): "timestamp", ("weather", "temperature_2m"): "temperature",
    ("weather", "rain"): "rainfall", ("weather", "snowfall"): "snowfall",
    ("weather", "weather_code"): "weather_condition", ("weather", "district"): "district",
    ("weather", "station_id"): "weather_station_id",
}
# Ánh xạ 1:n — một cột nguồn đóng góp cho nhiều cột đích; chấp nhận khi khớp với bất kỳ cột nào
ALSO_CORRECT = {("speeds", "link_points"): {"longitude"}, ("volume", "wktgeom"): {"longitude"}}

# Từ điển đồng nghĩa (tri thức miền) — token nguồn → token đích
SYNONYMS: dict[str, set[str]] = {
    "boro": {"district"}, "borough": {"district"},
    "vol": {"vehicle", "count"}, "volume": {"vehicle", "count"},
    "speed": {"avg", "speed"},
    "as": {"timestamp"}, "of": {"timestamp"}, "yr": {"timestamp"}, "hh": {"timestamp"}, "mm": {"timestamp"},
    "m": {"timestamp"}, "d": {"timestamp"}, "time": {"timestamp"},
    "rain": {"rainfall"}, "code": {"condition"},
    "link": {"road"}, "segmentid": {"road", "id"}, "street": {"road", "name"},
    "points": {"latitude", "longitude"}, "wktgeom": {"latitude", "longitude"}, "temperature": {"temperature"},
}


def name_score(src: str, tgt: str) -> float:
    ts, tt = set(tokens(src)), set(tokens(tgt))
    return max(jaccard(ts, tt), edit_similarity(src.lower(), tgt.lower()))


def synonym_score(src: str, tgt: str) -> float:
    ts = set(tokens(src)) | {src.lower()}
    expanded = set(ts)
    for t in ts:
        expanded |= SYNONYMS.get(t, set())
    return max(name_score(src, tgt), jaccard(expanded & set(tokens(tgt)) or set(), set(tokens(tgt))))


def match(score_fn, threshold: float) -> dict[tuple[str, str], tuple[str, float]]:
    """Với mỗi cột nguồn, chọn cột đích có điểm cao nhất nếu ≥ ngưỡng."""
    out = {}
    for source, cols in SOURCE_SCHEMAS.items():
        for c in cols:
            best = max(TARGET, key=lambda t: score_fn(c, t))
            s = score_fn(c, best)
            if s >= threshold:
                out[(source, c)] = (best, round(s, 3))
    return out


def evaluate(pred: dict) -> dict:
    def correct(k, v):
        return GROUND_TRUTH.get(k) == v or v in ALSO_CORRECT.get(k, set())

    tp = sum(1 for k, (v, _) in pred.items() if correct(k, v))
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(GROUND_TRUTH)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"predicted": len(pred), "correct": tp, "ground_truth": len(GROUND_TRUTH),
            "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def run_experiment(thresholds=(0.3, 0.4, 0.5, 0.6, 0.7)) -> dict:
    res = {"name": {}, "name+synonym": {}}
    for th in thresholds:
        res["name"][th] = evaluate(match(name_score, th))
        res["name+synonym"][th] = evaluate(match(synonym_score, th))
    res["detail_name_0.5"] = {f"{s}.{c}": v for (s, c), v in match(name_score, 0.5).items()}
    res["detail_synonym_0.5"] = {f"{s}.{c}": v for (s, c), v in match(synonym_score, 0.5).items()}
    return res
