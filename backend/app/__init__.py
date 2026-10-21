"""Backend FastAPI của hệ thống Big Data giao thông New York (Phase 3).

Backend dùng chung data contract với Phase 1–2 (`common/contract.py` ở thư mục gốc project),
nên thư mục gốc project phải nằm trong sys.path. Docker đã đặt PYTHONPATH; khi chạy tay từ thư
mục backend/ (PyCharm, uvicorn) thì đoạn dưới tự thêm vào.
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
try:
    import common.contract  # noqa: F401
except ModuleNotFoundError:
    sys.path.insert(0, str(_PROJECT_ROOT))
