from tests.conftest import pg_only


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"
    r = client.get("/api/v1/health/db").json()
    assert r["status"] == "ok"


def test_roads(client):
    r = client.get("/api/v1/roads", params={"district": "Brooklyn"}).json()
    assert r["total"] == 2
    d = client.get("/api/v1/roads/L1").json()
    assert d["stats"]["n_speed"] == 48 and d["stats"]["anomalies"] == 1
    assert client.get("/api/v1/roads/NOPE").status_code == 404


def test_create_road_validation(client):
    bad = client.post("/api/v1/roads", json={"road_id": "X9", "road_name": "A", "district": "Paris",
                                             "latitude": 40.7, "longitude": -73.9})
    assert bad.status_code == 422 and bad.json()["error"]["type"] == "validation_error"
    out = client.post("/api/v1/roads", json={"road_id": "X9", "road_name": "A", "district": "Queens",
                                             "latitude": 40.0, "longitude": -73.9})
    assert out.status_code == 422          # ngoài khung tọa độ New York
    ok = client.post("/api/v1/roads", json={"road_id": "X9", "road_name": "A", "district": "Queens",
                                            "latitude": 40.7, "longitude": -73.9})
    assert ok.status_code == 201
    assert client.post("/api/v1/roads", json={"road_id": "X9", "road_name": "A", "district": "Queens",
                                              "latitude": 40.7, "longitude": -73.9}).status_code == 409


def test_traffic_list_filter_paginate(client):
    r = client.get("/api/v1/traffic", params={"road_id": "L2", "start": "2024-03-02", "page_size": 5}).json()
    assert r["total"] == 24 and len(r["items"]) == 5
    assert r["items"][0]["timestamp"] == "2024-03-02T00:00:00"
    first = client.get(f"/api/v1/traffic/{r['items'][0]['id']}").json()
    assert first["road_id"] == "L2" and set(first) >= {"vehicle_count", "avg_speed", "weather_condition", "source"}
    assert client.get("/api/v1/traffic/999999").status_code == 404


def test_errors_are_uniform(client):
    r = client.get("/api/v1/traffic", params={"page_size": 100000})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"].endswith("page_size")
    r = client.get("/api/v1/traffic", params={"start": "2024-03-02", "end": "2024-03-01"})
    assert r.status_code == 400 and "start" in r.json()["error"]["message"]


def test_weather(client):
    assert client.get("/api/v1/weather", params={"district": "Brooklyn"}).json()["total"] == 48
    assert len(client.get("/api/v1/weather/stations").json()) == 2


def test_statistics(client):
    r = client.get("/api/v1/statistics", params={"dimension": "district"}).json()
    assert r[0]["group_key"] == "Brooklyn" and r[0]["median"] == 54.0
    assert client.get("/api/v1/statistics", params={"dimension": "xyz"}).status_code == 400
    dims = {d["dimension"] for d in client.get("/api/v1/statistics/dimensions").json()}
    assert dims == {"district", "hour"}
    s = client.get("/api/v1/statistics/summary").json()
    assert s["records"] == 144 and s["anomalies"] == 2 and s["roads"] == 3
    assert len(client.get("/api/v1/statistics/daily").json()) == 1
    assert client.get("/api/v1/statistics/weather-impact").json()[0]["controlled_month_change_pct"] == -4.6


def test_live_statistics_match_sql(client):
    r = client.get("/api/v1/statistics/live", params={"group_by": "district", "metric": "vehicle_count"}).json()
    by = {x["group_key"]: x for x in r}
    assert by["Brooklyn"]["n"] == 48 and by["Staten Island"]["n"] == 48


@pg_only
def test_postgres_only_features(client):
    r = client.get("/api/v1/statistics/live", params={"group_by": "hour"}).json()
    assert len(r) == 24 and r[0]["median"] is not None and r[0]["std"] is not None
    ts = client.get("/api/v1/traffic/timeseries", params={"bucket": "day"}).json()
    assert [p["n"] for p in ts] == [72, 72]


def test_anomalies(client):
    r = client.get("/api/v1/anomalies").json()
    assert r["total"] == 2 and abs(r["items"][0]["z_score"]) == 13.0       # sắp theo |z| giảm dần
    assert client.get("/api/v1/anomalies", params={"metric": "avg_speed"}).json()["total"] == 1
    assert client.get("/api/v1/anomalies", params={"min_abs_z": 10}).json()["total"] == 1
    s = client.get("/api/v1/anomalies/summary").json()
    assert s["total"] == 2 and s["top_roads"][0]["road_id"] == "L1"
    assert client.get("/api/v1/anomalies/daily").json()[0]["slow_anomalies"] == 1
