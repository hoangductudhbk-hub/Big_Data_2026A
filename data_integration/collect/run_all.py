"""
Chạy toàn bộ bước thu thập dữ liệu: thời tiết → lưu lượng → tốc độ (lâu nhất, để cuối).

    python -m data_integration.collect.run_all

Chạy lại bao nhiêu lần cũng được: các file đã tải xong sẽ được bỏ qua.
"""
import logging
import sys

from data_integration import config
from data_integration.collect import fetch_speeds, fetch_volume, fetch_weather

if __name__ == "__main__":
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.RAW_DIR / "collect_log.txt"     # giữ lại log để điền vào hướng dẫn bước 05
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
    )
    for module in (fetch_weather, fetch_volume, fetch_speeds):
        logging.info("===== %s =====", module.__name__)
        sys.argv = [module.__name__]          # dùng tham số mặc định
        try:
            module.main()
        except Exception:
            logging.exception("LỖI ở %s. Chạy lại tai_du_lieu.bat để tiếp tục.", module.__name__)
            raise
