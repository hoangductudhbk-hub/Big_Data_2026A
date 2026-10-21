"""Test profiling với dữ liệu raw giả lập có cài sẵn lỗi đã biết số lượng."""
import pandas as pd

from data_integration.collect import fetch_weather
from data_integration.profiling.core import profile_column
from data_integration.profiling.sources import profile_speeds, profile_volume, profile_weather


def _by_name(res, text):
    return next(c for c in res["checks"] if text in c["name"])


def test_profile_column_numeric_and_empty():
    p = profile_column(pd.Series(["1", "2", "", "x", "4"]))
    assert p["empty"] == 1 and p["distinct"] == 4
    assert p["numeric_rate"] == 0.75 and "stats" not in p    # < 95% là số


def test_weather_detects_dst_duplicate(tmp_path):
    # 3 ngày quanh lúc lùi giờ 03/11/2024 (05:00 UTC = 01:00 EDT, 06:00 UTC = 01:00 EST)
    start = int(pd.Timestamp("2024-11-02", tz="UTC").timestamp())
    hours = 72
    locs = [{"latitude": 0, "longitude": 0, "hourly": {
        "time": [start + 3600 * h for h in range(hours)],
        "temperature_2m": [10.0] * hours, "precipitation": [0.5] * hours, "rain": [0.5] * hours,
        "snowfall": [0.0] * hours, "weather_code": [61] * hours}} for _ in range(5)]
    path = tmp_path / "w.csv"
    fetch_weather.response_to_frame(locs).to_csv(path, index=False)
    res = profile_weather(path, "2024-11-02", "2024-11-04")
    assert res["rows"] == 5 * 72
    assert _by_name(res, "Trùng (station, time_local)")["count"] == 5 * 2     # mỗi trạm 2 dòng 01:00
    assert _by_name(res, "Trùng (station, time_utc)")["count"] == 0
    assert _by_name(res, "Khoảng trống")["count"] == 0


def test_volume_checks(tmp_path):
    base = dict(requestid="1", boro="Queens", yr="2024", m="3", d="7", hh="4", segmentid="55135",
                wktgeom="POINT (1035363.4 185093.4)", street="122 PL", fromst="A", tost="B", direction="SB")
    rows = [dict(base, mm=str(mm), vol="5") for mm in (0, 15, 30, 45)]
    rows.append(dict(base, mm="45", vol="9"))                    # trùng khóa, khác giá trị
    rows.append(dict(base, mm="10", vol="-3"))                   # phút sai + vol âm
    rows.append(dict(base, hh="5", mm="30", vol="7"))            # tạo khoảng thiếu 5:00, 5:15
    rows.append(dict(base, mm="0", vol="5", street="QUEENS BLVD", wktgeom="POINT (abc)"))
    path = tmp_path / "v.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    res = profile_volume(path)
    assert _by_name(res, "Phút không thuộc")["count"] == 1
    assert _by_name(res, "vol âm")["count"] == 1
    assert _by_name(res, "…trong đó khác giá trị")["count"] == 1
    assert _by_name(res, "wktgeom không đọc được")["count"] == 1
    assert _by_name(res, "Khung 15 phút bị thiếu")["count"] >= 2


def test_speeds_checks(tmp_path):
    pd.DataFrame({"link_id": ["10", "20"], "link_name": ["BQE N", "FDR S"], "borough": ["Brooklyn", "Manhattan"],
                  "owner": "", "transcom_id": "", "link_points": ""}).to_csv(tmp_path / "links.csv", index=False)
    t = pd.date_range("2024-01-01", periods=12, freq="5min").strftime("%Y-%m-%dT%H:%M:%S.000")
    rows = [dict(id="1", speed="30.5", travel_time="100", status="0", data_as_of=x, link_id="10",
                 borough="Brooklyn", link_name="BQE N") for x in t]
    rows.append(dict(rows[0]))                                                     # trùng toàn bộ
    rows.append(dict(rows[1], speed="0", travel_time="0", status="-101"))          # bản ghi rỗng + trùng khóa
    rows.append(dict(rows[2], data_as_of="1930-12-09T14:40:47.000", speed="250"))  # sai thời gian + quá nhanh
    rows.append(dict(rows[3], link_id="99"))                                       # tuyến lạ
    rows.append(dict(rows[4], link_id="20", link_name="FDR SOUTH"))                # tên khác danh mục
    pd.DataFrame(rows).to_csv(tmp_path / "speeds_2024-01.csv", index=False)
    res = profile_speeds(tmp_path)
    assert res["rows"] == 17
    assert _by_name(res, "Trùng toàn bộ")["count"] == 1
    assert _by_name(res, "speed = 0 và travel_time = 0")["count"] == 1
    assert _by_name(res, "status khác 0")["count"] == 1
    assert _by_name(res, "ngoài tháng")["count"] == 1
    assert _by_name(res, "speed > 100")["count"] == 1
    assert _by_name(res, "không có trong links.csv")["count"] == 1
    assert _by_name(res, "link_name khác")["count"] == 1
