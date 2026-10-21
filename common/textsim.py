"""
Các độ đo tương đồng chuỗi (đúng định nghĩa trong bài giảng Schema Alignment / Record Linkage).

Tự cài đặt để minh họa thuật toán; với dữ liệu lớn, bước 09 dùng thư viện rapidfuzz (cùng kết quả, nhanh hơn).
"""
from __future__ import annotations

import re


def levenshtein(a: str, b: str) -> int:
    """Khoảng cách chỉnh sửa: số phép chèn/xóa/thay thế tối thiểu (quy hoạch động, bộ nhớ O(len(b)))."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1,                 # xóa
                           cur[j - 1] + 1,              # chèn
                           prev[j - 1] + (ca != cb)))   # thay thế / giữ nguyên
        prev = cur
    return prev[-1]


def edit_similarity(a: str, b: str) -> float:
    """s(x, y) = 1 − d(x, y) / max(|x|, |y|)."""
    if not a and not b:
        return 1.0
    return 1 - levenshtein(a, b) / max(len(a), len(b))


def tokens(name: str) -> list[str]:
    """Tách tên thuộc tính/tên đường thành token: snake_case, camelCase, dấu cách, ký tự đặc biệt."""
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return [t for t in re.split(r"[^A-Za-z0-9]+", name.lower()) if t]


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def osa_distance(a: str, b: str) -> int:
    """
    Damerau–Levenshtein (Optimal String Alignment): như Levenshtein nhưng thêm phép HOÁN VỊ 2 ký tự kề nhau.
    'WALKER' → 'WLAKER' là 1 lỗi gõ (đổi chỗ A, L): Levenshtein tính 2, OSA tính 1.
    """
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[n][m]


def osa_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return 1 - osa_distance(a, b) / max(len(a), len(b))
