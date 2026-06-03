"""Tests for security/replay_detector.py."""

import time
import pytest
from adsb_secure.normalizer import AirCraftData, TraceStatus
from security.replay_detector import ReplayDetector


def _make_ac(hex="3c4b12", seen=1.0, lat=45.0, lon=9.0) -> AirCraftData:
    return AirCraftData(
        hex=hex, squawk=None, flight=None,
        lat=lat, lon=lon, seen_pos=1.0, altitude=10000,
        vert_rate=0, track=90.0, rssi=-20.0, speed=450.0,
        messages=100, seen=seen, mlat=None,
    )


def test_fresh_packet_not_replay():
    d = ReplayDetector(window_seconds=30)
    ac = _make_ac(seen=1.0)
    result = d.check(ac)
    assert result.replay_detected is False


def test_stale_packet_is_replay():
    d = ReplayDetector(window_seconds=30)
    ac = _make_ac(seen=60.0)  # seen=60s > window=30s
    result = d.check(ac)
    assert result.replay_detected is True
    assert result.status == TraceStatus.SUSPICIOUS


def test_duplicate_packet_is_replay():
    d = ReplayDetector(window_seconds=30)
    ac1 = _make_ac(seen=1.0, lat=45.0, lon=9.0)
    ac2 = _make_ac(seen=1.0, lat=45.0, lon=9.0)  # same fingerprint
    d.check(ac1)
    result = d.check(ac2)
    assert result.replay_detected is True


def test_different_position_not_replay():
    d = ReplayDetector(window_seconds=30)
    ac1 = _make_ac(seen=1.0, lat=45.0, lon=9.0)
    ac2 = _make_ac(seen=1.0, lat=46.0, lon=10.0)  # different position
    d.check(ac1)
    result = d.check(ac2)
    assert result.replay_detected is False


def test_different_icao_not_replay():
    d = ReplayDetector(window_seconds=30)
    ac1 = _make_ac(hex="aaaaaa", seen=1.0)
    ac2 = _make_ac(hex="bbbbbb", seen=1.0)
    d.check(ac1)
    result = d.check(ac2)
    assert result.replay_detected is False


def test_none_icao_skips_dedup():
    d = ReplayDetector(window_seconds=30)
    ac = _make_ac(seen=1.0)
    ac.hex = None
    result = d.check(ac)
    assert result.replay_detected is False  # no key to dedup on


def test_clear_resets_state():
    d = ReplayDetector(window_seconds=30)
    ac = _make_ac(seen=1.0)
    d.check(ac)
    d.clear()
    ac2 = _make_ac(seen=1.0)
    result = d.check(ac2)
    assert result.replay_detected is False  # cleared — not seen before
