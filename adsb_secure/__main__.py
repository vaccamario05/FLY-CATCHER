"""
Entrypoint: python -m adsb_secure

Sprint 2: acquisition → rate_limit → validate → hmac → replay → classify → store → log → Flask
"""

import argparse
import json
import logging
import os
import threading
import time
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("adsb_secure")


def run_pipeline(acquisition, rate_limiter, validator, hmac_validator,
                 replay_detector, classifier, trace_store, forensic_logger,
                 interval: float = 5.0, anomaly_detector=None,
                 heartbeat: Optional[list] = None) -> None:
    from security.forensic_logger import SecurityEvent, EventType, Severity

    logger.info("Pipeline started (interval=%.1fs)", interval)
    while True:
        raw_records = acquisition.fetch()
        accepted = dropped = 0

        for raw in raw_records:
            # 1 — Rate limit
            if not rate_limiter.allow():
                dropped += 1
                forensic_logger.log(SecurityEvent(
                    event_type=EventType.RATE_LIMIT_EXCEEDED,
                    severity=Severity.MEDIUM,
                    details={"stats": rate_limiter.stats},
                ))
                continue

            # 2 — Structural validation
            aircraft = validator.validate(raw)
            if not aircraft.structural_valid:
                forensic_logger.log(SecurityEvent(
                    event_type=EventType.PACKET_INVALID,
                    severity=Severity.LOW,
                    icao=aircraft.hex,
                    details={"reasons": aircraft.structural_reasons},
                ))
                continue

            # 3 — HMAC (PoC — tag from raw dict if present)
            hmac_tag = raw.get("_hmac_tag")
            aircraft = hmac_validator.validate(aircraft, hmac_tag)
            if aircraft.hmac_valid is False:
                forensic_logger.log(SecurityEvent(
                    event_type=EventType.HMAC_FAIL,
                    severity=Severity.HIGH,
                    icao=aircraft.hex,
                    details={},
                ))

            # 4 — Replay detection
            aircraft = replay_detector.check(aircraft)
            if aircraft.replay_detected:
                forensic_logger.log(SecurityEvent(
                    event_type=EventType.REPLAY_DETECTED,
                    severity=Severity.HIGH,
                    icao=aircraft.hex,
                    details={"seen": aircraft.seen},
                ))

            # 5 — Kinematic anomaly detection (ghost aircraft / trajectory tampering)
            if anomaly_detector is not None and aircraft.hex:
                history = trace_store.get_history(aircraft.hex) + [aircraft]
                aircraft = anomaly_detector.annotate(aircraft, history)
                if aircraft.anomaly_score is not None and aircraft.anomaly_score > 0.7:
                    forensic_logger.log(SecurityEvent(
                        event_type=EventType.ANOMALY_DETECTED,
                        severity=Severity.HIGH,
                        icao=aircraft.hex,
                        details={"score": aircraft.anomaly_score, "reason": aircraft.anomaly_reason},
                    ))

            # 6 — Final classification
            aircraft = classifier(aircraft)

            # 7 — Store
            trace_store.update(aircraft)
            accepted += 1

            if aircraft.status.value == "suspicious":
                forensic_logger.log(SecurityEvent(
                    event_type=EventType.PACKET_ACCEPTED,
                    severity=Severity.MEDIUM,
                    icao=aircraft.hex,
                    details={"status": aircraft.status.value},
                ))

        if heartbeat is not None:
            heartbeat[0] = time.time()

        logger.info(
            "Cycle done: %d fetched, %d accepted, %d rate-dropped → %d traces",
            len(raw_records), accepted, dropped, len(trace_store),
        )
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="ADS-B Secure — Sprint 2")
    parser.add_argument("--mode", choices=["live", "simulator"], default="simulator")
    parser.add_argument(
        "--file",
        default=os.path.join(
            os.path.dirname(__file__),
            "..", "notebook", "samples", "testing", "sample.json",
        ),
    )
    parser.add_argument("--url", default=os.environ.get("DUMP1090_URL", "http://localhost:8080/data/aircraft.json"))
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    from adsb_secure.acquisition import DataIngestion
    from adsb_secure.trace_store import TraceStore
    from security.validator import StructuralValidator
    from security.hmac_validator import HMACValidator
    from security.replay_detector import ReplayDetector
    from security.rate_limiter import TokenBucketRateLimiter
    from security.classifier import classify
    from security.forensic_logger import ForensicLogger
    from ml.anomaly_detector import AnomalyDetector
    from web.app import create_app

    trace_store = TraceStore()
    validator = StructuralValidator()
    hmac_validator = HMACValidator()
    rate_limiter = TokenBucketRateLimiter()
    forensic_logger = ForensicLogger()
    anomaly_detector = AnomalyDetector()
    if not anomaly_detector.is_trained:
        logger.warning("Anomaly model not trained/found — ghost/anomaly detection disabled this run")

    if args.mode == "simulator":
        from simulator.replay import JSONSimulator
        from simulator.preprocessor import HMACPreprocessor
        sim = JSONSimulator(args.file, loop=True)
        # Sign records with HMAC tag if key is set
        signed_sim = HMACPreprocessor(sim)
        acquisition = DataIngestion(simulator=signed_sim)
        # In simulator mode: skip stale check (historical 'seen' values are large)
        # Only use deduplication check to detect same record sent twice
        replay_detector = ReplayDetector(check_stale=False)
        logger.info("Mode: simulator (%s) — stale check disabled", args.file)
    else:
        headers = {}
        raw_headers = os.environ.get("ADSB_HTTP_HEADERS")
        if raw_headers:
            try:
                headers = json.loads(raw_headers)
            except json.JSONDecodeError:
                logger.warning("ADSB_HTTP_HEADERS is not valid JSON — ignoring")
        acquisition = DataIngestion(url=args.url, headers=headers)
        replay_detector = ReplayDetector()  # full check in live mode
        logger.info("Mode: live (%s)%s", args.url, " [authenticated feed]" if headers else "")

    heartbeat = [time.time()]

    def _pipeline_supervisor():
        while True:
            try:
                run_pipeline(
                    acquisition, rate_limiter, validator, hmac_validator,
                    replay_detector, classify, trace_store, forensic_logger,
                    args.interval, anomaly_detector=anomaly_detector, heartbeat=heartbeat,
                )
            except Exception:
                logger.exception("Pipeline crashed — restarting in %.1fs", args.interval)
                time.sleep(args.interval)

    pipeline_thread = threading.Thread(target=_pipeline_supervisor, daemon=True)
    pipeline_thread.start()

    flask_app = create_app(
        trace_store=trace_store, forensic_logger=forensic_logger, heartbeat=heartbeat,
        pipeline_interval=args.interval, rate_limiter=rate_limiter, replay_detector=replay_detector,
    )
    logger.info("Dashboard at http://localhost:%d", args.port)
    flask_app.run(host="0.0.0.0", port=args.port, debug=False)  # nosec B104


if __name__ == "__main__":
    main()
