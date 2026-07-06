"""
Module: acquisition.py
Sprint: 1
Purpose: Fetch raw ADS-B JSON from dump1090-compatible HTTP API or simulator.

Returns raw dicts — no parsing or validation here.

Compatible with dump1090 ("aircraft" key) and readsb-based feeds such as
ADS-B Exchange or airplanes.live ("ac" key) — both use the same per-record
field names (hex, alt_baro, gs, baro_rate, ...), already handled by
normalizer.build_from_dict.
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
