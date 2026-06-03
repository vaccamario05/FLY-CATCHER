"""Smoke tests for web/app.py — Flask routes (Sprint 2: auth required)."""

import pytest
from web.app import create_app
from adsb_secure.trace_store import TraceStore
from adsb_secure.normalizer import AirCraftData, TraceStatus


@pytest.fixture
def client():
    store = TraceStore()
    app = create_app(trace_store=store)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, store


@pytest.fixture
def auth_client(client):
    """Client pre-authenticated as operator."""
    c, store = client
    c.post("/login", data={"username": "operator", "password": "operator123"})
    return c, store


@pytest.fixture
def analyst_client(client):
    """Client pre-authenticated as analyst."""
    c, store = client
    c.post("/login", data={"username": "analyst", "password": "analyst123"})
    return c, store


# --- Public routes ---

def test_health_returns_200(client):
    c, _ = client
    resp = c.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_unauthenticated_redirects(client):
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 302
    assert "login" in resp.headers["Location"]


# --- Protected routes (operator) ---

def test_api_traces_empty(auth_client):
    c, _ = auth_client
    resp = c.get("/api/traces")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_api_traces_with_data(auth_client):
    c, store = auth_client
    ac = AirCraftData(
        hex="aabbcc", squawk=None, flight="TEST01",
        lat=45.0, lon=9.0, seen_pos=1.0, altitude=10000,
        vert_rate=0, track=90.0, rssi=-20.0, speed=450.0,
        messages=100, seen=1.0, mlat=None,
        status=TraceStatus.VALID,
    )
    store.update(ac)
    resp = c.get("/api/traces")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["hex"] == "aabbcc"
    assert data[0]["status"] == "valid"


def test_api_aircraft_not_found(auth_client):
    c, _ = auth_client
    resp = c.get("/api/aircraft/000000")
    assert resp.status_code == 404


def test_api_aircraft_found(auth_client):
    c, store = auth_client
    ac = AirCraftData(
        hex="123abc", squawk=None, flight=None,
        lat=10.0, lon=20.0, seen_pos=None, altitude=5000,
        vert_rate=None, track=None, rssi=None, speed=None,
        messages=None, seen=None, mlat=None,
        status=TraceStatus.SUSPICIOUS,
    )
    store.update(ac)
    resp = c.get("/api/aircraft/123abc")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["icao"] == "123abc"
    assert data["latest"]["status"] == "suspicious"


def test_dashboard_returns_html(auth_client):
    c, _ = auth_client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"ADS-B Secure" in resp.data


# --- RBAC ---

def test_operator_forbidden_from_audit(auth_client):
    c, _ = auth_client
    resp = c.get("/api/audit/logs")
    assert resp.status_code == 403


def test_analyst_allowed_audit(analyst_client):
    c, _ = analyst_client
    resp = c.get("/api/audit/logs")
    # 503 = no forensic_logger configured, but auth passed
    assert resp.status_code in (200, 503)
    assert resp.status_code != 403


def test_analyst_chain_verify(analyst_client):
    c, _ = analyst_client
    resp = c.get("/api/audit/verify")
    assert resp.status_code in (200, 503)
    assert resp.status_code != 403
