"""
Tải dữ liệu từ NYC Open Data (nền tảng Socrata) bằng ngôn ngữ truy vấn SoQL.

- Dùng endpoint .csv để giảm dung lượng so với JSON.
- Phân trang bằng $limit/$offset, sắp xếp theo :id (khóa nội bộ của Socrata) để các trang
  không bị trùng hoặc sót khi phân trang.
- Ghi ra file tạm .part, chỉ đổi tên thành file chính khi đã tải xong và đếm đủ số dòng,
  nhờ vậy chạy lại script sẽ bỏ qua những phần đã tải xong (resume).
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd

from data_integration import config
from data_integration.collect.http_utils import get_with_retry

log = logging.getLogger(__name__)

PAGE_SIZE = 50_000


def _headers() -> dict:
    return {"X-App-Token": config.NYC_APP_TOKEN} if config.NYC_APP_TOKEN else {}


def count_rows(dataset: str, where: str) -> int:
    url = f"{config.NYC_BASE_URL}/{dataset}.json"
    resp = get_with_retry(url, params={"$select": "count(*) AS n", "$where": where}, headers=_headers())
    return int(resp.json()[0]["n"])


def fetch_page(dataset: str, select: str, where: str, offset: int, limit: int = PAGE_SIZE,
               order: str = ":id") -> pd.DataFrame:
    url = f"{config.NYC_BASE_URL}/{dataset}.csv"
    params = {"$select": select, "$where": where, "$order": order, "$limit": limit, "$offset": offset}
    resp = get_with_retry(url, params=params, headers=_headers())
    # Đọc mọi cột dạng chuỗi: tầng raw giữ nguyên dữ liệu gốc, ép kiểu để dành cho bước cleaning
    return pd.read_csv(io.StringIO(resp.text), dtype=str, keep_default_na=False)


def download(dataset: str, select: str, where: str, out_file: Path, verify_count: bool = True) -> int:
    """Tải toàn bộ các dòng thỏa `where` vào out_file (CSV). Trả về số dòng đã tải."""
    if out_file.exists():
        log.info("Đã có %s, bỏ qua", out_file.name)
        return -1

    expected = count_rows(dataset, where) if verify_count else None
    log.info("%s: cần tải %s dòng", out_file.name, f"{expected:,}" if expected is not None else "?")

    part = out_file.with_suffix(out_file.suffix + ".part")
    total, offset, first = 0, 0, True
    if part.exists():
        # Tải dở lần trước: các trang đã ghi trọn vẹn (sắp xếp ổn định theo :id) nên nối tiếp từ dòng kế tiếp.
        # Chỉ giữ lại số dòng là bội của PAGE_SIZE để chắc chắn không có trang nào bị ghi dở.
        done = len(pd.read_csv(part, dtype=str, keep_default_na=False, usecols=[0]))
        keep = (done // PAGE_SIZE) * PAGE_SIZE
        if keep != done:
            pd.read_csv(part, dtype=str, keep_default_na=False, nrows=keep).to_csv(part, index=False)
        total = offset = keep
        first = keep == 0
        log.info("%s: nối tiếp từ dòng %s (lần trước tải dở)", out_file.name, f"{keep:,}")
    while True:
        page = fetch_page(dataset, select, where, offset)
        if page.empty:
            break
        page.to_csv(part, mode="a", header=first, index=False)
        first = False
        total += len(page)
        offset += len(page)
        log.info("  %s: %s dòng", out_file.name, f"{total:,}")
        if len(page) < PAGE_SIZE:
            break

    if expected is not None and total != expected:
        raise RuntimeError(f"{out_file.name}: tải {total} dòng nhưng API báo {expected}. "
                           "Giữ lại file .part để kiểm tra, hãy chạy lại.")
    if total == 0:
        part.unlink(missing_ok=True)
        log.warning("%s: không có dòng nào", out_file.name)
        return 0
    part.rename(out_file)
    return total
