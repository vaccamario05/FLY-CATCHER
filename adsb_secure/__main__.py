"""
Entrypoint: python -m adsb_secure

Wires pipeline (acquisition → validation → trace_store) with Flask dashboard.
Sprint 1: simulator mode only (no auth, no ML, no forensic logging).
"""

import argparse
import logging
import os
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("adsb_secure")


def run_pipeline(acquisition, validator, trace_store, interval: float = 5.0) -> None:
    """Background thread: fetch → validate → store, every `interval` seconds."""
    logger.info("Pipeline started (interval=%.1fs)", interval)
    while True:
        raw_records = acquisition.fetch()
        logger.debug("Fetched %d raw records", len(raw_records))
        for raw in raw_records:
            aircraft = validator.validate(raw)
            trace_store.update(aircraft)
        logger.info(
            "Cycle done: %d records → %d traces tracked",
            len(raw_records), len(trace_store),
        )
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="ADS-B Secure — Sprint 1")
    parser.add_argument(
        "--mode", choices=["live", "simulator"], default="simulator",
        help="Data source mode",
    )
    parser.add_argument(
        "--file",
        default=os.path.join(
            os.path.dirname(__file__),
            "..", "notebook", "samples", "testing", "sample.json"
        ),
        help="JSON file for simulator mode",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("DUMP1090_URL", "http://localhost:8080/data/aircraft.json"),
        help="dump1090 URL for live mode",
    )
    parser.add_argument("--port", type=int, default=5000, help="Flask port")
    parser.add_argument("--interval", type=float, default=5.0, help="Pipeline interval (s)")
    args = parser.parse_args()

    from adsb_secure.acquisition import DataIngestion
    from adsb_secure.trace_store import TraceStore
    from security.validator import StructuralValidator
    from web.app import create_app

    trace_store = TraceStore()
    validator = StructuralValidator()

    if args.mode == "simulator":
        from simulator.replay import JSONSimulator
        sim = JSONSimulator(args.file, loop=True)
        acquisition = DataIngestion(simulator=sim)
        logger.info("Mode: simulator (%s)", args.file)
    else:
        acquisition = DataIngestion(url=args.url)
        logger.info("Mode: live (%s)", args.url)

    # Pipeline in background thread
    pipeline_thread = threading.Thread(
        target=run_pipeline,
        args=(acquisition, validator, trace_store, args.interval),
        daemon=True,
    )
    pipeline_thread.start()

    # Flask in foreground
    flask_app = create_app(trace_store=trace_store)
    logger.info("Dashboard at http://localhost:%d", args.port)
    flask_app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
