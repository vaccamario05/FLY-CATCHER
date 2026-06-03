"""Tests for security/validator.py — StructuralValidator."""

import pytest
from security.validator import StructuralValidator
from adsb_secure.normalizer import TraceStatus

validator = StructuralValidator()


def _make(overrides: dict) -> dict:
    base = {
        "hex": "3c4b12",
        "lat": 45.0,
        "lon": 9.0,
        "altitude": 10000,
        "speed": 450,
        "track": 180.0,
        "flight": "AZ1234",
        "rssi": -20.0,
        "messages": 100,
        "seen": 1.0,
        "seen_pos": 1.0,
    }
    base.update(overrides)
    return base


# --- Valid packet ---

def test_valid_packet_accepted():
    ac = validator.validate(_make({}))
    assert ac.structural_valid is True
    assert ac.status == TraceStatus.UNVERIFIED
    assert ac.structural_reasons == []


# --- ICAO checks ---

def test_missing_icao_invalid():
    ac = validator.validate(_make({"hex": None}))
    assert ac.structural_valid is False
    assert ac.status == TraceStatus.INVALID
    assert any("icao" in r for r in ac.structural_reasons)


def test_bad_icao_format_invalid():
    ac = validator.validate(_make({"hex": "ZZZZZZ"}))
    assert ac.structural_valid is False
    assert any("invalid_icao" in r for r in ac.structural_reasons)


def test_short_icao_invalid():
    ac = validator.validate(_make({"hex": "3c4b"}))
    assert ac.structural_valid is False


def test_icao_uppercase_accepted():
    # ICAO hex is case-insensitive
    ac = validator.validate(_make({"hex": "3C4B12"}))
    assert ac.structural_valid is True


# --- lat/lon ---

def test_lat_out_of_range():
    ac = validator.validate(_make({"lat": 200.0}))
    assert ac.structural_valid is False
    assert any("lat_out_of_range" in r for r in ac.structural_reasons)


def test_lon_out_of_range():
    ac = validator.validate(_make({"lon": -200.0}))
    assert ac.structural_valid is False
    assert any("lon_out_of_range" in r for r in ac.structural_reasons)


def test_none_lat_lon_accepted():
    # Position optional — packet may lack position
    ac = validator.validate(_make({"lat": None, "lon": None}))
    assert ac.structural_valid is True
    assert ac.status == TraceStatus.UNVERIFIED


# --- Altitude ---

def test_altitude_too_high():
    ac = validator.validate(_make({"altitude": 150000}))
    assert ac.structural_valid is False
    assert any("altitude_out_of_range" in r for r in ac.structural_reasons)


def test_altitude_too_low():
    ac = validator.validate(_make({"altitude": -9999}))
    assert ac.structural_valid is False


def test_none_altitude_accepted():
    ac = validator.validate(_make({"altitude": None}))
    assert ac.structural_valid is True


# --- Speed ---

def test_speed_too_high():
    ac = validator.validate(_make({"speed": 5000}))
    assert ac.structural_valid is False
    assert any("speed_out_of_range" in r for r in ac.structural_reasons)


def test_speed_zero_accepted():
    ac = validator.validate(_make({"speed": 0}))
    assert ac.structural_valid is True


# --- Track ---

def test_track_out_of_range():
    ac = validator.validate(_make({"track": 400.0}))
    assert ac.structural_valid is False


def test_track_zero_accepted():
    ac = validator.validate(_make({"track": 0.0}))
    assert ac.structural_valid is True


# --- Flight callsign ---

def test_flight_invalid_chars():
    ac = validator.validate(_make({"flight": "AZ!@#$%"}))
    assert ac.structural_valid is False


def test_flight_too_long():
    ac = validator.validate(_make({"flight": "TOOLONGFLIGHT"}))
    assert ac.structural_valid is False


def test_flight_none_accepted():
    ac = validator.validate(_make({"flight": None}))
    assert ac.structural_valid is True


# --- Sample JSON field names (alt_baro / gs / baro_rate) ---

def test_sample_json_fields_accepted():
    raw = {
        "hex": "845f9f",
        "flight": "KZ51    ",
        "alt_baro": 31996,
        "gs": 487.0,
        "track": 244.0,
        "baro_rate": 48,
        "lat": 57.32872,
        "lon": -177.562752,
        "seen_pos": 873.399,
        "messages": 4420465,
        "seen": 803.5,
        "rssi": -29.2,
    }
    ac = validator.validate(raw)
    assert ac.structural_valid is True
    assert ac.altitude == 31996
    assert ac.speed == 487.0


# --- Multiple errors ---

def test_multiple_errors_all_reported():
    ac = validator.validate(_make({"lat": 999, "lon": 999, "altitude": 999999}))
    assert ac.structural_valid is False
    assert len(ac.structural_reasons) >= 3


# --- Build failure ---

def test_empty_dict_invalid():
    ac = validator.validate({})
    assert ac.structural_valid is False
    assert ac.status == TraceStatus.INVALID
