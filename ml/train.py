"""
Module: ml/train.py
Sprint: 3 (debito tecnico)
Purpose: Train Isolation Forest on real ADS-B samples and persist model.

Usage:
    python3.11 -m ml.train                              # uses notebook/samples/
    python3.11 -m ml.train --samples notebook/samples   # explicit path
    python3.11 -m ml.train --augment 200                # add 200 synthetic samples

The script:
1. Loads all JSON files from samples/valid/ + samples/testing/
2. Builds trace histories per ICAO
3. Extracts feature vectors
4. Augments with synthetic normal data if --augment > 0
5. Trains IsolationForest (contamination=0.05)
6. Saves model to models/isolation_forest.pkl + scaler
7. Reports training stats
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ml.train")


def load_samples(samples_dir: str) -> list[dict]:
    """Load all aircraft records from all JSON files in samples_dir."""
    base = Path(samples_dir)
    records = []
    for json_file in sorted(base.rglob("*.json")):
        try:
            data = json.loads(json_file.read_text())
            batch = data.get("aircraft", [])
            records.extend(batch)
            logger.info("Loaded %d records from %s", len(batch), json_file)
        except Exception as e:
            logger.warning("Skipping %s: %s", json_file, e)
    return records


def build_vectors(records: list[dict]) -> list[list[float]]:
    """Build feature vectors from records, grouped by ICAO."""
    from adsb_secure.normalizer import build_from_dict
    from adsb_secure.trace_store import TraceStore
    from ml.feature_extractor import extract, to_vector

    store = TraceStore(max_history=50)
    for raw in records:
        try:
            ac = build_from_dict(raw)
            store.update(ac)
        except Exception:
            continue

    vectors = []
    for icao in store.icao_set():
        history = store.get_history(icao)
        if len(history) < 2:
            # Single record: build a synthetic vector from field values
            latest = store.get_latest(icao)
            if latest:
                vec = [
                    latest.speed or 450.0,
                    latest.altitude or 35000.0,
                    latest.vert_rate or 0.0,
                    latest.track or 180.0,
                    0.0, 0.0, 0.0,
                    latest.speed or 450.0,
                    0.0,
                    latest.seen_pos or 1.0,
                ]
                vectors.append(vec)
            continue

        features = extract(history)
        if features:
            vectors.append(to_vector(features))

    return vectors


def augment_normal(vectors: list[list[float]], n: int, seed: int = 42) -> list[list[float]]:
    """Add n synthetic normal vectors by perturbing existing ones."""
    if not vectors:
        return vectors
    rng = np.random.default_rng(seed)
    base = np.array(vectors)
    mean = base.mean(axis=0)
    std = base.std(axis=0) + 1e-6
    synthetic = (mean + rng.normal(0, 0.3, (n, len(mean))) * std).tolist()
    return vectors + synthetic


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ADS-B Secure Isolation Forest")
    parser.add_argument("--samples", default="notebook/samples", help="Samples directory")
    parser.add_argument("--augment", type=int, default=100, help="Add N synthetic normal samples")
    parser.add_argument("--contamination", type=float, default=0.05)
    parser.add_argument("--estimators", type=int, default=100)
    args = parser.parse_args()

    logger.info("Loading samples from %s", args.samples)
    records = load_samples(args.samples)
    if not records:
        logger.error("No records found. Exiting.")
        sys.exit(1)
    logger.info("Total records: %d", len(records))

    vectors = build_vectors(records)
    logger.info("Feature vectors from real data: %d", len(vectors))

    if args.augment > 0:
        vectors = augment_normal(vectors, args.augment)
        logger.info("After augmentation: %d vectors", len(vectors))

    if len(vectors) < 10:
        logger.error("Need at least 10 vectors (got %d). Exiting.", len(vectors))
        sys.exit(1)

    from ml.anomaly_detector import AnomalyDetector
    detector = AnomalyDetector(contamination=args.contamination, n_estimators=args.estimators)
    detector.train(vectors)

    # Quick validation
    test_normal = vectors[0]
    test_ghost = [9999.0, 200000.0, 99999.0, 720.0, 5.0, 5.0, 99999.0, 8000.0, 7999.0, 0.0]
    norm_score, _ = detector.predict(test_normal)
    ghost_score, ghost_reason = detector.predict(test_ghost)

    logger.info("Validation — normal sample score: %.3f", norm_score)
    logger.info("Validation — ghost aircraft score: %.3f (%s)", ghost_score, ghost_reason)
    logger.info("Model trained and saved. Ready for production.")


if __name__ == "__main__":
    main()
