"""Tests for ml/feature_extractor.py."""

import math
import time
import pytest
from adsb_secure.normalizer import AirCraftData
from ml.feature_extractor import extract, to_vector, _haversine_nm


def _make_ac(lat, lon, alt=10000.0, speed=450.0, track=90.0, vert_rate=0.0, dt_offset=0) -> AirCraftData:
    ac = AirCraftData(
        hex="aabbcc", squawk=None, flight=None,
        lat=lat, lon=lon, seen_pos=1.0, altitude=alt,
        vert_rate=vert_rate, track=track, rssi=-20.0, speed=speed,
        messages=100, seen=1.0, mlat=None,
    )
    ac.received_at = time.time() + dt_offset
    return ac


def test_extract_requires_two_records():
    history = [_make_ac(45.0, 9.0)]
    assert extract(history) is None


def test_extract_returns_dict():
    h = [_make_ac(45.0, 9.0, dt_offset=0), _make_ac(45.01, 9.01, dt_offset=5)]
    features = extract(h)
    assert isinstance(features, dict)
    assert "speed_kt" in features
    assert "delta_lat" in features


def test_extract_position_jump_detected():
    # 5 degree jump in 5 seconds — physically impossible
    h = [_make_ac(45.0, 9.0, dt_offset=0), _make_ac(50.0, 14.0, dt_offset=5)]
    features = extract(h)
    assert features is not None
    # speed_discrepancy should be huge
    assert features["speed_discrepancy"] > 1000


def test_extract_normal_aircraft():
    # ~0.005 deg/s at 450kt is realistic
    h = [_make_ac(45.0, 9.0, speed=450.0, dt_offset=0),
         _make_ac(45.01, 9.02, speed=450.0, dt_offset=10)]
    features = extract(h)
    assert features is not None
    # computed speed should be in ballpark of reported
    assert features["computed_speed_kt"] < 2000


def test_extract_missing_position():
    h = [_make_ac(None, None, dt_offset=0), _make_ac(45.0, 9.0, dt_offset=5)]
    h[0].lat = None
    h[0].lon = None
    assert extract(h) is None


def test_to_vector_length():
    h = [_make_ac(45.0, 9.0, dt_offset=0), _make_ac(45.01, 9.01, dt_offset=5)]
    features = extract(h)
    v = to_vector(features)
    assert len(v) == 10


def test_to_vector_all_floats():
    h = [_make_ac(45.0, 9.0, dt_offset=0), _make_ac(45.01, 9.01, dt_offset=5)]
    v = to_vector(extract(h))
    assert all(isinstance(x, float) for x in v)


def test_haversine_known_distance():
    # Naples (40.85, 14.27) to Rome FCO (41.80, 12.25) ~101nm
    dist = _haversine_nm(40.85, 14.27, 41.80, 12.25)
    assert 90 < dist < 115
