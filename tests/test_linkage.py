"""Test bước 09: độ đo OSA, luật ghép tên, blocking, khoảng cách tới polyline, nối đoạn ↔ tuyến."""
import pandas as pd
import pytest

from common.textsim import levenshtein, osa_distance
from data_integration.linkage import name_variants as nv
from data_integration.linkage import road_linkage as rl
from data_integration.linkage.geo import point_polyline_distance


def test_osa_counts_transposition_as_one_edit():
    assert levenshtein("WALKER", "WLAKER") == 2
    assert osa_distance("WALKER", "WLAKER") == 1
    assert osa_distance("hnoi", "hanoi") == 1


def test_name_rules():
    assert nv.rule_a("40 STREET", "90 STREET")                 # luật plan: ghép sai
    assert not nv.rule_b("40 STREET", "90 STREET")             # khác số → không ghép
    assert not nv.rule_b("EAST 117 STREET", "WEST 117 STREET")  # khác hướng
    assert nv.rule_c("WALKER STREET", "WLAKER STREET")
    assert nv.rule_c("DE KALB AVENUE", "DEKALB AVENUE")
    assert not nv.rule_c("CATON AVENUE", "WATSON AVENUE")


def test_blocking_drops_pairs_with_different_first_two_letters():
    names = ["WALKER STREET", "WLAKER STREET", "ARDEN AVENUE"]
    assert len(nv.candidate_pairs(names, None)) == 3
    assert len(nv.candidate_pairs(names, nv.BLOCKING_KEYS["2 chữ cái đầu"])) == 0   # WA ≠ WL: bỏ lỡ
    assert len(nv.candidate_pairs(names, nv.BLOCKING_KEYS["Chữ cái đầu"])) == 1


def test_variant_clusters_transitive():
    c = nv.variant_clusters(["BLOOMINGDALE ROAD", "BLLOMINGDALE ROAD", "BLOOMUINGDALE ROAD", "ARDEN AVENUE"])
    assert len(c) == 1 and c.iloc[0]["so_bien_the"] == 3


def test_point_polyline_distance():
    line = [(40.70, -73.90), (40.70, -73.80)]                     # đoạn thẳng theo kinh tuyến
    assert point_polyline_distance(40.70, -73.85, line) == pytest.approx(0, abs=0.01)
    assert point_polyline_distance(40.701, -73.85, line) == pytest.approx(110.5, rel=0.01)   # 0,001° vĩ ≈ 110 m


def test_name_score_prefix_not_containment():
    assert rl.name_score("BROOKLYN QUEENS EXPRESSWAY", "BROOKLYN QUEENS EXPRESSWAY ET 34 WB") == 1.0
    assert rl.name_score("BROOKLYN BRIDGE MANHATTAN SIDE", "MANHATTAN BRIDGE") < 0.8


def test_road_linkage_and_twin():
    links = pd.DataFrame({
        "link_id": ["1", "2", "3"], "main_road": ["FDR DRIVE", "FDR DRIVE", "WEST STREET"],
        "endpoints": ["63; 25 STREET", "25; 63 STREET", "A; B"],          # như dữ liệu thật FDR
        "district": ["Manhattan"] * 3, "latitude": [40.75] * 3, "longitude": [-73.97] * 3,
        "link_name": ["FDR S", "FDR N", "WEST ST"],
    })
    segs = pd.DataFrame({"segmentid": ["9"], "main_road": ["FDR DRIVE"], "district": ["Manhattan"],
                         "latitude": [40.7501], "longitude": [-73.97], "street": ["F D R DRIVE"],
                         "endpoints": ["X; Y"]})
    poly = {"1": [(40.74, -73.97), (40.76, -73.97)], "2": [], "3": [(40.74, -73.97), (40.76, -73.97)]}
    m, n, _ = rl.compare(links, segs, poly, block=True)
    assert n == 3 and list(m["link_id"]) == ["1"]                 # tuyến 3 gần nhưng khác tên
    m2 = rl.add_twins(m, links)
    assert set(m2["link_id"]) == {"1", "2"}
    reg = rl.build_registry(links, segs, m2)
    assert reg.loc[reg.road_id == "L1", "has_volume"].item() and len(reg) == 3   # đoạn 9 gộp vào L1
