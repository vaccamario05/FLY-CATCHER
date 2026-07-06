"""Tests for adsb_secure/acquisition.py — dump1090 and readsb-compatible feeds."""

import json
from unittest.mock import patch, MagicMock

from adsb_secure.acquisition import DataIngestion


def _fake_response(payload: dict):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__ = lambda self: self
    resp.__exit__ = lambda self, *a: None
    return resp


def test_fetch_dump1090_aircraft_key():
    with patch("adsb_secure.acquisition.urlopen", return_value=_fake_response({"aircraft": [{"hex": "aabbcc"}]})):
        ingestion = DataIngestion(url="http://localhost:8080/data/aircraft.json")
        records = ingestion.fetch()
    assert records == [{"hex": "aabbcc"}]


def test_fetch_readsb_ac_key():
    """ADS-B Exchange / airplanes.live use 'ac' instead of 'aircraft'."""
    with patch("adsb_secure.acquisition.urlopen", return_value=_fake_response({"ac": [{"hex": "ddeeff"}], "now": 123})):
        ingestion = DataIngestion(url="https://adsbexchange-com1.p.rapidapi.com/v2/whatever")
        records = ingestion.fetch()
    assert records == [{"hex": "ddeeff"}]


def test_fetch_missing_key_returns_empty():
    with patch("adsb_secure.acquisition.urlopen", return_value=_fake_response({"unexpected": []})):
        ingestion = DataIngestion(url="http://localhost:8080/data/aircraft.json")
        records = ingestion.fetch()
    assert records == []


def test_headers_passed_to_request():
    captured = {}

    def fake_urlopen(req, timeout=5):
        captured["headers"] = dict(req.header_items())
        return _fake_response({"ac": []})

    with patch("adsb_secure.acquisition.urlopen", side_effect=fake_urlopen):
        ingestion = DataIngestion(
            url="https://adsbexchange-com1.p.rapidapi.com/v2/whatever",
            headers={"X-Rapidapi-Key": "secret123"},
        )
        ingestion.fetch()

    # urllib.Request normalizes header key casing (X-Rapidapi-key)
    assert captured["headers"].get("X-rapidapi-key") == "secret123"


def test_no_headers_by_default():
    ingestion = DataIngestion(url="http://localhost:8080/data/aircraft.json")
    assert ingestion.headers == {}


def test_disallowed_scheme_rejected():
    ingestion = DataIngestion(url="file:///etc/passwd")
    records = ingestion.fetch()
    assert records == []


def test_fetch_opensky_states_converted():
    """OpenSky uses positional 'states' arrays in metric units — must convert
    to the dump1090-style dict schema (feet/knots/fpm) normalizer expects."""
    state = [
        "44083b", "EJU82AQ ", "Austria", 1783354419, 1783354423,
        14.2521, 40.9897, 3000.0, False, 100.0, 59.0, -5.0,
        None, 3100.0, "1000", False, 0,
    ]
    with patch("adsb_secure.acquisition.urlopen", return_value=_fake_response({"time": 123, "states": [state]})):
        ingestion = DataIngestion(url="https://opensky-network.org/api/states/all?lamin=40&lomin=13&lamax=41&lomax=15")
        records = ingestion.fetch()

    assert len(records) == 1
    rec = records[0]
    assert rec["hex"] == "44083b"
    assert rec["flight"] == "EJU82AQ"
    assert rec["lat"] == 40.9897
    assert rec["lon"] == 14.2521
    assert rec["squawk"] == "1000"
    # unit conversions: 3000m -> ~9843ft, 100 m/s -> ~194kt
    assert abs(rec["alt_baro"] - 9842.5) < 1.0
    assert abs(rec["gs"] - 194.384) < 0.5
    assert rec["baro_rate"] < 0  # descending


def test_fetch_opensky_skips_null_states():
    with patch("adsb_secure.acquisition.urlopen", return_value=_fake_response({"time": 123, "states": [None, None]})):
        ingestion = DataIngestion(url="https://opensky-network.org/api/states/all?lamin=40&lomin=13&lamax=41&lomax=15")
        records = ingestion.fetch()
    assert records == []


def test_fetch_opensky_handles_missing_optional_fields():
    """callsign/altitude/velocity/vertical_rate/squawk can legitimately be null."""
    state = ["44083b", None, "Austria", None, None, 14.25, 40.98, None, False, None, None, None, None, None, None, False, 0]
    with patch("adsb_secure.acquisition.urlopen", return_value=_fake_response({"time": 123, "states": [state]})):
        ingestion = DataIngestion(url="https://opensky-network.org/api/states/all?lamin=40&lomin=13&lamax=41&lomax=15")
        records = ingestion.fetch()
    assert len(records) == 1
    assert records[0]["flight"] is None
    assert records[0]["alt_baro"] is None
    assert records[0]["seen"] is None
