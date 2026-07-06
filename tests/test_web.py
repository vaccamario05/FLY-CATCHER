"""Smoke tests for web/app.py — Flask routes (Sprint 2+: auth required)."""

import pytest
from web.app import create_app, _build_alerts
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


# --- Supervisor role ---

@pytest.fixture
def supervisor_client(client):
    """Client pre-authenticated as supervisor."""
    c, store = client
    c.post("/login", data={"username": "supervisor", "password": "supervisor123"})
    return c, store


def test_supervisor_can_view_dashboard(supervisor_client):
    c, _ = supervisor_client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"ADS-B Secure" in resp.data


def test_supervisor_can_view_traces(supervisor_client):
    c, _ = supervisor_client
    resp = c.get("/api/traces")
    assert resp.status_code == 200


def test_supervisor_forbidden_from_audit(supervisor_client):
    c, _ = supervisor_client
    resp = c.get("/api/audit/logs")
    assert resp.status_code == 403


def test_supervisor_forbidden_from_export(supervisor_client):
    c, _ = supervisor_client
    resp = c.get("/api/export/csv")
    assert resp.status_code == 403


# --- Analyst events page ---

def test_analyst_events_page(analyst_client):
    c, _ = analyst_client
    resp = c.get("/analyst/events")
    assert resp.status_code == 200
    assert b"Security Events" in resp.data


def test_operator_forbidden_from_events_page(auth_client):
    c, _ = auth_client
    resp = c.get("/analyst/events")
    assert resp.status_code == 403


# --- PDF export ---

def test_analyst_pdf_export_no_logger(analyst_client):
    c, _ = analyst_client
    resp = c.get("/api/export/pdf")
    assert resp.status_code == 503


def test_operator_forbidden_from_pdf_export(auth_client):
    c, _ = auth_client
    resp = c.get("/api/export/pdf")
    assert resp.status_code == 403


# --- Alert panel (_build_alerts) ---

def _make_trace(hex_id, status, reasons=None, anomaly_reason=None, anomaly_score=None):
    ac = AirCraftData(
        hex=hex_id, squawk=None, flight=None,
        lat=45.0, lon=9.0, seen_pos=None, altitude=10000,
        vert_rate=None, track=None, rssi=None, speed=None,
        messages=None, seen=None, mlat=None,
        status=status,
        structural_reasons=reasons or [],
        anomaly_reason=anomaly_reason,
        anomaly_score=anomaly_score,
    )
    return ac


def test_build_alerts_suspicious_included():
    traces = [_make_trace("aabbcc", TraceStatus.SUSPICIOUS, reasons=["speed_exceeded"])]
    alerts = _build_alerts(traces)
    assert len(alerts) == 1
    assert alerts[0]["icao"] == "aabbcc"
    assert alerts[0]["severity"] == "medium"


def test_build_alerts_invalid_included():
    traces = [_make_trace("112233", TraceStatus.INVALID, reasons=["invalid_icao"])]
    alerts = _build_alerts(traces)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "high"


def test_build_alerts_valid_excluded():
    traces = [_make_trace("ffffff", TraceStatus.VALID)]
    alerts = _build_alerts(traces)
    assert alerts == []


def test_build_alerts_anomaly_reason_included():
    traces = [_make_trace("aabbcc", TraceStatus.SUSPICIOUS,
                          anomaly_reason="impossible speed delta", anomaly_score=-0.15)]
    alerts = _build_alerts(traces)
    assert "impossible speed delta" in alerts[0]["reasons"]
