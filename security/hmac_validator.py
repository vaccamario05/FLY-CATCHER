"""
Module: hmac_validator.py
Sprint: 2
Purpose: HMAC-SHA256 integrity verification for ADS-B packets.

PoC SCOPE — operates only on simulated/preprocessed data with a pre-shared key.
This does NOT modify or authenticate the real ADS-B protocol.
Key loaded from env ADSB_HMAC_KEY — never hardcoded.
"""

import hashlib
import hmac
import json
import logging
import os
from typing import Optional

from adsb_secure.normalizer import AirCraftData, TraceStatus

logger = logging.getLogger(__name__)

# Fields included in HMAC computation — order is fixed for determinism
_HMAC_FIELDS = ("hex", "lat", "lon", "altitude", "speed", "track")


def _get_key() -> Optional[bytes]:
    raw = os.environ.get("ADSB_HMAC_KEY", "")
    if not raw:
        return None
    return raw.encode("utf-8")


def _build_payload(aircraft: AirCraftData) -> bytes:
    """Deterministic serialization of HMAC-covered fields."""
    parts = {f: getattr(aircraft, f, None) for f in _HMAC_FIELDS}
    return json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_hmac(aircraft: AirCraftData, key: bytes) -> str:
    """Compute HMAC-SHA256 over critical fields. Returns hex digest."""
    payload = _build_payload(aircraft)
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


class HMACValidator:
    """
    Verifies HMAC tag on AirCraftData objects.

    If ADSB_HMAC_KEY is not set, validation is skipped and
    aircraft.hmac_valid is left as None (unverifiable).

    Usage:
        v = HMACValidator()
        aircraft = v.validate(aircraft, provided_tag)
    """

    def __init__(self):
        self._key = _get_key()
        if self._key is None:
            logger.warning(
                "ADSB_HMAC_KEY not set — HMAC validation disabled (PoC mode)"
            )

    def validate(self, aircraft: AirCraftData, provided_tag: Optional[str]) -> AirCraftData:
        """
        Verify HMAC tag against aircraft fields.
        Sets aircraft.hmac_valid and updates status if failed.
        """
        if self._key is None:
            aircraft.hmac_valid = None  # not verifiable
            return aircraft

        if provided_tag is None:
            aircraft.hmac_valid = False
            aircraft.status = TraceStatus.SUSPICIOUS
            logger.debug("HMAC FAIL hex=%s — no tag provided", aircraft.hex)
            return aircraft

        expected = compute_hmac(aircraft, self._key)

        # Timing-safe comparison
        if hmac.compare_digest(expected, provided_tag):
            aircraft.hmac_valid = True
            logger.debug("HMAC OK hex=%s", aircraft.hex)
        else:
            aircraft.hmac_valid = False
            aircraft.status = TraceStatus.SUSPICIOUS
            logger.info("HMAC FAIL hex=%s — payload tampered", aircraft.hex)

        return aircraft

    def sign(self, aircraft: AirCraftData) -> str:
        """
        Produce HMAC tag for an aircraft record.
        Used by simulator preprocessor to generate signed test data.
        """
        if self._key is None:
            raise RuntimeError("ADSB_HMAC_KEY not set — cannot sign")
        return compute_hmac(aircraft, self._key)
