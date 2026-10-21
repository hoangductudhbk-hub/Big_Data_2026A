def test_import_traffic_partial(client):
    rows = [
        {"road_id": "L1", "timestamp": "2024-03-05T08:00:00", "avg_speed": 30.5},                 # đường có sẵn
        {"road_id": "S77", "road_name": "NEW ROAD", "district": "Queens", "latitude": 40.7, "longitude": -73.8,
         "timestamp": "2024-03-05T08:00:00", "vehicle_count": 500},                               # đường mới
        {"road_id": "L1", "timestamp": "2024-03-05T08:30:00", "avg_speed": 30},                   # không đầu giờ
        {"road_id": "L1", "timestamp": "2024-03-05T09:00:00", "avg_speed": 500},                  # vượt contract
        {"road_id": "ZZ", "timestamp": "2024-03-05T09:00:00", "avg_speed": 20},                   # đường lạ, thiếu info
        {"road_id": "L1", "timestamp": "2024-03-05T10:00:00"},                                    # không có số đo
        {"road_id": "L1", "timestamp": "không phải ngày"},                                        # sai kiểu
    ]
    r = client.post("/api/v1/import/traffic", json=rows)
    assert r.status_code == 200, r.text
    b = r.json()
    assert (b["received"], b["inserted"], b["updated"], b["rejected"]) == (7, 2, 0, 5)
    assert b["status"] == "partial" and b["new_roads"] == ["S77"]
    assert [x["row"] for x in b["rejected_rows"]] == [3, 4, 5, 6, 7]
    assert "đầu giờ" in b["rejected_rows"][0]["errors"][0]
    assert client.get("/api/v1/roads/S77").json()["has_volume"] is True
    rec = client.get("/api/v1/traffic", params={"road_id": "L1", "start": "2024-03-05"}).json()["items"][0]
    assert rec["road_name"] == "BROOKLYN QUEENS EXPRESSWAY" and rec["source"] == "speeds"   # tự bổ sung từ danh mục


def test_import_upsert_is_idempotent(client):
    row = [{"road_id": "L2", "timestamp": "2024-03-06T08:00:00", "avg_speed": 50.0, "vehicle_count": 300}]
    a = client.post("/api/v1/import/traffic", json=row).json()
    b = client.post("/api/v1/import/traffic", json=[{**row[0], "avg_speed": 55.0}]).json()
    assert (a["inserted"], b["inserted"], b["updated"]) == (1, 0, 1)
    items = client.get("/api/v1/traffic", params={"road_id": "L2", "start": "2024-03-06"}).json()["items"]
    assert len(items) == 1 and items[0]["avg_speed"] == 55.0 and items[0]["source"] == "speeds+volume"


def test_import_timezone_is_converted(client):
    r = client.post("/api/v1/import/traffic",
                    json=[{"road_id": "L2", "timestamp": "2024-07-01T12:00:00Z", "avg_speed": 70}]).json()
    assert r["inserted"] == 1
    items = client.get("/api/v1/traffic", params={"road_id": "L2", "start": "2024-07-01"}).json()["items"]
    assert items[0]["timestamp"] == "2024-07-01T08:00:00"        # 12:00 UTC = 08:00 New York (EDT)


def test_import_all_or_nothing(client):
    rows = [{"road_id": "L1", "timestamp": "2024-03-07T08:00:00", "avg_speed": 30},
            {"road_id": "L1", "timestamp": "2024-03-07T09:00:00", "avg_speed": -1}]
    r = client.post("/api/v1/import/traffic", params={"all_or_nothing": True}, json=rows)
    assert r.status_code == 422 and r.json()["error"]["details"]["rejected"] == 1
    assert client.get("/api/v1/traffic", params={"road_id": "L1", "start": "2024-03-07"}).json()["total"] == 0


def test_import_duplicate_in_batch(client):
    rows = [{"road_id": "L1", "timestamp": "2024-03-08T08:00:00", "avg_speed": 30},
            {"road_id": "L1", "timestamp": "2024-03-08T08:00:00", "avg_speed": 31}]
    b = client.post("/api/v1/import/traffic", json=rows).json()
    assert b["inserted"] == 1 and b["rejected_rows"][0]["row"] == 2


def test_import_traffic_csv_file(client):
    csv = ("road_id,timestamp,avg_speed,vehicle_count\n"
           "L2,2024-03-09T08:00:00,61.5,420\n"
           "L2,2024-03-09T09:00:00,abc,\n")
    r = client.post("/api/v1/import/traffic/file", files={"file": ("x.csv", csv, "text/csv")}).json()
    assert r["inserted"] == 1 and r["rejected"] == 1
    bad = client.post("/api/v1/import/traffic/file", files={"file": ("x.xlsx", b"123", "application/octet-stream")})
    assert bad.status_code == 400


def test_import_weather(client):
    rows = [{"station_id": "OM_QUEENS", "district": "Queens", "timestamp": "2024-03-01T00:00:00",
             "temperature": 3.0, "rainfall": 0.5, "weather_condition": "Drizzle"},
            {"station_id": "OM_QUEENS", "timestamp": "2024-03-01T01:00:00", "rainfall": -2},
            {"station_id": "OM_QUEENS", "timestamp": "2024-03-01T02:00:00", "weather_condition": "Tornado"}]
    b = client.post("/api/v1/import/weather", json=rows).json()
    assert (b["inserted"], b["rejected"]) == (1, 2)


def test_import_logs_and_spark_reload(client):
    r = client.post("/api/v1/import/spark-results")
    assert r.status_code == 200 and r.json()["tables"]["anomalies"] == 2
    logs = client.get("/api/v1/import/logs", params={"page_size": 100}).json()
    assert logs["total"] > 0 and {"partial", "ok", "failed"} & {x["status"] for x in logs["items"]}
