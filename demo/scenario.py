"""
Module: demo/scenario.py
Purpose: Inject a fixed set of scripted anomalous aircraft into the simulator
feed every cycle, so every classification path (INVALID, HMAC fail, replay,
ML anomaly) is visibly active without running demo/inject_attack.py in a
separate terminal.

Wraps a JSONSimulator — real sample aircraft pass through unchanged.
"""

import logging

logger = logging.getLogger(__name__)

# ICAO used for the deliberately HMAC-tampered record — pass this to
# HMACPreprocessor(tamper_icao=...) so its signed tag gets corrupted.
HMAC_TAMPER_ICAO = "445566"

_BASE_RECORD = {
    "squawk": "1200", "vert_rate": 0, "rssi": -20.0, "messages": 1,
}


class DemoScenarioSimulator:
    """
    Wraps a simulator and appends scripted records to every fetch() cycle:

      GHOST01 — malformed ICAO, fails structural validation      -> INVALID
      abc123  — altitude out of physical range                   -> INVALID
      def456  — position alternates between two distant points   -> SUSPICIOUS (anomaly)
      112233  — identical (hex, seen, lat, lon) every cycle       -> SUSPICIOUS (replay)
      445566  — structurally fine, tag corrupted upstream         -> SUSPICIOUS (hmac_fail)
                (pair with HMACPreprocessor(tamper_icao=HMAC_TAMPER_ICAO))
    """

    def __init__(self, simulator):
        self._sim = simulator
        self._cycle = 0

    def fetch(self) -> list[dict]:
        records = list(self._sim.fetch())
        self._cycle += 1

        records.append({
            **_BASE_RECORD,
            "hex": "GHOST01",  # not 6 hex chars -> fails ICAO regex
            "flight": "GHOST01",
            "lat": 45.0, "lon": 9.0, "alt_baro": 35000, "gs": 450,
            "track": 90, "seen": 1.0, "seen_pos": 1.0,
        })

        records.append({
            **_BASE_RECORD,
            "hex": "abc123",
            "flight": "IMPOSS1",
            "lat": 45.1, "lon": 9.1, "alt_baro": 99000,  # > 60000ft max
            "gs": 450, "track": 90, "seen": 1.0, "seen_pos": 1.0,
        })

        # Tiny per-cycle jitter on 'seen' keeps these two from *also* tripping
        # replay detection (identical hex/seen/lat/lon = replay by design) —
        # each demo aircraft should demonstrate exactly one classification path.
        jitter = self._cycle * 0.001

        toggle = self._cycle % 2
        records.append({
            **_BASE_RECORD,
            "hex": "def456",
            "flight": "GHOST02",
            "lat": 45.0 if toggle == 0 else 52.0,
            "lon": 9.0 if toggle == 0 else 20.0,
            "alt_baro": 36000, "gs": 480, "track": 90,
            "seen": 1.0 + jitter, "seen_pos": 1.0,
        })

        records.append({
            **_BASE_RECORD,
            "hex": "112233",
            "flight": "REPLAY1",
            "lat": 44.5, "lon": 8.5, "alt_baro": 34000, "gs": 460,
            "track": 90, "seen": 5.0, "seen_pos": 5.0,  # frozen every cycle, on purpose
        })

        records.append({
            **_BASE_RECORD,
            "hex": HMAC_TAMPER_ICAO,
            "flight": "TAMPER1",
            "lat": 44.0, "lon": 8.0, "alt_baro": 33000, "gs": 440,
            "track": 90, "seen": 1.0 + jitter, "seen_pos": 1.0,
        })

        return records
