"""Smoke tests for web/app.py — Flask routes."""

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


def test_health_returns_200(client):
    c, _ = client
    resp = c.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_api_traces_empty(client):
    c, _ = client
    resp = c.get("/api/traces")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_api_traces_with_data(client):
    c, store = client
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


def test_api_aircraft_not_found(client):
    c, _ = client
    resp = c.get("/api/aircraft/000000")
    assert resp.status_code == 404


def test_api_aircraft_found(client):
    c, store = client
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


def test_dashboard_returns_html(client):
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"ADS-B Secure" in resp.data
