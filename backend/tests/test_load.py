import pandas as pd
import pytest
from sqlalchemy import func, select

from app.etl.load_processed import LoadError, load
from app.models import Anomaly, ImportLog, IntegratedTraffic, Road, Statistic


def test_load_counts(engine, data_dir):
    from sqlalchemy.orm import Session
    load(engine, data_dir, verbose=False)        # các test khác có thể đã import thêm dữ liệu → nạp lại
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(IntegratedTraffic)) == 3 * 48
        assert s.scalar(select(func.count()).select_from(Road)) == 3
        assert s.scalar(select(func.count()).select_from(Anomaly)) == 2
        assert s.scalar(select(func.count()).select_from(Statistic)) == 2
        assert s.scalar(select(func.count()).select_from(ImportLog)) >= 8


def test_reload_is_idempotent(engine, data_dir):
    c1 = load(engine, data_dir, verbose=False)
    c2 = load(engine, data_dir, verbose=False)
    assert c1 == c2 and c1["integrated_traffic"] == 144


def test_contract_violation_rolls_back(engine, data_dir, tmp_path):
    """File vi phạm contract → không nạp gì, dữ liệu cũ còn nguyên."""
    import shutil
    bad = tmp_path / "data"
    shutil.copytree(data_dir, bad)
    p = bad / "processed" / "integrated_traffic" / "part-0.parquet"
    df = pd.read_parquet(p)
    df.loc[0, "avg_speed"] = 999.0          # contract: avg_speed ≤ 160
    df.to_parquet(p)
    with pytest.raises(LoadError, match="contract"):
        load(engine, bad, verbose=False)
    from sqlalchemy.orm import Session
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(IntegratedTraffic)) == 144


def test_unknown_road_in_anomalies_is_rejected(engine, data_dir, tmp_path):
    import shutil
    bad = tmp_path / "data"
    shutil.copytree(data_dir, bad)
    p = bad / "processed" / "analytics" / "anomalies.parquet"
    df = pd.read_parquet(p)
    df.loc[0, "road_id"] = "L_KHONG_CO"
    df.to_parquet(p)
    with pytest.raises(LoadError, match="road_id"):
        load(engine, bad, only=("analytics",), verbose=False)
