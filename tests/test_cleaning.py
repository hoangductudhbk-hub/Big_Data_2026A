"""Test làm sạch với dữ liệu cài sẵn lỗi đã biết."""
import pandas as pd
import pytest

from data_integration.cleaning.common import CleaningLog, normalize_district, parse_link_points
from data_integration.cleaning.speeds import clean_links, clean_speeds_month, coverage_flags
from data_integration.cleaning.volume import clean_volume
from data_integration.cleaning.weather import clean_weather


def _step(log, text):
    return next(s for s in log.steps if text in s["rule"])


def test_normalize_district():
    s = pd.Series(["queens", " Staten  Island ", "BRONX", "Hanoi"])
    assert list(normalize_district(s).fillna("NA")) == ["Queens", "Staten Island", "Bronx", "NA"]


def test_parse_link_points_drops_truncated_tail():
    assert parse_link_points("40.1,-73.1 40.2,-73.2 40.3,-7") == [(40.1, -73.1), (40.2, -73.2)]
    assert parse_link_points("") == []
    # Chuỗi dài đúng 255 và cặp cuối bị cắt nhưng VẪN đúng định dạng ('-73.12345678901' → '-73.123456789')
    pts = (" ".join(["40.123456,-73.123456"] * 11) + " 40.1234567,-73.12345678901")[:255]
    assert len(pts) == 255 and pts.endswith("40.1234567,-73.123456789")
    parsed = parse_link_points(pts)
    assert len(parsed) == 11 and all(p == (40.123456, -73.123456) for p in parsed)


def test_clean_weather_merges_dst_duplicate():
    raw = pd.DataFrame({
        "station_id": ["S", "S", "S"], "district": ["Queens"] * 3,
        "time_local": ["2024-11-03 00:00:00", "2024-11-03 01:00:00", "2024-11-03 01:00:00"],
        "temperature_2m": ["10", "8", "6"], "precipitation": ["0", "0", "1"], "rain": ["0", "0", "1"],
        "snowfall": ["0", "0", "0"], "weather_code": ["0", "3", "61"],
    })
    df, log = clean_weather(raw)
    assert len(df) == 2
    one = df[df.timestamp == pd.Timestamp("2024-11-03 01:00")].iloc[0]
    assert one.temperature == 7 and one.weather_code == 61 and one.weather_condition == "Rain"
    assert _step(log, "lùi giờ")["affected"] == 2


def test_clean_volume():
    base = dict(requestid="1", boro="queens", yr="2024", m="3", d="7", hh="4", segmentid="55135",
                wktgeom="POINT (1035363.4 185093.4)", street="122  pl", fromst="Dead end", tost="B", direction="SB")
    rows = [dict(base, mm=str(mm), vol=str(v)) for mm, v in [(0, 10), (15, 20), (30, 0), (45, 40)]]
    rows.append(dict(base, requestid="2", mm="45", vol="60"))     # trùng khóa → trung bình 50
    rows.append(dict(base, mm="10", vol="5"))                     # phút lệch → loại
    df, log = clean_volume(pd.DataFrame(rows))
    assert len(df) == 4
    assert df.loc[df.timestamp.dt.minute == 45, "vol"].iloc[0] == 50
    assert df["street"].iloc[0] == "122 PL" and df["fromst"].iloc[0] == "DEAD END"
    assert df["district"].iloc[0] == "Queens"
    assert 40.5 < df["latitude"].iloc[0] < 41 and -74.3 < df["longitude"].iloc[0] < -73.6
    assert bool(df.loc[df.vol == 0, "flag_zero"].iloc[0])


def test_clean_speeds_month():
    base = dict(id="1", speed="30", travel_time="100", status="0", link_id="10",
                borough="Queens", link_name="X")
    rows = [dict(base, data_as_of=f"2024-01-01T00:{m:02d}:00.000") for m in (0, 5, 10, 15)]
    rows.append(dict(base, data_as_of="2024-01-01T00:20:00.000", status="-101", speed="12"))
    rows.append(dict(base, data_as_of="2024-01-01T00:25:00.000", speed="0", travel_time="0"))
    rows.append(dict(base, data_as_of="2024-01-01T00:30:00.000", speed="250"))
    rows.append(dict(rows[0]))                                    # trùng
    log = CleaningLog("speeds")
    out = clean_speeds_month(pd.DataFrame(rows), log)
    assert len(out) == 4 and log.rows_in == 8 and log.rows_out == 4
    assert out["speed_kmh"].iloc[0] == pytest.approx(48.28, abs=0.01)
    assert _step(log, "status = -101")["affected"] == 1
    assert _step(log, "Trùng")["affected"] == 1


def test_clean_links_adds_missing_and_computes_centroid():
    raw = pd.DataFrame({"link_id": ["10"], "link_name": ["bqe n"], "borough": ["Brooklyn"],
                        "owner": [""], "transcom_id": [""], "link_points": ["40.70,-73.90 40.72,-73.92 40.7"]})
    seen = pd.DataFrame({"link_id": ["10", "99"], "link_name": ["BQE N", "NEW"], "borough": ["Brooklyn", "Queens"]})
    links, log = clean_links(raw, seen)
    assert len(links) == 2
    l10 = links[links.link_id == "10"].iloc[0]
    assert l10.link_name == "BQE N" and l10.n_points == 2      # "40.7" cuối bị cắt → bỏ
    assert l10.latitude == pytest.approx(40.71) and l10.longitude == pytest.approx(-73.91)
    assert pd.isna(links[links.link_id == "99"].iloc[0].latitude)


def test_coverage_flags_marks_outage():
    ts = pd.date_range("2024-01-01", "2024-01-03 23:00", freq="h")
    df = pd.DataFrame({"link_id": "10", "timestamp": ts})
    df = df[~df.timestamp.dt.day.eq(2) | df.timestamp.dt.hour.lt(3)]   # ngày 2 chỉ có 3/24 giờ
    cov = coverage_flags(df)
    assert len(cov) == 31                                             # đủ ngày của tháng
    assert list(cov.loc[cov.is_outage, "date"].dt.day)[:2] == [2, 4]  # ngày 2 thiếu, từ ngày 4 không có dữ liệu


def test_to_parquet_us_writes_microseconds(tmp_path):
    import pyarrow.parquet as pq
    from data_integration.cleaning.common import to_parquet_us
    to_parquet_us(pd.DataFrame({"t": pd.to_datetime(["2024-01-01 08:00"])}), tmp_path / "x.parquet")
    assert str(pq.read_schema(tmp_path / "x.parquet").field("t").type) == "timestamp[us]"
