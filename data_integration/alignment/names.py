"""
Chuẩn hóa tên đường (giải quyết DATA heterogeneity: cùng một đường nhưng mỗi nguồn viết một kiểu).

    'BQE N LEONARD STREET - 46TH STREET'  → main = 'BROOKLYN QUEENS EXPRESSWAY', direction = 'N',
                                             endpoints = ['LEONARD STREET', '46 STREET']
    'BROOKLYN QUEENS EXPWY ET 34 WB'       → 'BROOKLYN QUEENS EXPRESSWAY ET 34 WB'
    'F D R DRIVE'                          → 'FDR DRIVE'

Không sửa lỗi chính tả trong dữ liệu gốc (BLLOMINGDALE, WLAKER...): việc đó để độ đo edit distance
ở bước 09 xử lý — đúng vai trò của so khớp xấp xỉ.
"""
from __future__ import annotations

import re

# Tên viết tắt các cao tốc / cầu / hầm của New York (xuất hiện trong link_name của nguồn tốc độ)
ROAD_ACRONYMS = {
    "BQE": "BROOKLYN QUEENS EXPRESSWAY", "LIE": "LONG ISLAND EXPRESSWAY", "CVE": "CLEARVIEW EXPRESSWAY",
    "CIP": "CROSS ISLAND PARKWAY", "GCP": "GRAND CENTRAL PARKWAY", "CBE": "CROSS BRONX EXPRESSWAY",
    "MDE": "MAJOR DEEGAN EXPRESSWAY", "BE": "BRUCKNER EXPRESSWAY", "VWE": "VAN WYCK EXPRESSWAY",
    "SIE": "STATEN ISLAND EXPRESSWAY", "WSE": "WEST SHORE EXPRESSWAY", "GOW": "GOWANUS EXPRESSWAY",
    "MLK": "MARTIN LUTHER KING EXPRESSWAY", "BRP": "BRONX RIVER PARKWAY", "HRP": "HUTCHINSON RIVER PARKWAY",
    "SSP": "SOUTHERN STATE PARKWAY", "FDR": "FDR DRIVE", "TBB": "TRIBOROUGH BRIDGE",
    "TNB": "THROGS NECK BRIDGE", "BWB": "BRONX WHITESTONE BRIDGE", "GWB": "GEORGE WASHINGTON BRIDGE",
    "VNB": "VERRAZZANO NARROWS BRIDGE", "BBT": "BROOKLYN BATTERY TUNNEL", "QMT": "QUEENS MIDTOWN TUNNEL",
    "NYST": "NEW YORK STATE THRUWAY",
}
# Hậu tố / từ viết tắt thông thường
WORD_ABBR = {
    "AVE": "AVENUE", "AV": "AVENUE", "ST": "STREET", "BLVD": "BOULEVARD", "BL": "BOULEVARD",
    "PKWY": "PARKWAY", "PKY": "PARKWAY", "EXPWY": "EXPRESSWAY", "EXPY": "EXPRESSWAY", "EXP": "EXPRESSWAY",
    "HWY": "HIGHWAY", "RD": "ROAD", "PL": "PLACE", "DR": "DRIVE", "TPK": "TURNPIKE", "TPKE": "TURNPIKE",
    "PT": "POINT", "BR": "BRIDGE", "LN": "LANE", "BKN": "BROOKLYN", "BKLYN": "BROOKLYN",
    "MAN": "MANHATTAN", "QNS": "QUEENS", "IS": "ISLAND",
}
DIRECTIONS = {"N", "S", "E", "W", "NB", "SB", "EB", "WB"}
_ORDINAL = re.compile(r"\b(\d+)(ST|ND|RD|TH)\b")


def _base_clean(text: str) -> str:
    t = (text or "").upper()
    t = re.sub(r"\([^)]*\)", " ", t)                        # bỏ chú thích trong ngoặc: (U/LVL), (EXIT 13 ...)
    t = re.sub(r"\b([A-Z]) (?=[A-Z]\b)", r"\1", t)          # 'F D R' → 'FDR'
    t = t.replace("@", " ")
    t = _ORDINAL.sub(r"\1", t)                              # '84TH' → '84'
    return re.sub(r"[^A-Z0-9 ]+", " ", t)


def normalize_name(text: str) -> str:
    """Chuẩn hóa 1 tên đường: bỏ ngoặc, ghép chữ cái rời, bỏ số thứ tự, mở rộng viết tắt."""
    toks = _base_clean(text).split()
    out = []
    for i, tk in enumerate(toks):
        if tk in ROAD_ACRONYMS:
            out.extend(ROAD_ACRONYMS[tk].split())
        elif tk == "ST" and i == 0 and len(toks) > 1 and not toks[1].isdigit():
            out.append("SAINT")                              # 'ST JAMES PLACE' → SAINT, không phải STREET
        elif tk in WORD_ABBR:
            out.append(WORD_ABBR[tk])
        else:
            out.append(tk)
    # Bỏ từ lặp liền nhau sinh ra khi mở rộng viết tắt: 'FDR DRIVE' + 'DRIVE' → 'FDR DRIVE'
    dedup = [t for i, t in enumerate(out) if i == 0 or t != out[i - 1]]
    return " ".join(dedup)


def parse_link_name(link_name: str) -> dict:
    """
    Tách tên tuyến của nguồn tốc độ: '<ĐƯỜNG CHÍNH> <HƯỚNG> <ĐIỂM ĐẦU> - <ĐIỂM CUỐI>'.
    Đường chính = các token đứng trước token hướng đầu tiên.
    """
    first, *rest = [p.strip() for p in re.split(r"\s+-\s+|-(?=[A-Z])", link_name.upper()) if p.strip()]
    toks = _base_clean(first).split()
    idx = next((i for i, t in enumerate(toks) if t in DIRECTIONS and i > 0), None)
    if idx is None:
        main, direction, start = " ".join(toks), "", ""
    else:
        main, direction, start = " ".join(toks[:idx]), toks[idx], " ".join(toks[idx + 1:])
    endpoints = [e for e in [start, *rest] if e]
    return {
        "main_road": normalize_name(main),
        "direction": direction,
        "endpoints": [normalize_name(e) for e in endpoints],
    }
