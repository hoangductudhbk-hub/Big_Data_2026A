"""Test bước 08: độ đo chuỗi, chuẩn hóa tên, quy đổi về giờ, schema matching."""
import pandas as pd

from common.textsim import edit_similarity, jaccard, levenshtein, tokens
from data_integration.alignment import aggregate
from data_integration.alignment.names import normalize_name, parse_link_name
from data_integration.alignment.schema_matching import GROUND_TRUTH, evaluate, run_experiment


def test_levenshtein_matches_exercise():
    # Bài tập 1: x = hnoi, y = hanoi → d = 1, s = 0.8
    assert levenshtein("hnoi", "hanoi") == 1
    assert edit_similarity("hnoi", "hanoi") == 0.8
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("", "abc") == 3


def test_tokens_and_jaccard():
    assert tokens("ProductDescription") == ["product", "description"]
    assert tokens("data_as_of") == ["data", "as", "of"]
    assert jaccard({"product", "name"}, {"product", "description"}) == 1 / 3


def test_normalize_name():
    assert normalize_name("F D R DRIVE") == "FDR DRIVE"
    assert normalize_name("WILLETS PT BLVD") == "WILLETS POINT BOULEVARD"
    assert normalize_name("ST JAMES PLACE") == "SAINT JAMES PLACE"
    assert normalize_name("EAST 174 ST BRIDGE") == "EAST 174 STREET BRIDGE"
    assert normalize_name("84TH ST") == "84 STREET"


def test_parse_link_name():
    p = parse_link_name("BQE N LEONARD STREET - 46TH STREET")
    assert p == {"main_road": "BROOKLYN QUEENS EXPRESSWAY", "direction": "N",
                 "endpoints": ["LEONARD STREET", "46 STREET"]}
    assert parse_link_name("CBE E AMSTERDAM AVE(U/LVL) - MORRIS AVE")["endpoints"] == ["AMSTERDAM AVENUE", "MORRIS AVENUE"]


def test_speeds_hourly():
    df = pd.DataFrame({"link_id": "1", "speed_kmh": [40.0, 60.0, 50.0],
                       "timestamp": pd.to_datetime(["2024-01-01 08:05", "2024-01-01 08:55", "2024-01-01 09:00"])})
    h = aggregate.speeds_hourly(df)
    assert list(h["avg_speed"]) == [50.0, 50.0] and list(h["n_readings"]) == [2, 1]


def test_volume_hourly_keeps_only_complete_hours():
    rows = []
    for d in ("NB", "SB"):
        for mm in (0, 15, 30, 45):
            rows.append(("1", d, pd.Timestamp(f"2024-01-01 08:{mm:02d}"), 10))
    for mm in (0, 15, 30):                                            # giờ 9: hướng NB thiếu 1 khung
        rows.append(("1", "NB", pd.Timestamp(f"2024-01-01 09:{mm:02d}"), 10))
    for mm in (0, 15, 30, 45):
        rows.append(("1", "SB", pd.Timestamp(f"2024-01-01 09:{mm:02d}"), 10))
    for mm in (0, 15, 30, 45):                                        # giờ 10: thiếu cả hướng NB
        rows.append(("1", "SB", pd.Timestamp(f"2024-01-01 10:{mm:02d}"), 10))
    v = pd.DataFrame(rows, columns=["segmentid", "direction", "timestamp", "vol"]).assign(flag_outlier=False)
    out, st = aggregate.volume_hourly(v)
    assert list(out["vehicle_count"]) == [80]                          # chỉ giờ 8 đầy đủ: 2 hướng × 4 × 10
    assert st == {"segment_hours": 3, "complete": 1, "dropped_incomplete": 2}


def test_schema_matching_experiment():
    r = run_experiment(thresholds=(0.5,))
    assert r["name"][0.5]["recall"] < r["name+synonym"][0.5]["recall"]
    assert evaluate({k: (v, 1.0) for k, v in GROUND_TRUTH.items()})["f1"] == 1.0
