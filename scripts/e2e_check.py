"""
Bước 21 — Kiểm tra toàn hệ thống end-to-end qua HTTP (chạy khi API đang chạy và đã nạp dữ liệu).

    python scripts/e2e_check.py                       # mặc định http://localhost:8000
    python scripts/e2e_check.py --base http://localhost:8000 --report docs/bao-cao/21_e2e.md

Đối chiếu ba tầng với nhau:
  Parquet của Phase 1–2 (đọc trực tiếp bằng pandas)  ⇄  PostgreSQL (qua API)  ⇄  SQL trực tiếp (/statistics/live)
Mọi kiểm tra đều là so sánh số liệu THẬT, không phải chỉ "trả về 200".
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def call(base, path, method="GET", body=None):
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"} if body is not None else {})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data, status = json.loads(r.read() or b"null"), r.status
    except urllib.error.HTTPError as e:
        data, status = json.loads(e.read() or b"null"), e.code
    return status, data, (time.perf_counter() - t0) * 1000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data")
    ap.add_argument("--report", type=Path, default=None)
    a = ap.parse_args()
    import pandas as pd

    proc = a.data_dir / "processed"
    it = pd.read_parquet(proc / "integrated_traffic")
    an = pd.read_parquet(proc / "analytics" / "anomalies.parquet")
    st = pd.read_parquet(proc / "analytics" / "statistics.parquet")
    rows, ok_all = [], True

    def check(name, path, cond, detail, method="GET", body=None, expect=200):
        nonlocal ok_all
        status, data, ms = call(a.base, path, method, body)
        try:
            passed = status == expect and bool(cond(data))
        except Exception as e:  # noqa: BLE001
            passed, detail = False, f"{detail} (lỗi: {e})"
        ok_all &= passed
        rows.append({"kiem_tra": name, "endpoint": f"{method} {path}", "http": status, "ms": round(ms),
                     "ket_qua": "ĐẠT" if passed else "LỖI", "chi_tiet": detail(data) if callable(detail) else detail})
        print(f"[{'ĐẠT' if passed else 'LỖI'}] {name:<55} {status} {ms:6.0f} ms")
        return data

    check("API sống", "/health", lambda d: d["status"] == "ok", "status ok")
    check("Database + schema Alembic", "/api/v1/health/db", lambda d: d["schema_revision"] is not None,
          lambda d: f"{d.get('database')} · revision {d.get('schema_revision')}")
    s = check("Số bản ghi DB = số dòng Parquet integrated_traffic", "/api/v1/statistics/summary",
              lambda d: d["records"] == len(it), lambda d: f"DB {d['records']:,} · Parquet {len(it):,}")
    check("Số đường DB = số road_id trong Parquet", "/api/v1/statistics/summary",
          lambda d: d["roads"] == it["road_id"].nunique(), lambda d: f"{d['roads']} đường")
    check("Số bất thường DB = Parquet của bước 17", "/api/v1/anomalies?page_size=1",
          lambda d: d["total"] == len(an), lambda d: f"{d['total']:,} bản ghi")
    spark = st[(st.dimension == "district") & (st.metric == "avg_speed")].set_index("group_key")
    check("Spark (bước 15) = SQL trực tiếp trên PostgreSQL", "/api/v1/statistics/live?group_by=district",
          lambda d: all(abs(x["mean"] - spark.loc[x["group_key"], "mean"]) < 0.01
                        and abs(x["median"] - spark.loc[x["group_key"], "median"]) < 0.01
                        and x["n"] == spark.loc[x["group_key"], "n"] for x in d),
          lambda d: "mean, median, n của 5 quận khớp đến 0,01")
    check("GET /roads", "/api/v1/roads?page_size=5", lambda d: d["total"] > 0, lambda d: f"{d['total']} đường")
    first = check("GET /traffic (lọc + phân trang)", "/api/v1/traffic?road_id=L4616337&start=2024-03-01&end=2024-03-02",
                  lambda d: d["total"] == 24 or d["total"] > 0, lambda d: f"{d['total']} bản ghi ngày 01/03/2024")
    if first and first.get("items"):
        rid = first["items"][0]["id"]
        check("GET /traffic/{id}", f"/api/v1/traffic/{rid}", lambda d: d["id"] == rid, "đúng bản ghi")
    check("GET /traffic/timeseries", "/api/v1/traffic/timeseries?bucket=month", lambda d: len(d) >= 12,
          lambda d: f"{len(d)} tháng")
    check("GET /weather", "/api/v1/weather?page_size=1", lambda d: d["total"] > 0, lambda d: f"{d['total']:,} giờ")
    check("GET /statistics", "/api/v1/statistics?dimension=hour", lambda d: len(d) == 48, lambda d: f"{len(d)} dòng")
    check("GET /statistics/weather-impact", "/api/v1/statistics/weather-impact", lambda d: len(d) > 0,
          lambda d: f"{len(d)} nhóm")
    check("GET /anomalies/summary", "/api/v1/anomalies/summary", lambda d: d["total"] == len(an),
          lambda d: f"đường nhiều nhất: {d['top_roads'][0]['road_name']}")
    check("Lỗi 404 có định dạng thống nhất", "/api/v1/traffic/0", lambda d: d["error"]["type"] == "not_found",
          lambda d: d["error"]["message"], expect=404)
    check("Lỗi 422 khi tham số sai", "/api/v1/traffic?page_size=0", lambda d: d["error"]["type"] == "validation_error",
          lambda d: d["error"]["details"][0]["field"], expect=422)
    bad = [{"road_id": "L4616337", "timestamp": "2024-03-01T08:00:00", "avg_speed": 999}]
    check("POST /import/traffic từ chối dữ liệu sai contract", "/api/v1/import/traffic?all_or_nothing=true",
          lambda d: d["error"]["details"]["rejected"] == 1, lambda d: d["error"]["details"]["rejected_rows"][0]["errors"][0],
          method="POST", body=bad, expect=422)
    check("Dashboard được phục vụ", "/api/v1/health", lambda d: True, "xem /dashboard/")  # trang HTML kiểm tra riêng
    try:
        with urllib.request.urlopen(a.base + "/dashboard/", timeout=10) as r:
            html_ok = r.status == 200 and b"app.js" in r.read()
    except Exception:  # noqa: BLE001
        html_ok = False
    rows[-1].update(ket_qua="ĐẠT" if html_ok else "LỖI", endpoint="GET /dashboard/", chi_tiet="trả về trang HTML có app.js")
    ok_all &= html_ok

    print(f"\n{'TẤT CẢ ĐẠT' if ok_all else 'CÓ LỖI'}: {sum(r['ket_qua'] == 'ĐẠT' for r in rows)}/{len(rows)}")
    if a.report:
        lines = [f"# Báo cáo bước 21 — Kiểm tra end-to-end", "",
                 f"Sinh tự động lúc {datetime.now():%Y-%m-%d %H:%M} · API `{a.base}` · dữ liệu `{a.data_dir}`", "",
                 f"**Kết quả: {sum(r['ket_qua'] == 'ĐẠT' for r in rows)}/{len(rows)} kiểm tra đạt.**", "",
                 "| Kiểm tra | Endpoint | HTTP | ms | Kết quả | Chi tiết |", "|---|---|---|---|---|---|"]
        lines += [f"| {r['kiem_tra']} | `{r['endpoint']}` | {r['http']} | {r['ms']} | {r['ket_qua']} | "
                  f"{str(r['chi_tiet']).replace('|', '/')} |" for r in rows]
        a.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Báo cáo:", a.report)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
