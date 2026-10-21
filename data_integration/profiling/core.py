"""
Hàm profiling dùng chung: mô tả từng cột của một bảng dữ liệu raw (mọi cột đọc dạng chuỗi).

Với mỗi cột, đo:
- số giá trị rỗng (chuỗi rỗng hoặc NaN) và tỉ lệ %
- số giá trị khác nhau (distinct) và các giá trị phổ biến nhất
- tỉ lệ đọc được thành số; nếu phần lớn là số: min, max, mean, std, các phân vị
"""
from __future__ import annotations

import pandas as pd


def is_empty(s: pd.Series) -> pd.Series:
    return s.isna() | (s.astype("string").str.strip() == "")


def profile_column(s: pd.Series, top_n: int = 5) -> dict:
    n = len(s)
    empty = is_empty(s)
    non_empty = s[~empty]
    num = pd.to_numeric(non_empty, errors="coerce")
    numeric_rate = float(num.notna().mean()) if len(non_empty) else 0.0
    out = {
        "rows": n,
        "empty": int(empty.sum()),
        "empty_pct": round(100 * float(empty.mean()), 3) if n else 0.0,
        "distinct": int(non_empty.nunique()),
        "top_values": {str(k): int(v) for k, v in non_empty.value_counts().head(top_n).items()},
        "numeric_rate": round(numeric_rate, 4),
    }
    if numeric_rate >= 0.95:
        num = num.dropna()
        out["not_numeric"] = int(len(non_empty) - len(num))
        q = num.quantile([0.01, 0.25, 0.5, 0.75, 0.99])
        out["stats"] = {
            "min": float(num.min()), "p01": float(q[0.01]), "p25": float(q[0.25]), "median": float(q[0.5]),
            "p75": float(q[0.75]), "p99": float(q[0.99]), "max": float(num.max()),
            "mean": round(float(num.mean()), 4), "std": round(float(num.std()), 4),
        }
    return out


def profile_frame(df: pd.DataFrame, top_n: int = 5) -> dict:
    return {c: profile_column(df[c], top_n) for c in df.columns}


def iqr_outliers(x: pd.Series, k: float = 3.0) -> tuple[int, float, float]:
    """Đếm giá trị ngoài [Q1 - k·IQR, Q3 + k·IQR]. k = 3 là ngưỡng 'ngoại lai mạnh' (Tukey)."""
    x = x.dropna()
    q1, q3 = x.quantile(0.25), x.quantile(0.75)
    lo, hi = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
    return int(((x < lo) | (x > hi)).sum()), float(lo), float(hi)


# ---------------------------------------------------------------------------
# Xuất báo cáo Markdown
# ---------------------------------------------------------------------------
def fmt(x) -> str:
    if isinstance(x, float):
        return f"{x:,.2f}" if abs(x) < 1e6 else f"{x:,.0f}"
    if isinstance(x, int):
        return f"{x:,}"
    return str(x)


def columns_table(profile: dict) -> str:
    lines = ["| Cột | Rỗng | % rỗng | Distinct | % là số | Min | Median | Max | Giá trị phổ biến |",
             "|---|---|---|---|---|---|---|---|---|"]
    for col, p in profile.items():
        st = p.get("stats", {})
        top = ", ".join(f"`{k[:25]}` ({fmt(v)})" for k, v in list(p["top_values"].items())[:3])
        lines.append(
            f"| `{col}` | {fmt(p['empty'])} | {p['empty_pct']:.2f} | {fmt(p['distinct'])} | "
            f"{100 * p['numeric_rate']:.1f} | {fmt(st['min']) if st else ''} | "
            f"{fmt(st['median']) if st else ''} | {fmt(st['max']) if st else ''} | {top} |")
    return "\n".join(lines)


def checks_table(checks: list[dict]) -> str:
    lines = ["| Kiểm tra | Số bản ghi | Tỉ lệ | Ghi chú |", "|---|---|---|---|"]
    for c in checks:
        pct = f"{c['pct']:.3f}%" if c.get("pct") is not None else ""
        lines.append(f"| {c['name']} | {fmt(c['count'])} | {pct} | {c.get('note', '')} |")
    return "\n".join(lines)


def check(name: str, count: int, total: int | None = None, note: str = "") -> dict:
    return {"name": name, "count": int(count),
            "pct": (100 * count / total) if total else None, "note": note}
