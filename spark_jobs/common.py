"""
Dùng chung cho các job PySpark của Phase 2 (bước 11–17).

- get_spark(): tạo SparkSession cấu hình thống nhất (múi giờ New York, bộ nhớ, số nhân)
- PATHS: đường dẫn dữ liệu đầu vào/đầu ra
- timed(): đo thời gian một action
- Report: gom bảng/kết quả → docs/bao-cao/NN_*.md + .json

Đổi nguồn dữ liệu mock ↔ thật bằng biến môi trường:  INTEGRATED_PATH=data/mock/integrated_traffic
"""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "integrated": Path(os.getenv("INTEGRATED_PATH", ROOT / "data" / "processed" / "integrated_traffic")),
    "coverage": ROOT / "data" / "processed" / "coverage_daily.parquet",
    "roads": ROOT / "data" / "processed" / "roads.parquet",
    "speeds_clean": ROOT / "data" / "interim" / "speeds_clean",
    "links_clean": ROOT / "data" / "interim" / "links_clean.parquet",
    "weather_clean": ROOT / "data" / "interim" / "weather_clean.parquet",
    "raw_speeds": ROOT / "data" / "raw" / "speeds",
    "analytics": ROOT / "data" / "processed" / "analytics",
    "reports": ROOT / "docs" / "bao-cao",
}


def get_spark(app: str, cores: str = "*", driver_memory: str = "2g", extra: dict | None = None):
    # Máy không phân giải được hostname (VM, WSL, mạng công ty) → Spark không khởi động: ép dùng localhost
    os.environ.setdefault("SPARK_LOCAL_HOSTNAME", "localhost")
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    from pyspark.sql import SparkSession

    b = (SparkSession.builder.master(f"local[{cores}]").appName(app)
         .config("spark.driver.memory", driver_memory)
         .config("spark.sql.session.timeZone", "America/New_York")
         .config("spark.ui.showConsoleProgress", "false")
         .config("spark.sql.shuffle.partitions", "8"))       # dữ liệu cỡ vài GB trên 1 máy: 200 (mặc định) là quá nhiều
    for k, v in (extra or {}).items():
        b = b.config(k, v)
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


@contextmanager
def timed(results: dict, key: str):
    t0 = time.perf_counter()
    yield
    results[key] = round(time.perf_counter() - t0, 3)


def best_of(fn, repeat: int = 3) -> float:
    """Chạy fn nhiều lần, trả về thời gian NHỎ NHẤT (giảm nhiễu do JIT/cache hệ điều hành).
    CHÚ Ý: fn phải DỰNG LẠI DataFrame mỗi lần (vd lambda: build().collect()). Gọi lại action trên CÙNG một
    DataFrame thì Spark dùng lại kết quả shuffle cũ (skipped stages) → thời gian đo được sai, gần bằng 0."""
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return round(min(times), 3)


def measure(build, repeat: int = 3) -> dict:
    """build() trả về DataFrame MỚI. Đo lần đầu (lạnh) và tốt nhất trong `repeat` lần (đã ấm)."""
    times = []
    for _ in range(repeat):
        df = build()
        t0 = time.perf_counter()
        df.collect()
        times.append(time.perf_counter() - t0)
    return {"first_s": round(times[0], 3), "best_s": round(min(times), 3)}


def md_table(pdf, floatfmt: str = "{:,.2f}") -> str:
    cols = list(pdf.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for row in pdf.itertuples(index=False):
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append(floatfmt.format(v))
            elif isinstance(v, int) and not isinstance(v, bool):
                cells.append(f"{v:,}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


class Report:
    def __init__(self, step: str, title: str, spark=None):
        self.step, self.title = step, title
        self.parts: list[str] = []
        self.data: dict = {"generated": f"{datetime.now():%Y-%m-%d %H:%M}"}
        if spark is not None:
            sc = spark.sparkContext
            self.data["env"] = {"spark": spark.version, "master": sc.master,
                                "parallelism": sc.defaultParallelism,
                                "integrated_path": str(PATHS["integrated"].relative_to(ROOT))
                                if PATHS["integrated"].is_relative_to(ROOT) else str(PATHS["integrated"])}

    def h(self, text: str, level: int = 2):
        self.parts += ["", "#" * level + " " + text, ""]

    def p(self, text: str):
        self.parts.append(text)

    def table(self, pdf, key: str | None = None):
        self.parts += [md_table(pdf), ""]
        if key:
            self.data[key] = pdf.to_dict("records")

    def code(self, text: str, lang: str = "text"):
        self.parts += [f"```{lang}", text.strip(), "```", ""]

    def save(self):
        PATHS["reports"].mkdir(parents=True, exist_ok=True)
        env = self.data.get("env", {})
        head = [f"# {self.title}", "", f"Sinh tự động lúc {self.data['generated']}"
                + (f" · Spark {env['spark']} · {env['master']} ({env['parallelism']} nhân) · dữ liệu `{env['integrated_path']}`"
                   if env else "") + ".", ""]
        (PATHS["reports"] / f"{self.step}.md").write_text("\n".join(head + self.parts) + "\n", encoding="utf-8")
        (PATHS["reports"] / f"{self.step}.json").write_text(
            json.dumps(self.data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def save_analytics(df, name: str) -> Path:
    """Ghi kết quả phân tích (Spark DataFrame nhỏ) ra Parquet để backend (Phase 3) nạp vào PostgreSQL."""
    out = PATHS["analytics"] / f"{name}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.toPandas().to_parquet(out, index=False)
    return out
