from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta


def iso_days_ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def test_manual_lab_trend_and_range(make_account):
    client, _ = make_account("labs")
    payload = {
        "code": "alt",
        "value": 48,
        "unit": "U/L",
        "measured_at": iso_days_ago(10),
        "ref_low": 7,
        "ref_high": 35,
        "ref_text": "7-35",
        "source": "Test Lab",
    }
    created = client.post("/api/v1/labs/manual", json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["range_status"] == "high"
    assert body["ref_high"] == 35

    payload["value"] = 32
    payload["measured_at"] = iso_days_ago(2)
    client.post("/api/v1/labs/manual", json=payload)
    trends = client.get("/api/v1/labs/trends").json()
    alt = next(item for item in trends if item["code"] == "alt")
    assert len(alt["points"]) == 2
    assert alt["absolute_change"] == -16
    assert "increased" not in alt["interpretation"].lower() or "decreased" in alt["interpretation"].lower()


def test_unit_conversion_is_explicit(make_account):
    client, _ = make_account("units")
    response = client.post(
        "/api/v1/labs/manual",
        json={
            "code": "glucose",
            "value": 5.4,
            "unit": "mmol/L",
            "measured_at": iso_days_ago(1),
            "ref_low": 3.9,
            "ref_high": 5.6,
            "source": "Test Lab",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["unit"] == "mg/dL"
    assert abs(body["value"] - 97.2983) < 0.01
    assert abs(body["ref_low"] - 70.271) < 0.001
    assert body["converted_from"] == "mmol/L"

    indeterminate = client.post(
        "/api/v1/labs/manual",
        json={
            "code": "bilirubin",
            "value": 1.1,
            "unit": "mg/dL",
            "measured_at": iso_days_ago(1),
            "source": "Test Lab",
        },
    )
    assert indeterminate.status_code == 201
    assert indeterminate.json()["range_status"] == "indeterminate"


def test_unsupported_unit_and_future_date_rejected(make_account):
    client, _ = make_account("invalidlabs")
    response = client.post(
        "/api/v1/labs/manual",
        json={
            "code": "creatinine",
            "value": 1,
            "unit": "furlongs",
            "measured_at": iso_days_ago(1),
        },
    )
    assert response.status_code == 422
    assert "not supported" in response.json()["detail"]

    future = client.post(
        "/api/v1/labs/manual",
        json={
            "code": "alt",
            "value": 20,
            "unit": "U/L",
            "measured_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        },
    )
    assert future.status_code == 422

    bad_range = client.post(
        "/api/v1/labs/manual",
        json={
            "code": "alt",
            "value": 20,
            "unit": "U/L",
            "measured_at": iso_days_ago(1),
            "ref_low": 40,
            "ref_high": 10,
        },
    )
    assert bad_range.status_code == 422


def test_csv_import_and_review_flags(make_account):
    client, _ = make_account("csv")
    csv_content = (
        "code,value,unit,date,ref_low,ref_high,source\n"
        f"ALT,48,U/L,{datetime.now(UTC).date().isoformat()},7,35,CSV Lab\n"
        f"LDL,118,mg/dL,{datetime.now(UTC).date().isoformat()},,100,CSV Lab\n"
    )
    response = client.post(
        "/api/v1/labs/upload",
        files={"file": ("panel.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 2
    codes = {item["code"] for item in body["results"]}
    assert codes == {"alt", "ldl"}
    labs = client.get("/api/v1/labs?latest_only=true").json()
    assert all(item["quality_status"] == "unverified_import" for item in labs)


def test_csv_without_units_is_rejected(make_account):
    client, _ = make_account("csvbad")
    csv_content = f"code,value,date\nALT,48,{datetime.now(UTC).date().isoformat()}\n"
    response = client.post(
        "/api/v1/labs/upload",
        files={"file": ("panel.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 422
    assert "unit" in json.dumps(response.json()).lower()


def test_fhir_observation_import(make_account):
    client, _ = make_account("fhir")
    date = datetime.now(UTC).replace(microsecond=0).isoformat()
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "alt", "display": "Alanine aminotransferase"}]},
                    "subject": {"reference": "Patient/self"},
                    "effectiveDateTime": date,
                    "valueQuantity": {"value": 41, "unit": "U/L"},
                    "referenceRange": [{"low": {"value": 7, "unit": "U/L"}, "high": {"value": 35, "unit": "U/L"}}],
                }
            }
        ],
    }
    response = client.post(
        "/api/v1/labs/upload",
        files={"file": ("observations.json", json.dumps(bundle).encode(), "application/json")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 1
    assert response.json()["results"][0]["range_status"] == "high"


def test_lab_results_are_tenant_isolated(make_account):
    client_a, _ = make_account("twin-a")
    client_b, _ = make_account("twin-b")
    created = client_a.post(
        "/api/v1/labs/manual",
        json={
            "code": "alt",
            "value": 77,
            "unit": "U/L",
            "measured_at": iso_days_ago(2),
            "ref_low": 7,
            "ref_high": 35,
            "source": "A only lab",
        },
    ).json()
    assert client_b.get("/api/v1/labs").json() == []
    assert client_b.delete(f"/api/v1/labs/{created['id']}").status_code == 404
    a_labs = client_a.get("/api/v1/labs").json()
    assert any(item["value"] == 77 for item in a_labs)
    assert all(item["value"] != 77 for item in client_b.get("/api/v1/labs").json())
