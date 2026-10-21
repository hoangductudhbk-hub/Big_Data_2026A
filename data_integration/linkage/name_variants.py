"""
Phát hiện BIẾN THỂ của cùng một tên phố (lỗi chính tả, cách viết) trên toàn bộ tên của 2 nguồn.

So sánh 3 luật quyết định và 4 cách blocking, đánh giá bằng nhãn do người kiểm tra (labels.py).
"""
from __future__ import annotations

import itertools
import re
import time

import pandas as pd

from common.textsim import edit_similarity, osa_similarity
from data_integration.linkage.labels import TRUE_NAME_PAIRS

# Token mang tính "định danh": khác token này là khác đường, dù chuỗi rất giống nhau
QUALIFIERS = {"N", "S", "E", "W", "NB", "SB", "EB", "WB", "NORTH", "SOUTH", "EAST", "WEST",
              "UPPER", "LOWER", "NJ", "NY"}


def numbers(s: str) -> tuple:
    return tuple(re.findall(r"\d+", s))


def qualifiers(s: str) -> frozenset:
    return frozenset(t for t in s.split() if t in QUALIFIERS)


def rule_a(a: str, b: str) -> bool:
    """Luật trong plan: Levenshtein similarity ≥ 0,8."""
    return edit_similarity(a, b) >= 0.8


def rule_b(a: str, b: str) -> bool:
    """+ cùng các con số + cùng các từ chỉ hướng/tầng/bang."""
    return rule_a(a, b) and numbers(a) == numbers(b) and qualifiers(a) == qualifiers(b)


def rule_c(a: str, b: str) -> bool:
    """Như B, nhưng dùng OSA (có phép hoán vị), bỏ khoảng trắng trước khi so, ngưỡng 0,88."""
    if numbers(a) != numbers(b) or qualifiers(a) != qualifiers(b):
        return False
    return osa_similarity(a.replace(" ", ""), b.replace(" ", "")) >= 0.88


RULES = {"A: Levenshtein ≥ 0,8 (plan)": rule_a, "B: A + cùng số + cùng hướng/tầng": rule_b,
         "C: B + OSA không khoảng trắng ≥ 0,88": rule_c}

BLOCKING_KEYS = {
    "Không blocking (so mọi cặp)": None,
    "Chữ cái đầu": lambda s: s[:1],
    "2 chữ cái đầu": lambda s: s[:2],
    "Chữ cái đầu + các con số": lambda s: (s[:1], numbers(s)),
}


def candidate_pairs(names: list[str], key) -> list[tuple[str, str]]:
    if key is None:
        return list(itertools.combinations(names, 2))
    blocks: dict = {}
    for n in names:
        blocks.setdefault(key(n), []).append(n)
    return [p for b in blocks.values() for p in itertools.combinations(sorted(b), 2)]


def _pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def evaluate_rules(names: list[str]) -> list[dict]:
    """Chạy 3 luật trên MỌI cặp (không blocking) và tính precision/recall theo nhãn."""
    truth = {_pair(*p) for p in TRUE_NAME_PAIRS}
    pairs = list(itertools.combinations(names, 2))
    out = []
    for label, rule in RULES.items():
        found = {_pair(a, b) for a, b in pairs if rule(a, b)}
        tp = len(found & truth)
        out.append({"luat": label, "so_cap_ghep": len(found), "dung": tp,
                    "precision": round(tp / len(found), 3) if found else 0.0,
                    "recall": round(tp / len(truth), 3) if truth else 0.0,
                    "cap_sai_vi_du": "; ".join(f"{a} ~ {b}" for a, b in sorted(found - truth)[:4])})
    return out


def evaluate_blocking(names: list[str], rule=rule_c) -> list[dict]:
    """Reduction ratio và pair completeness của từng khóa blocking (so với kết quả không blocking)."""
    full = {_pair(a, b) for a, b in itertools.combinations(names, 2) if rule(a, b)}
    total = len(names) * (len(names) - 1) // 2
    out = []
    for label, key in BLOCKING_KEYS.items():
        t0 = time.perf_counter()
        cands = candidate_pairs(names, key)
        found = {_pair(a, b) for a, b in cands if rule(a, b)}
        out.append({"blocking": label, "so_cap_so_sanh": len(cands),
                    "reduction_ratio": round(1 - len(cands) / total, 4),
                    "pair_completeness": round(len(found & full) / len(full), 3) if full else 1.0,
                    "thoi_gian_ms": round(1000 * (time.perf_counter() - t0), 1),
                    "bo_lo": "; ".join(f"{a} ~ {b}" for a, b in sorted(full - found))})
    return out


def variant_clusters(names: list[str], rule=rule_c) -> pd.DataFrame:
    """Gom các tên được luật coi là cùng 1 đường thành cụm (bao đóng bắc cầu bằng union-find)."""
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in candidate_pairs(names, BLOCKING_KEYS["Chữ cái đầu"]):
        if rule(a, b):
            parent[find(a)] = find(b)
    groups: dict = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)
    rows = [{"ten_chuan": max(g, key=len), "bien_the": " / ".join(sorted(g)), "so_bien_the": len(g)}
            for g in groups.values() if len(g) > 1]
    return pd.DataFrame(rows)
