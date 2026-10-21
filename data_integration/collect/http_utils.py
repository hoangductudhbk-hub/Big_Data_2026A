"""Gọi HTTP có thử lại (retry) với thời gian chờ tăng dần."""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}

# Một số máy chủ chặn nhãn mặc định "python-requests/x.y" (chống bot) và trả về 403.
# Gửi kèm User-Agent ghi rõ đây là project học tập.
DEFAULT_HEADERS = {
    "User-Agent": "Big_Data_2026A/1.0 (university course project; python)",
    "Accept": "*/*",
}


def get_with_retry(url: str, params: dict | None = None, headers: dict | None = None,
                   max_retries: int = 6, timeout: int = 120) -> requests.Response:
    """GET, tự thử lại khi bị giới hạn tốc độ (429) hoặc lỗi máy chủ (5xx), hoặc mất kết nối."""
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers={**DEFAULT_HEADERS, **(headers or {})},
                                timeout=timeout)
        except requests.RequestException as exc:
            if attempt == max_retries:
                raise
            log.warning("Lỗi kết nối (%s), thử lại sau %.0fs (lần %d/%d)", exc, delay, attempt, max_retries)
        else:
            if resp.status_code not in RETRY_STATUS:
                if resp.status_code >= 400:
                    log.error("HTTP %s khi gọi %s\nNội dung trả về: %s", resp.status_code, resp.url, resp.text[:800])
                    if resp.status_code == 403:
                        log.error("403 = máy chủ từ chối. Cách xử lý: đăng ký app token miễn phí "
                                  "(xem docs/huong-dan/05_thu_thap_du_lieu.md, mục 3) rồi chạy lại.")
                resp.raise_for_status()
                return resp
            if attempt == max_retries:
                resp.raise_for_status()
            log.warning("HTTP %s, thử lại sau %.0fs (lần %d/%d)", resp.status_code, delay, attempt, max_retries)
        time.sleep(delay)
        delay = min(delay * 2, 120)
    raise RuntimeError("unreachable")
