from __future__ import annotations

import uuid


def test_health_and_api_root(app_client):
    assert app_client.get("/health").json()["status"] == "ok"
    root = app_client.get("/api/v1").json()
    assert "not a medical device" in root["notice"].lower()


def test_register_login_me_logout(make_account):
    client, user_id = make_account("auth")
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["id"] == user_id
    assert me.json()["user"]["created_at"].endswith(("+00:00", "Z"))
    consent = me.json()["consent"]
    assert consent["terms_accepted"] is True
    assert consent["ai_processing"] is False

    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": me.json()["user"]["email"], "password": "StrongPass123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == user_id


def test_duplicate_email_rejected(make_account, app_client):
    client, _ = make_account("dup")
    email = client.get("/api/v1/auth/me").json()["user"]["email"]
    other = app_client
    response = other.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "name": "Duplicate",
            "accept_terms": True,
        },
    )
    assert response.status_code == 409


def test_weak_password_and_missing_terms_rejected(app_client):
    weak = app_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"weak-{uuid.uuid4().hex[:6]}@example.com",
            "password": "short",
            "name": "Weak",
            "accept_terms": True,
        },
    )
    assert weak.status_code == 422
    no_terms = app_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"terms-{uuid.uuid4().hex[:6]}@example.com",
            "password": "StrongPass123",
            "name": "No Terms",
            "accept_terms": False,
        },
    )
    assert no_terms.status_code == 422


def test_wrong_password_rejected(app_client, make_account):
    client, _ = make_account("wrongpass")
    email = client.get("/api/v1/auth/me").json()["user"]["email"]
    response = app_client.post(
        "/api/v1/auth/login", json={"email": email, "password": "DefinitelyWrong123"}
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_unauthenticated_endpoints_blocked(app_client):
    for path in ["/api/v1/overview", "/api/v1/labs", "/api/v1/genetics", "/api/v1/twin"]:
        assert app_client.get(path).status_code == 401
    assert app_client.post("/api/v1/simulations", json={"medication_id": "metoprolol"}).status_code == 401


def test_profile_update_and_validation(make_account):
    client, _ = make_account("profile")
    response = client.patch(
        "/api/v1/profile",
        json={
            "date_of_birth": "1990-04-02",
            "sex_at_birth": "female",
            "height_cm": 165,
            "weight_kg": 62,
            "conditions": [{"name": "Asthma", "diagnosed_year": 2001, "status": "active"}],
            "allergies": [{"substance": "Penicillin", "severity": "moderate"}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["height_cm"] == 165
    assert response.json()["conditions"][0]["name"] == "Asthma"
    invalid = client.patch("/api/v1/profile", json={"height_cm": 5})
    assert invalid.status_code == 422
    invalid_dob = client.patch("/api/v1/profile", json={"date_of_birth": "3000-01-01"})
    assert invalid_dob.status_code == 422


def test_cookie_mutations_reject_cross_site_origin(make_account):
    client, _ = make_account("csrf")
    payload = {
        "code": "alt",
        "value": 22,
        "unit": "U/L",
        "measured_at": "2026-01-01T10:00:00Z",
        "ref_low": 7,
        "ref_high": 35,
    }
    blocked = client.post("/api/v1/labs/manual", json=payload, headers={"Origin": "https://evil.example"})
    assert blocked.status_code == 403
    allowed = client.post("/api/v1/labs/manual", json=payload, headers={"Origin": "http://localhost:3000"})
    assert allowed.status_code == 201
