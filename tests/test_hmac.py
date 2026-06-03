"""Tests for security/hmac_validator.py."""

import os
import pytest
from adsb_secure.normalizer import AirCraftData, TraceStatus

# Set key before import so HMACValidator picks it up
TEST_KEY = "deadbeef" * 8
os.environ["ADSB_HMAC_KEY"] = TEST_KEY

from security.hmac_validator import HMACValidator, compute_hmac


def _make_ac(**kw) -> AirCraftData:
    defaults = dict(
        hex="3c4b12", squawk=None, flight="TST001",
        lat=45.0, lon=9.0, seen_pos=1.0, altitude=10000,
        vert_rate=0, track=90.0, rssi=-20.0, speed=450.0,
        messages=100, seen=1.0, mlat=None,
    )
    defaults.update(kw)
    return AirCraftData(**defaults)


def test_hmac_valid_tag_accepted():
    v = HMACValidator()
    ac = _make_ac()
    tag = v.sign(ac)
    result = v.validate(ac, tag)
    assert result.hmac_valid is True
    assert result.status != TraceStatus.SUSPICIOUS


def test_hmac_tampered_payload_rejected():
    v = HMACValidator()
    ac = _make_ac()
    tag = v.sign(ac)
    # tamper altitude after signing
    ac.altitude = 99999.0
    result = v.validate(ac, tag)
    assert result.hmac_valid is False
    assert result.status == TraceStatus.SUSPICIOUS


def test_hmac_wrong_tag_rejected():
    v = HMACValidator()
    ac = _make_ac()
    result = v.validate(ac, "00" * 32)
    assert result.hmac_valid is False
    assert result.status == TraceStatus.SUSPICIOUS


def test_hmac_no_tag_rejected():
    v = HMACValidator()
    ac = _make_ac()
    result = v.validate(ac, None)
    assert result.hmac_valid is False
    assert result.status == TraceStatus.SUSPICIOUS


def test_hmac_no_key_skips_validation():
    original = os.environ.pop("ADSB_HMAC_KEY", None)
    try:
        v = HMACValidator()
        ac = _make_ac()
        result = v.validate(ac, None)
        assert result.hmac_valid is None  # not verifiable
    finally:
        if original:
            os.environ["ADSB_HMAC_KEY"] = original


def test_hmac_sign_requires_key():
    original = os.environ.pop("ADSB_HMAC_KEY", None)
    try:
        v = HMACValidator()
        ac = _make_ac()
        with pytest.raises(RuntimeError):
            v.sign(ac)
    finally:
        if original:
            os.environ["ADSB_HMAC_KEY"] = original


def test_hmac_different_icao_different_tag():
    v = HMACValidator()
    ac1 = _make_ac(hex="aaaaaa")
    ac2 = _make_ac(hex="bbbbbb")
    assert v.sign(ac1) != v.sign(ac2)


def test_hmac_compare_digest_not_equal():
    """Ensure we use compare_digest (timing-safe), not ==."""
    import inspect
    import security.hmac_validator as mod
    src = inspect.getsource(mod)
    assert "compare_digest" in src
    assert "== provided_tag" not in src
