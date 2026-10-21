"""Test phần xử lý của bước thu thập, dùng phản hồi API giả lập (không cần mạng)."""
import pandas as pd

from data_integration import config
from data_integration.collect import fetch_speeds, fetch_weather, socrata


def _fake_open_meteo(n_hours=3, start_unix=1710050400):
    # 1710050400 = 2024-03-10 06:00 UTC = 01:00 EST. Lúc 07:00 UTC New York đổi sang giờ mùa hè (EDT)
    locs = []
    for i, s in enumerate(config.WEATHER_STATIONS.values()):
        locs.append({
            "latitude": s["latitude"], "longitude": s["longitude"],
            "hourly": {
                "time": [start_unix + 3600 * h for h in range(n_hours)],
                "temperature_2m": [1.0 + i] * n_hours,
                "precipitation": [0.0] * n_hours,
                "rain": [0.0] * n_hours,
                "snowfall": [0.0] * n_hours,
                "weather_code": [3] * n_hours,
            },
        })
    return locs


def test_weather_frame_has_all_stations_and_dst_correct():
    df = fetch_weather.response_to_frame(_fake_open_meteo())
    assert len(df) == 5 * 3
    assert set(df["station_id"]) == set(config.WEATHER_STATIONS)
    q = df[df.station_id == "OM_QUEENS"].reset_index(drop=True)
    # 06:00 UTC = 01:00 EST; 07:00 UTC = 03:00 EDT (không tồn tại 02:00 ngày này); 08:00 UTC = 04:00 EDT
    assert list(q["time_local"].dt.hour) == [1, 3, 4]


def test_weather_params_use_unixtime_gmt_with_padding():
    p = fetch_weather.build_params("2024-01-01", "2024-12-31")
    assert p["timezone"] == "GMT" and p["timeformat"] == "unixtime"
    assert len(p["latitude"].split(",")) == 5
    assert p["start_date"] == "2023-12-31" and p["end_date"] == "2025-01-01"


def test_weather_clip_to_local_year():
    # Dữ liệu UTC từ 31/12/2023 đến hết 01/01/2025 → sau khi cắt phải đúng 8.784 giờ địa phương của 2024
    start = int(pd.Timestamp("2023-12-31", tz="UTC").timestamp())
    hours = 24 * 368
    locs = [{"latitude": 0, "longitude": 0, "hourly": {
        "time": [start + 3600 * h for h in range(hours)], "temperature_2m": [0.0] * hours,
        "precipitation": [0.0] * hours, "rain": [0.0] * hours, "snowfall": [0.0] * hours,
        "weather_code": [0] * hours}} for _ in range(5)]
    df = fetch_weather.clip_local_range(fetch_weather.response_to_frame(locs), "2024-01-01", "2024-12-31")
    q = df[df.station_id == "OM_QUEENS"]
    assert len(q) == 8784                       # năm nhuận: 366 × 24 giờ thực
    assert q["time_local"].min() == pd.Timestamp("2024-01-01 00:00")
    assert q["time_local"].max() == pd.Timestamp("2024-12-31 23:00")


def test_month_where_boundaries():
    w = fetch_speeds.month_where("2024-12")
    assert "data_as_of >= '2024-12-01T00:00:00'" in w
    assert "data_as_of < '2025-01-01T00:00:00'" in w
    assert fetch_speeds.month_list("2024-01-01", "2024-12-31")[-1] == "2024-12"


def test_socrata_download_pages_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setattr(socrata, "PAGE_SIZE", 2)
    data = pd.DataFrame({"id": ["1", "2", "3", "4", "5"], "speed": ["10", "20", "30", "40", "50"]})
    monkeypatch.setattr(socrata, "count_rows", lambda ds, where: len(data))
    monkeypatch.setattr(socrata, "fetch_page",
                        lambda ds, sel, where, offset, limit=None, order=":id": data.iloc[offset:offset + 2].copy())
    out = tmp_path / "x.csv"
    assert socrata.download("ds", "id,speed", "1=1", out) == 5
    assert pd.read_csv(out).shape == (5, 2)
    assert not (tmp_path / "x.csv.part").exists()
    # Chạy lại thì bỏ qua file đã có
    assert socrata.download("ds", "id,speed", "1=1", out) == -1


def test_socrata_download_fails_when_count_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(socrata, "count_rows", lambda ds, where: 10)
    monkeypatch.setattr(socrata, "fetch_page",
                        lambda ds, sel, where, offset, limit=None, order=":id":
                        pd.DataFrame({"id": ["1"]}) if offset == 0 else pd.DataFrame())
    out = tmp_path / "y.csv"
    try:
        socrata.download("ds", "id", "1=1", out)
        assert False, "phải báo lỗi khi thiếu dòng"
    except RuntimeError:
        pass
    assert not out.exists() and (tmp_path / "y.csv.part").exists()


def test_socrata_download_resumes_from_part(tmp_path, monkeypatch):
    monkeypatch.setattr(socrata, "PAGE_SIZE", 2)
    data = pd.DataFrame({"id": [str(i) for i in range(1, 8)]})
    calls = []
    monkeypatch.setattr(socrata, "count_rows", lambda ds, where: len(data))

    def fake_page(ds, sel, where, offset, limit=None, order=":id"):
        calls.append(offset)
        return data.iloc[offset:offset + 2].copy()

    monkeypatch.setattr(socrata, "fetch_page", fake_page)
    out = tmp_path / "z.csv"
    # Giả lập lần trước: ghi được 2 trang (4 dòng) + 1 dòng của trang thứ 3 bị ghi dở
    data.iloc[:5].to_csv(tmp_path / "z.csv.part", index=False)
    assert socrata.download("ds", "id", "1=1", out) == 7
    assert calls[0] == 4                              # nối tiếp từ dòng 4, không tải lại từ đầu
    assert list(pd.read_csv(out)["id"]) == list(range(1, 8))
