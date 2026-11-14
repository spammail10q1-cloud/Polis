from __future__ import annotations


def test_metoprolol_simulation_is_explicitly_experimental(demo_client):
    response = demo_client.post(
        "/api/v1/simulations",
        json={"medication_id": "metoprolol", "dose_text": "illustrative input only"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    result = data["result"]
    assert data["status"] in {"partial", "complete"}
    assert result["model"]["status"] == "experimental"
    assert any(metric["key"] == "relative_auc" for metric in result["summary_metrics"])
    assert len(result["curve"]["times"]) > 50
    assert result["curve"]["y_label"].startswith("Relative concentration")
    assert result["evidence"]
    assert result["medication"]["parameter_sources"]
    assert all(parameter.get("source") for parameter in result["medication"]["parameter_sources"])
    assert result["sensitivity"]["drivers"]
    assert result["sensitivity"]["not_causal"] is True
    assert any("reference" in assumption.lower() for assumption in result["assumptions"])
    assert any("No dose calculation" in flag["title"] for flag in result["safety_flags"])
    assert all("× reference" in metric["unit"] or metric["unit"] == "h" for metric in result["summary_metrics"])
    # No absolute concentration or mg-based dose recommendation is returned.
    serialized = str(result)
    assert "ng/mL" not in serialized
    assert "recommended dose" not in serialized.lower()


def test_simulation_is_deterministic_for_same_inputs(demo_client):
    first = demo_client.post("/api/v1/simulations", json={"medication_id": "metoprolol"}).json()
    second = demo_client.post("/api/v1/simulations", json={"medication_id": "metoprolol"}).json()
    metric_a = next(m for m in first["result"]["summary_metrics"] if m["key"] == "relative_auc")
    metric_b = next(m for m in second["result"]["summary_metrics"] if m["key"] == "relative_auc")
    assert metric_a["value"] == metric_b["value"]
    assert first["result"]["uncertainty"]["interval_definition"] == second["result"]["uncertainty"]["interval_definition"]


def test_clopidogrel_uses_pathway_index_and_flags_omeprazole(demo_client):
    response = demo_client.post(
        "/api/v1/simulations",
        json={"medication_id": "clopidogrel", "dose_text": "illustrative input"},
    )
    assert response.status_code == 201, response.text
    result = response.json()["result"]
    assert result["pathway_index"] is not None
    assert result["pathway_index"]["value"] < 1.0
    assert result["curve"] is None
    assert len(result["summary_metrics"]) == 1
    assert result["summary_metrics"][0]["key"] == "pathway_index"
    major = [item for item in result["interactions"] if item["severity"] in {"major", "contraindicated"}]
    assert major
    assert any(item["other_medication"] == "Omeprazole" for item in major)
    assert any("efficacy" in statement.lower() for statement in result["uncertainty"]["statements"])
    assert any("activated" in item.lower() or "activation" in item.lower() for item in result["clinician_questions"])


def test_unsupported_medication_returns_structured_refusal(demo_client):
    response = demo_client.post(
        "/api/v1/simulations",
        json={"medication_id": "azathioprine"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "not_supported"
    result = data["result"]
    assert result["status"] == "not_supported"
    assert result["model"]["used"] is False
    assert "summary_metrics" not in result
    assert "curve" not in result
    assert "pathway_index" not in result
    assert "No simulation" in result["headline"]
    assert result["evidence"]
    assert result["clinician_questions"]
    assert any("specialist" in question.lower() or "bleeding" in question.lower() or "monitor" in question.lower() for question in result["clinician_questions"])


def test_unknown_medication_is_not_simulated(demo_client):
    response = demo_client.post("/api/v1/simulations", json={"medication_name": "Unobtainium"})
    assert response.status_code == 404
    assert "not in the curated formulary" in response.json()["detail"]


def test_allergy_overlap_is_flagged_without_cross_reactivity_claims(demo_client):
    response = demo_client.post("/api/v1/simulations", json={"medication_id": "amoxicillin"})
    assert response.status_code == 201
    result = response.json()["result"]
    assert result["allergy_flags"]
    assert result["allergy_flags"][0]["substance"] == "Penicillin"
    assert any(flag["severity"] == "danger" for flag in result["safety_flags"])
    assert any("cannot determine" in flag["statement"].lower() for flag in result["allergy_flags"])


def test_missing_personal_data_remains_visible(make_account):
    client, _ = make_account("empty-sim")
    response = client.post("/api/v1/simulations", json={"medication_id": "metoprolol"})
    assert response.status_code == 201, response.text
    result = response.json()["result"]
    assert result["synthetic_data"] is False
    assert any("CYP2D6" in item for item in result["missing_information"])
    assert any("eGFR" in item or "renal" in item.lower() for item in result["missing_information"])
    assert any("weight" in item.lower() for item in result["missing_information"])
    assert any("assum" in assumption.lower() for assumption in result["assumptions"])
    assert any(input_item["classification"] == "unknown" for input_item in result["model_inputs"])


def test_simulations_are_tenant_isolated(make_account):
    client_a, _ = make_account("sim-a")
    client_b, _ = make_account("sim-b")
    simulation = client_a.post("/api/v1/simulations", json={"medication_id": "ibuprofen"}).json()
    assert client_b.get(f"/api/v1/simulations/{simulation['id']}").status_code == 404
    assert client_b.get(f"/api/v1/simulations/{simulation['id']}/evidence").status_code == 404
    assert all(item["id"] != simulation["id"] for item in client_b.get("/api/v1/simulations").json())
