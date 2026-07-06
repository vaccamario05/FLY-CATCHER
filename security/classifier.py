"""
Module: classifier.py
Sprint: 2
Purpose: Aggregate validation results into final TraceStatus.

Decision logic:
  INVALID   — structural validation failed
  SUSPICIOUS — HMAC failed OR replay detected OR anomaly detected (Sprint 3)
  VALID     — all checks passed (structural ok + hmac ok + no replay)
  UNVERIFIED — structural ok but HMAC not available (key not set)
"""

from adsb_secure.normalizer import AirCraftData, TraceStatus
from ml import anomaly_detector as _anomaly_detector_module


def classify(aircraft: AirCraftData) -> AirCraftData:
    """
    Set final status on aircraft based on accumulated check results.
    Call this after all validators have run.
    Fail-safe: any uncertainty → UNVERIFIED, never VALID.
    """
    # Already marked INVALID by structural validator
    if not aircraft.structural_valid:
        aircraft.status = TraceStatus.INVALID
        return aircraft

    # Any hard failure → SUSPICIOUS
    if aircraft.replay_detected:
        aircraft.status = TraceStatus.SUSPICIOUS
        return aircraft

    if aircraft.hmac_valid is False:
        aircraft.status = TraceStatus.SUSPICIOUS
        return aircraft

    # Sprint 3: anomaly score threshold — read live from ml.anomaly_detector so
    # a runtime threshold change (analyst config) actually takes effect here,
    # instead of this module keeping its own stale hardcoded value.
    if (aircraft.anomaly_score is not None
            and aircraft.anomaly_score > _anomaly_detector_module._ANOMALY_THRESHOLD):
        aircraft.status = TraceStatus.SUSPICIOUS
        return aircraft

    # HMAC key not configured → cannot verify → UNVERIFIED
    if aircraft.hmac_valid is None:
        aircraft.status = TraceStatus.UNVERIFIED
        return aircraft

    # All checks passed
    aircraft.status = TraceStatus.VALID
    return aircraft
