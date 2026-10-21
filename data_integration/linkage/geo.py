"""Hàm hình học: khoảng cách từ 1 điểm tới đường gấp khúc (polyline) của tuyến, đơn vị mét."""
from __future__ import annotations

import math

import numpy as np

_LAT0 = 40.7                                   # vĩ độ tham chiếu của New York
_MX = math.cos(math.radians(_LAT0)) * 111_320  # mét / độ kinh độ
_MY = 110_540                                  # mét / độ vĩ độ


def to_xy(lat: float, lon: float) -> np.ndarray:
    """Chiếu phẳng đều (equirectangular) quanh New York — sai số < 0,5% trong phạm vi thành phố."""
    return np.array([lon * _MX, lat * _MY])


def point_segment_distance(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    ab = b - a
    denom = float(np.dot(ab, ab))
    t = 0.0 if denom == 0 else min(1.0, max(0.0, float(np.dot(p - a, ab)) / denom))
    return float(np.linalg.norm(p - (a + t * ab)))


def point_polyline_distance(lat: float, lon: float, points: list[tuple[float, float]]) -> float:
    if not points or lat != lat:               # lat != lat ⇔ NaN
        return float("nan")
    p = to_xy(lat, lon)
    xy = [to_xy(*q) for q in points]
    if len(xy) == 1:
        return float(np.linalg.norm(p - xy[0]))
    return min(point_segment_distance(p, xy[i], xy[i + 1]) for i in range(len(xy) - 1))
