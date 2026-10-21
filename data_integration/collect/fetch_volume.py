"""
Tải NYC Automated Traffic Volume Counts (dataset 7ym2-wayt) theo năm.

Chạy:
    python -m data_integration.collect.fetch_volume                # năm của phạm vi nghiên cứu
    python -m data_integration.collect.fetch_volume --years 2023 2024

Đầu ra:
    data/raw/volume/volume_YYYY.csv
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd
import requests

from data_integration import config
from data_integration.collect import socrata

log = logging.getLogger("fetch_volume")

COLUMNS = "requestid,boro,yr,m,d,hh,mm,vol,segmentid,wktgeom,street,fromst,tost,direction"


def year_where(year: int) -> str:
    """Cột yr có thể là số hoặc chuỗi tùy cách Socrata lưu; thử dạng số trước."""
    try:
        socrata.count_rows(config.VOLUME_DATASET, f"yr = {year}")
        return f"yr = {year}"
    except requests.HTTPError as exc:
        # Chỉ chuyển sang so sánh chuỗi khi lỗi là do sai kiểu dữ liệu (HTTP 400)
        if exc.response is None or exc.response.status_code != 400:
            raise
        log.info("yr không phải kiểu số, dùng so sánh chuỗi")
        return f"yr = '{year}'"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs="*", type=int)
    args = parser.parse_args()

    years = args.years or sorted({pd.Timestamp(config.STUDY_START).year, pd.Timestamp(config.STUDY_END).year})
    (config.RAW_DIR / "volume").mkdir(parents=True, exist_ok=True)

    for y in years:
        out = config.RAW_DIR / "volume" / f"volume_{y}.csv"
        if out.exists():                     # không gọi API khi đã có file (chạy lại được khi không có VPN)
            log.info("Đã có %s, bỏ qua", out.name)
            continue
        n = socrata.download(config.VOLUME_DATASET, COLUMNS, year_where(y), out)
        log.info("Năm %d: %s", y, f"{n:,} dòng" if n >= 0 else "đã có sẵn")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
