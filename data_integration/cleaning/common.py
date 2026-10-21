"""Hàm làm sạch dùng chung và sổ ghi các quy tắc đã áp dụng (để xuất báo cáo cleaning)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from common.contract import DISTRICTS

_DISTRICT_LOOKUP = {d.upper(): d for d in DISTRICTS}
_DISTRICT_LOOKUP.update({"STATEN IS": "Staten Island", "SI": "Staten Island", "MN": "Manhattan",
                         "BK": "Brooklyn", "BX": "Bronx", "QN": "Queens"})


def normalize_district(s: pd.Series) -> pd.Series:
    """Đưa tên quận về 5 giá trị chuẩn của contract; giá trị lạ thành NA."""
    key = s.astype("string").str.upper().str.strip().str.replace(r"\s+", " ", regex=True)
    return key.map(_DISTRICT_LOOKUP).astype("string")


def normalize_text(s: pd.Series) -> pd.Series:
    """Viết hoa, bỏ khoảng trắng thừa. Không đổi viết tắt ở đây (để dành cho bước 08–09)."""
    return s.astype("string").str.upper().str.strip().str.replace(r"\s+", " ", regex=True)


_PAIR = re.compile(r"(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)")


SOCRATA_TEXT_LIMIT = 255


def parse_link_points(text: str) -> list[tuple[float, float]]:
    """
    Đọc chuỗi 'lat,lon lat,lon ...'.
    Socrata cắt chuỗi ở 255 ký tự → cặp cuối có thể bị cụt. Cụt có thể vẫn trông hợp lệ
    (vd '-73.9351' thành '-73.93', lệch tới ~400 m), nên khi chuỗi dài đúng 255 thì LUÔN bỏ cặp cuối.
    """
    if not isinstance(text, str) or not text:
        return []
    tokens = text.split(" ")
    if len(text) >= SOCRATA_TEXT_LIMIT or (tokens and not _PAIR.fullmatch(tokens[-1])):
        tokens = tokens[:-1]
    pts = []
    for t in tokens:
        m = _PAIR.fullmatch(t)
        if m:
            pts.append((float(m.group(1)), float(m.group(2))))
    return pts


@dataclass
class CleaningLog:
    """Ghi lại từng quy tắc: bao nhiêu dòng bị loại/sửa, để báo cáo minh bạch."""
    source: str
    rows_in: int = 0
    steps: list[dict] = field(default_factory=list)
    rows_out: int = 0

    def add(self, rule: str, affected: int, action: str, note: str = "") -> None:
        prev = next((s for s in self.steps if s["rule"] == rule and s["action"] == action), None)
        if prev:                                    # cộng dồn khi xử lý theo từng file tháng
            prev["affected"] += int(affected)
        else:
            self.steps.append({"rule": rule, "affected": int(affected), "action": action, "note": note})

    def as_dict(self) -> dict:
        return {"source": self.source, "rows_in": self.rows_in, "rows_out": self.rows_out, "steps": self.steps}


def to_parquet_us(df: pd.DataFrame, path) -> None:
    """
    Ghi Parquet với timestamp độ chính xác MICRO giây.
    pandas mặc định ghi NANO giây; Spark 3.x không đọc được (Illegal Parquet type: TIMESTAMP(NANOS)).
    """
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].astype("datetime64[us]")
    out.to_parquet(path, index=False)
