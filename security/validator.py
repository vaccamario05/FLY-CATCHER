"""
Module: validator.py
Sprint: 1
Purpose: Structural validation of ADS-B packets before any processing.

All ADS-B input is untrusted. This validator is the first gate.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from adsb_secure.normalizer import AirCraftData, TraceStatus, build_from_dict

logger = logging.getLogger(__name__)

_ICAO_RE = re.compile(r'^[0-9a-fA-F]{6}$')

# Physical aviation constraints
_ALT_MIN_FT = -1500.0
_ALT_MAX_FT = 60000.0
_SPEED_MIN_KT = 0.0
_SPEED_MAX_KT = 1500.0
_LAT_MIN = -90.0
_LAT_MAX = 90.0
_LON_MIN = -180.0
_LON_MAX = 180.0
_FLIGHT_MAX_LEN = 8
_SQUAWK_RE = re.compile(r'^[0-7]{4}$')


@dataclass
class ValidationResult:
    is_valid: bool
    reasons: list = field(default_factory=list)


class StructuralValidator:
    """
    Validates raw ADS-B dict before building AirCraftData.
    Returns (AirCraftData, valid) with status and reasons set.
    """

    def validate(self, raw: dict) -> AirCraftData:
        """
        Build AirCraftData from raw dict and run all structural checks.
        Sets aircraft.structural_valid, aircraft.structural_reasons, aircraft.status.
        Never raises — bad packets get status=INVALID.
        """
        try:
            aircraft = build_from_dict(raw)
        except Exception as e:
            logger.warning("Cannot build AirCraftData from raw: %s", e)
            return AirCraftData(
                hex=None, squawk=None, flight=None, lat=None, lon=None,
                seen_pos=None, altitude=None, vert_rate=None, track=None,
                rssi=None, speed=None, messages=None, seen=None, mlat=None,
                status=TraceStatus.INVALID,
                structural_valid=False,
                structural_reasons=["build_failed: " + str(e)],
            )

        result = self._run_checks(raw, aircraft)
        aircraft.structural_valid = result.is_valid
        aircraft.structural_reasons = result.reasons

        if not result.is_valid:
            aircraft.status = TraceStatus.INVALID
            logger.debug("Packet INVALID hex=%s reasons=%s", aircraft.hex, result.reasons)
        else:
            aircraft.status = TraceStatus.UNVERIFIED  # passes to next layer

        return aircraft

    def _run_checks(self, raw: dict, aircraft: AirCraftData) -> ValidationResult:
        reasons = []

        # ICAO hex — mandatory
        if not aircraft.hex:
            reasons.append("missing_icao")
        elif not _ICAO_RE.match(aircraft.hex):
            reasons.append(f"invalid_icao_format:{aircraft.hex!r}")

        # lat/lon — optional but if present must be in range
        if aircraft.lat is not None:
            if not (_LAT_MIN <= aircraft.lat <= _LAT_MAX):
                reasons.append(f"lat_out_of_range:{aircraft.lat}")

        if aircraft.lon is not None:
            if not (_LON_MIN <= aircraft.lon <= _LON_MAX):
                reasons.append(f"lon_out_of_range:{aircraft.lon}")

        # altitude
        if aircraft.altitude is not None:
            if not (_ALT_MIN_FT <= aircraft.altitude <= _ALT_MAX_FT):
                reasons.append(f"altitude_out_of_range:{aircraft.altitude}")

        # speed
        if aircraft.speed is not None:
            if not (_SPEED_MIN_KT <= aircraft.speed <= _SPEED_MAX_KT):
                reasons.append(f"speed_out_of_range:{aircraft.speed}")

        # track
        if aircraft.track is not None:
            if not (0.0 <= aircraft.track <= 360.0):
                reasons.append(f"track_out_of_range:{aircraft.track}")

        # flight callsign — alphanumeric + spaces only, max 8 chars
        if aircraft.flight is not None:
            stripped = aircraft.flight.strip()
            if len(stripped) > _FLIGHT_MAX_LEN:
                reasons.append(f"flight_too_long:{len(stripped)}")
            if stripped and not re.match(r'^[A-Za-z0-9 ]+$', stripped):
                reasons.append(f"flight_invalid_chars:{stripped!r}")

        # squawk — optional, 4 octal digits if present
        if aircraft.squawk is not None:
            if not _SQUAWK_RE.match(str(aircraft.squawk)):
                reasons.append(f"invalid_squawk:{aircraft.squawk!r}")

        return ValidationResult(is_valid=len(reasons) == 0, reasons=reasons)
