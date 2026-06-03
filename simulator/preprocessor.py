"""
Module: preprocessor.py
Sprint: 3 (debito tecnico)
Purpose: Sign simulated ADS-B records with HMAC tag for end-to-end pipeline testing.

The simulator produces raw dicts without HMAC tags.
This preprocessor adds `_hmac_tag` to each record so the HMACValidator
can verify them in the full pipeline — enabling end-to-end HMAC testing
without real authenticated ADS-B hardware.

PoC SCOPE — this simulates what a trusted ground station would do if
it pre-signed messages before injecting them into the pipeline.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class HMACPreprocessor:
    """
    Wraps a simulator and adds `_hmac_tag` to each record.

    Usage:
        sim = JSONSimulator(file)
        preprocessor = HMACPreprocessor(sim)
        ingestion = DataIngestion(simulator=preprocessor)

    Records without HMAC key set pass through unsigned (tag=None).
    """

    def __init__(self, simulator, tamper_icao: Optional[str] = None):
        """
        :param simulator: upstream simulator with fetch() method
        :param tamper_icao: if set, intentionally corrupt HMAC for this ICAO
                            (for testing tamper detection)
        """
        self._sim = simulator
        self._tamper_icao = tamper_icao
        self._validator = None
        self._init_validator()

    def _init_validator(self) -> None:
        key = os.environ.get("ADSB_HMAC_KEY", "")
        if not key:
            logger.warning("HMACPreprocessor: ADSB_HMAC_KEY not set — records unsigned")
            return
        try:
            from adsb_secure.normalizer import build_from_dict
            from security.hmac_validator import HMACValidator
            self._validator = HMACValidator()
            self._build = build_from_dict
        except Exception as e:
            logger.error("HMACPreprocessor init failed: %s", e)

    def fetch(self) -> list[dict]:
        records = self._sim.fetch()
        if self._validator is None:
            return records

        signed = []
        for raw in records:
            try:
                ac = self._build(raw)
                tag = self._validator.sign(ac)

                # Tamper injection for testing
                if self._tamper_icao and raw.get("hex") == self._tamper_icao:
                    tag = "00" * 32  # corrupt tag
                    logger.debug("Injected tampered tag for %s", self._tamper_icao)

                raw = dict(raw)  # copy — don't mutate original
                raw["_hmac_tag"] = tag
            except Exception as e:
                logger.warning("Could not sign record %s: %s", raw.get("hex"), e)
            signed.append(raw)
        return signed
