from __future__ import annotations


def test_digital_twin_has_ten_systems_and_honest_statuses(demo_client):
    response = demo_client.get("/api/v1/twin")
    assert response.status_code == 200
    data = response.json()
    assert len(data["systems"]) == 10
    assert 0 < data["overall_completeness"] < 100
    assert "not a scan" in data["disclaimer"].lower()
    statuses = {system["id"]: system["status"] for system in data["systems"]}
    assert statuses["liver"] == "review"
    assert statuses["lungs"] == "partial"
    assert all(status in {"available", "review", "partial", "missing", "experimental"} for status in statuses.values())
    assert all("diseased" not in system["status_reason"].lower() for system in data["systems"])


def test_twin_system_detail_and_unknown_system(demo_client):
    response = demo_client.get("/api/v1/twin/systems/liver")
    assert response.status_code == 200
    data = response.json()
    assert data["description"]
    assert data["measurements_detail"]
    assert any(measurement["code"] == "alt" for measurement in data["measurements_detail"])
    assert data["genetic_factors"]
    assert any("do not measure total liver function" in limitation.lower() for limitation in data["limitations"])
    assert demo_client.get("/api/v1/twin/systems/unknown").status_code == 404


def test_completeness_is_not_a_health_score(demo_client):
    response = demo_client.get("/api/v1/twin/completeness")
    assert response.status_code == 200
    data = response.json()
    assert data["not_a_health_score"] is True
    assert "nothing about health status" in data["note"].lower()


def test_wearables_are_labelled_device_estimates(demo_client):
    response = demo_client.get("/api/v1/wearables")
    assert response.status_code == 200
    data = response.json()
    assert data["devices"]
    assert all(device["is_synthetic"] for device in data["devices"])
    assert data["metrics"]
    assert all(metric["quality"] == "device_estimate" for metric in data["metrics"])
    series = demo_client.get("/api/v1/wearables/series", params={"metric": "sleep_duration", "days": 14}).json()
    assert 1 <= len(series["points"]) <= 15
    assert "not laboratory" in series["data_quality_note"].lower()
    assert series["points"][0]["is_synthetic"] is True


def test_wearable_integrations_are_not_claimed_operational(demo_client):
    data = demo_client.get("/api/v1/wearables/integrations").json()
    assert data["operational"] is False
    assert any(item["status"] == "sample_data_only" for item in data["integrations"])
    assert any(item["provider"] == "apple_health" for item in data["integrations"])


def test_overview_has_no_fabricated_health_score(demo_client):
    data = demo_client.get("/api/v1/overview").json()
    assert "twin" in data
    assert data["data_status"]["not_a_health_score"] is True
    assert "Demonstration data" in data["synthetic_notice"]
    assert len(data["insights"]) >= 5
    assert len(data["active_medications"]) >= 5
    assert all("sources" in insight for insight in data["insights"])


def test_model_registry_is_explicitly_not_clinically_validated(demo_client):
    response = demo_client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["models"]
    assert all(model["clinically_validated"] is False for model in data["models"])
    assert any(model["status"] == "experimental" for model in data["models"])
    assert "No model" in data["validation_policy"]


def test_wearable_csv_import_is_explicitly_user_supplied(make_account):
    from datetime import UTC, datetime, timedelta

    client, _ = make_account("wearable-import")
    day = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%d")
    csv_content = (
        "metric,value,unit,date,source\n"
        f"sleep_duration,7.2,h,{day},My device export\n"
        f"hrv,48,ms,{day},My device export\n"
        f"steps,9100,steps,{day},My device export\n"
    )
    response = client.post(
        "/api/v1/wearables/import",
        files={"file": ("wearables.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["imported"] == 3
    assert data["device"]["connection_status"] == "manual_import"
    assert "not laboratory" in data["notice"]
    series = client.get("/api/v1/wearables/series", params={"metric": "sleep_duration", "days": 30}).json()
    assert len(series["points"]) == 1
    assert series["points"][0]["is_synthetic"] is False

    duplicate = client.post(
        "/api/v1/wearables/import",
        files={"file": ("wearables-again.csv", csv_content.encode(), "text/csv")},
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["imported"] == 0
    assert duplicate.json()["skipped"] == 3


def test_wearable_import_rejects_unknown_metric_and_bad_unit(make_account):
    from datetime import UTC, datetime, timedelta

    client, _ = make_account("wearable-bad")
    day = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    csv_content = (
        "metric,value,unit,date\n"
        f"mood,7,score,{day}\n"
        f"hrv,45,bananas,{day}\n"
        f"resting_hr,58,bpm,{day}\n"
    )
    response = client.post(
        "/api/v1/wearables/import",
        files={"file": ("bad.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["imported"] == 1
    assert len(data["errors"]) == 2
    assert any("unsupported metric" in error for error in data["errors"])
    assert any("unit" in error for error in data["errors"])


def test_wearable_import_is_tenant_isolated(make_account):
    from datetime import UTC, datetime, timedelta

    client_a, _ = make_account("wear-a")
    client_b, _ = make_account("wear-b")
    day = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    content = f"metric,value,unit,date\nhrv,44,ms,{day}\n"
    client_a.post("/api/v1/wearables/import", files={"file": ("a.csv", content.encode(), "text/csv")})
    assert client_b.get("/api/v1/wearables/series", params={"metric": "hrv", "days": 30}).json()["points"] == []
    assert client_a.get("/api/v1/wearables/series", params={"metric": "hrv", "days": 30}).json()["points"]
