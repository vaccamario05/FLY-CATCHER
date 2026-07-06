"""
Module: acquisition.py
Sprint: 1
Purpose: Fetch raw ADS-B JSON from dump1090-compatible HTTP API or simulator.

Returns raw dicts — no parsing or validation here.

Compatible with:
  - dump1090 ("aircraft" key)
  - readsb-based feeds such as ADS-B Exchange or airplanes.live ("ac" key) —
    same per-record field names (hex, alt_baro, gs, baro_rate, ...), already
    handled by normalizer.build_from_dict.
  - OpenSky Network ("states" key, positional arrays, metric units, no API
    key needed for anonymous/rate-limited access) — converted to the same
    dump1090-style dict schema by _opensky_state_to_dict() below.
"""

import json
import logging
import os
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_URL = os.environ.get(
    "DUMP1090_URL", "http://localhost:8080/data/aircraft.json"
)

_M_TO_FT = 3.28084
_MS_TO_KT = 1.94384
_MS_TO_FPM = 196.850


def _opensky_state_to_dict(state: list) -> dict:
    """
    Map an OpenSky /api/states/all state vector to a dump1090-style dict.

    OpenSky field order (documented, stable):
      0 icao24, 1 callsign, 2 origin_country, 3 time_position, 4 last_contact,
      5 longitude, 6 latitude, 7 baro_altitude(m), 8 on_ground, 9 velocity(m/s),
      10 true_track, 11 vertical_rate(m/s), 12 sensors, 13 geo_altitude(m),
      14 squawk, 15 spi, 16 position_source
    """
    import time as _time

    last_contact = state[4]
    return {
        "hex": state[0],
        "flight": (state[1] or "").strip() or None,
        "lat": state[6],
        "lon": state[5],
        "alt_baro": state[7] * _M_TO_FT if state[7] is not None else None,
        "gs": state[9] * _MS_TO_KT if state[9] is not None else None,
        "track": state[10],
        "baro_rate": state[11] * _MS_TO_FPM if state[11] is not None else None,
        "squawk": state[14],
        "seen": (_time.time() - last_contact) if last_contact else None,
        "seen_pos": (_time.time() - last_contact) if last_contact else None,
        "messages": 1,
    }


class DataIngestion:
    """
    Fetch raw aircraft records from a dump1090/readsb-compatible HTTP API or
    a simulator source.

    Usage:
        ingestion = DataIngestion()
        for raw_dict in ingestion.fetch():
            ...

        # Authenticated external feed (e.g. ADS-B Exchange via RapidAPI):
        ingestion = DataIngestion(
            url="https://adsbexchange-com1.p.rapidapi.com/v2/lat/.../lon/.../dist/...",
            headers={"X-RapidAPI-Key": "...", "X-RapidAPI-Host": "adsbexchange-com1.p.rapidapi.com"},
        )
    """

    def __init__(self, url: str = _DEFAULT_URL, simulator=None, headers: dict = None):
        """
        :param url: dump1090/readsb-compatible HTTP URL
        :param simulator: optional simulator object with a fetch() method.
                         If set, reads from simulator instead of HTTP.
        :param headers: optional HTTP headers (e.g. API key) for external feeds.
        """
        self.url = url
        self.simulator = simulator
        self.headers = headers or {}

    def fetch(self) -> list[dict]:
        """
        Return list of raw aircraft dicts. Never raises.
        Returns empty list on failure.
        """
        if self.simulator is not None:
            return self._fetch_from_simulator()
        return self._fetch_from_http()

    @staticmethod
    def _validate_url(url: str) -> None:
        """Reject non-HTTP schemes to prevent file:// or custom scheme abuse."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Disallowed URL scheme: {parsed.scheme!r}")

    def _fetch_from_http(self) -> list[dict]:
        try:
            self._validate_url(self.url)
            req = urlopen(Request(self.url, headers=self.headers), timeout=5)  # nosec B310
            raw = req.read()
            data = json.loads(raw.decode("utf-8"))
            if "states" in data:
                # OpenSky Network — positional arrays, metric units, needs conversion.
                records = [_opensky_state_to_dict(s) for s in (data.get("states") or []) if s]
            else:
                # dump1090 uses "aircraft", readsb-based feeds (ADS-B Exchange,
                # airplanes.live) use "ac" — same per-record schema either way.
                records = data.get("aircraft") or data.get("ac") or []
            logger.debug("Fetched %d records from %s", len(records), self.url)
            return records
        except URLError as e:
            logger.warning("ADS-B source unreachable (%s): %s", self.url, e)
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Malformed ADS-B source response: %s", e)
            return []
        except ValueError as e:
            logger.error("Rejected ADS-B source URL: %s", e)
            return []

    def _fetch_from_simulator(self) -> list[dict]:
        try:
            return list(self.simulator.fetch())
        except Exception as e:
            logger.error("Simulator fetch failed: %s", e)
            return []
