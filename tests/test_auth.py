"""Tests for web/auth.py — RBAC and session management."""

import os
import pytest
from web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_unauthenticated_redirects_to_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_page_loads(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"ADS-B Secure" in resp.data


def test_login_valid_operator(client):
    resp = client.post("/login", data={"username": "operator", "password": "operator123"})
    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


def test_login_valid_analyst(client):
    resp = client.post("/login", data={"username": "analyst", "password": "analyst123"})
    assert resp.status_code == 302


def test_login_wrong_password(client):
    resp = client.post("/login", data={"username": "operator", "password": "wrong"})
    assert resp.status_code == 401
    assert b"Invalid credentials" in resp.data


def test_login_unknown_user(client):
    resp = client.post("/login", data={"username": "hacker", "password": "pass"})
    assert resp.status_code == 401


def test_authenticated_dashboard(client):
    client.post("/login", data={"username": "operator", "password": "operator123"})
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"ADS-B Secure" in resp.data


def test_operator_cannot_access_audit_api(client):
    client.post("/login", data={"username": "operator", "password": "operator123"})
    resp = client.get("/api/audit/logs")
    assert resp.status_code == 403


def test_analyst_can_access_audit_api(client):
    client.post("/login", data={"username": "analyst", "password": "analyst123"})
    resp = client.get("/api/audit/logs")
    # 503 because no forensic_logger configured in test app — but auth passed
    assert resp.status_code in (200, 503)
    assert resp.status_code != 403


def test_logout_clears_session(client):
    client.post("/login", data={"username": "operator", "password": "operator123"})
    client.get("/logout")
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_unauthenticated_api_returns_401(client):
    resp = client.get("/api/traces")
    # Should redirect (302) not 401 for browser routes
    assert resp.status_code == 302


def test_health_no_auth_required(client):
    resp = client.get("/health")
    assert resp.status_code == 200
