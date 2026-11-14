from __future__ import annotations


def test_causal_catalog_is_explicitly_experimental(demo_client):
    data = demo_client.get("/api/v1/causal/catalog").json()
    assert {treatment["code"] for treatment in data["treatments"]} == {"sleep_duration", "steps"}
    assert data["minimum_days"] == 14
    assert data["evidence_class"] == "experimental_hypothesis"
    assert "not" in data["disclaimer"].lower()


def test_causal_sleep_hrv_query_returns_assumption_bearing_estimate(demo_client):
    response = demo_client.post(
        "/api/v1/causal/simulate",
        json={"treatment": "sleep_duration", "outcome": "hrv", "delta": 0.5},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "complete"
    assert data["available_days"] >= 14
    assert data["estimate"]["low"] <= data["estimate"]["value"] <= data["estimate"]["high"]
    assert data["model"]["evidence_class"] == "experimental_hypothesis"
    assert data["not_causal_proof"] is True
    assert data["dag"]["nodes"] and data["dag"]["edges"]
    assert data["assumptions"] and data["limitations"] and data["alternative_explanations"]
    assert any("unmeasured" in assumption.lower() for assumption in data["assumptions"])
    assert data["evidence"]
    assert data["evidence"][0]["id"] == "cdc-sleep"


def test_causal_steps_resting_hr(demo_client):
    response = demo_client.post(
        "/api/v1/causal/simulate",
        json={"treatment": "steps", "outcome": "resting_hr", "delta": 1000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["estimate"]["unit"] == "bpm"
    assert data["treatment"]["code"] == "steps"


def test_causal_rejects_invalid_requests(demo_client):
    invalid_treatment = demo_client.post(
        "/api/v1/causal/simulate",
        json={"treatment": "sleep_duration", "outcome": "hrv", "delta": 20},
    )
    assert invalid_treatment.status_code == 422
    invalid_pair = demo_client.post(
        "/api/v1/causal/simulate",
        json={"treatment": "steps", "outcome": "hrv", "delta": 100000},
    )
    assert invalid_pair.status_code == 422
    bad_schema = demo_client.post(
        "/api/v1/causal/simulate",
        json={"treatment": "alcohol", "outcome": "hrv", "delta": 1},
    )
    assert bad_schema.status_code == 422


def test_causal_insufficient_data_is_a_successful_structured_outcome(make_account):
    client, _ = make_account("causal-empty", ai_processing=True)
    response = client.post(
        "/api/v1/causal/simulate",
        json={"treatment": "sleep_duration", "outcome": "hrv", "delta": 0.5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_data"
    assert data["available_days"] < 14
    assert data["missing_information"]
    assert data["disclaimer"]
