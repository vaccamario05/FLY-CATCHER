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
