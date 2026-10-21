"""
Tải NYC DOT Traffic Speeds (dataset i4gi-tjb9) theo từng tháng.

Chạy:
    python -m data_integration.collect.fetch_speeds                  # cả năm 2024
    python -m data_integration.collect.fetch_speeds --months 2024-01 2024-02
    python -m data_integration.collect.fetch_speeds --links-only     # chỉ tải danh mục tuyến đường

Đầu ra:
    data/raw/speeds/speeds_YYYY-MM.csv   Bản ghi tốc độ (không lấy cột polyline cho nhẹ)
    data/raw/speeds/links.csv            Danh mục tuyến: link_id, link_name, borough, link_points...

Vì sao tách danh mục tuyến ra riêng: các cột link_points/encoded_poly_line dài hàng trăm ký tự và
lặp lại ở MỌI bản ghi. Nếu tải kèm thì dung lượng tăng nhiều lần. Đây là bước chuẩn hóa
(normalization): tách thông tin "tĩnh" của tuyến đường khỏi bản ghi đo "động".
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from data_integration import config
from data_integration.collect import socrata

log = logging.getLogger("fetch_speeds")

RECORD_COLUMNS = "id,speed,travel_time,status,data_as_of,link_id,borough,link_name"
LINK_COLUMNS = "link_id,link_name,borough,owner,transcom_id,link_points"


def month_list(start: str, end: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]


def month_where(month: str) -> str:
    start = pd.Period(month, freq="M").start_time
    nxt = start + pd.offsets.MonthBegin(1)
    return f"data_as_of >= '{start:%Y-%m-%dT%H:%M:%S}' AND data_as_of < '{nxt:%Y-%m-%dT%H:%M:%S}'"


def download_links(months: list[str]) -> None:
    """Lấy danh mục tuyến từ 1 giờ dữ liệu đầu mỗi tháng (đủ để thấy mọi tuyến đang hoạt động)."""
    out = config.RAW_DIR / "speeds" / "links.csv"
    if out.exists():
        log.info("Đã có links.csv, bỏ qua")
        return
    frames = []
    for m in months:
        start = pd.Period(m, freq="M").start_time + pd.Timedelta(hours=12)   # 12h trưa ngày 1
        end = start + pd.Timedelta(hours=1)
        where = f"data_as_of >= '{start:%Y-%m-%dT%H:%M:%S}' AND data_as_of < '{end:%Y-%m-%dT%H:%M:%S}'"
        page = socrata.fetch_page(config.SPEEDS_DATASET, LINK_COLUMNS, where, offset=0)
        page["seen_month"] = m
        frames.append(page)
        log.info("Danh mục tuyến %s: %d bản ghi", m, len(page))
    links = pd.concat(frames, ignore_index=True)
    # Giữ phiên bản mới nhất của mỗi link_id (tên/tọa độ có thể được sửa trong năm)
    links = links.sort_values("seen_month").drop_duplicates("link_id", keep="last")
    links.to_csv(out, index=False)
    log.info("Đã lưu %d tuyến → %s", len(links), out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--months", nargs="*", help="Danh sách tháng YYYY-MM (mặc định: cả phạm vi nghiên cứu)")
    parser.add_argument("--links-only", action="store_true")
    args = parser.parse_args()

    months = args.months or month_list(config.STUDY_START, config.STUDY_END)
    (config.RAW_DIR / "speeds").mkdir(parents=True, exist_ok=True)

    download_links(months)
    if args.links_only:
        return

    summary = []
    for m in months:
        out = config.RAW_DIR / "speeds" / f"speeds_{m}.csv"
        if out.exists():
            summary.append((m, -1))
            continue
        n = socrata.download(config.SPEEDS_DATASET, RECORD_COLUMNS, month_where(m), out)
        summary.append((m, n))
    log.info("Tổng kết:\n%s", "\n".join(f"  {m}: {n:,} dòng" if n >= 0 else f"  {m}: đã có sẵn"
                                          for m, n in summary))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
