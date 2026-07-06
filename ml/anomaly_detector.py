"""
Module: anomaly_detector.py
Sprint: 3
Purpose: Isolation Forest anomaly detector for ADS-B traces.

Trained on legitimate samples from notebook/samples/.
Classifies traces as normal or anomalous based on kinematic features.
Model persisted to disk via joblib (sklearn-recommended serialization).
"""

import logging
import os
from pathlib import Path
from typing import Optional

import joblib  # sklearn-recommended — avoids pickle security issues (Bandit B301/B403)

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from adsb_secure.normalizer import AirCraftData, TraceStatus
from ml.feature_extractor import extract, to_vector

logger = logging.getLogger(__name__)

_MODEL_PATH = os.environ.get("IF_MODEL_PATH", "models/isolation_forest.pkl")
_SCALER_PATH = os.environ.get("IF_SCALER_PATH", "models/isolation_forest_scaler.pkl")
_ANOMALY_THRESHOLD = float(os.environ.get("IF_THRESHOLD", "0.7"))


class AnomalyDetector:
    """
    Isolation Forest wrapper for ADS-B trace anomaly detection.

    Usage:
        detector = AnomalyDetector()
        detector.train(training_vectors)      # list[list[float]]
        score, reason = detector.predict(feature_vector)
        aircraft = detector.annotate(aircraft, history)
    """

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self._model: Optional[IsolationForest] = None
        self._scaler: Optional[StandardScaler] = None
        self._trained = False

        # Try loading persisted model
        self._try_load()

    @property
    def is_trained(self) -> bool:
        return self._trained

    def _try_load(self) -> None:
        try:
            if Path(_MODEL_PATH).exists() and Path(_SCALER_PATH).exists():
                self._model = joblib.load(_MODEL_PATH)
                self._scaler = joblib.load(_SCALER_PATH)
                self._trained = True
                logger.info("Loaded IF model from %s", _MODEL_PATH)
        except Exception as e:
            logger.warning("Could not load IF model: %s", e)

    def train(self, vectors: list[list[float]]) -> None:
        """Train IF on a list of feature vectors."""
        if len(vectors) < 10:
            raise ValueError(f"Need at least 10 training samples, got {len(vectors)}")
        X = np.array(vectors)
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)
        self._model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=42,
        )
        self._model.fit(X_scaled)
        self._trained = True
        logger.info("IF trained on %d samples", len(vectors))
        self._save()

    def _save(self) -> None:
        Path(_MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, _MODEL_PATH)
        joblib.dump(self._scaler, _SCALER_PATH)
        logger.info("IF model saved to %s", _MODEL_PATH)

    def predict(self, vector: list[float]) -> tuple[float, str]:
        """
        Predict anomaly score for a feature vector.
        Returns (score 0-1, reason string).
        score > _ANOMALY_THRESHOLD → anomalous.
        """
        if not self._trained:
            return 0.0, "model_not_trained"

        X = np.array([vector])
        X_scaled = self._scaler.transform(X)

        # decision_function: negative = more anomalous
        raw_score = self._model.decision_function(X_scaled)[0]
        # Normalize to [0, 1] — lower raw_score = higher anomaly
        # IF scores typically in [-0.5, 0.5]
        normalized = max(0.0, min(1.0, 0.5 - raw_score))

        reason = self._explain(vector, normalized)
        return normalized, reason

    def _explain(self, vector: list[float], score: float) -> str:
        """Simple rule-based explanation for high anomaly scores."""
        if score < _ANOMALY_THRESHOLD:
            return ""
        reasons = []
        speed, alt, vr, track, dlat, dlon, dalt, comp_speed, disc, seen_pos = vector
        if disc > 500:
            reasons.append(f"speed_discrepancy={disc:.0f}kt")
        if speed > 800:
            reasons.append(f"speed_too_high={speed:.0f}kt")
        if abs(dalt) > 8000:
            reasons.append(f"extreme_vert_rate={dalt:.0f}fpm")
        if abs(dlat) > 0.01 or abs(dlon) > 0.01:
            reasons.append("position_jump")
        return "|".join(reasons) if reasons else "anomalous_pattern"

    def annotate(
        self, aircraft: AirCraftData, history: list[AirCraftData]
    ) -> AirCraftData:
        """
        Extract features from history and annotate aircraft with anomaly score.
        Updates aircraft.anomaly_score, aircraft.anomaly_reason, and status.
        """
        if not self._trained:
            return aircraft

        features = extract(history)
        if features is None:
            return aircraft

        vector = to_vector(features)
        score, reason = self.predict(vector)
        aircraft.anomaly_score = score
        aircraft.anomaly_reason = reason or None

        if score > _ANOMALY_THRESHOLD and aircraft.status != TraceStatus.INVALID:
            aircraft.status = TraceStatus.SUSPICIOUS
            logger.info(
                "Anomaly detected hex=%s score=%.3f reason=%s",
                aircraft.hex, score, reason,
            )
        return aircraft


def train_from_samples(samples_dir: str = "notebook/samples") -> AnomalyDetector:
    """
    Train AnomalyDetector from all JSON files in samples/valid/.
    Returns fitted detector.
    """
    import json
    from pathlib import Path
    from adsb_secure.normalizer import build_from_dict
    from adsb_secure.trace_store import TraceStore

    detector = AnomalyDetector()
    store = TraceStore(max_history=50)
    vectors = []

    valid_dir = Path(samples_dir) / "valid"
    files = list(valid_dir.glob("*.json")) if valid_dir.exists() else []

    # Fallback to testing samples
    if not files:
        test_file = Path(samples_dir) / "testing" / "sample.json"
        if test_file.exists():
            files = [test_file]

    if not files:
        raise FileNotFoundError(f"No sample JSON files found in {samples_dir}")

    for json_file in files:
        logger.info("Loading training data from %s", json_file)
        data = json.loads(json_file.read_text())
        for raw in data.get("aircraft", []):
            ac = build_from_dict(raw)
            store.update(ac)

    for icao in store.icao_set():
        history = store.get_history(icao)
        if len(history) >= 2:
            features = extract(history)
            if features:
                vectors.append(to_vector(features))

    if len(vectors) < 2:
        # Generate synthetic vectors from single records for training
        for icao in store.icao_set():
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

    logger.info("Training IF on %d feature vectors", len(vectors))
    detector.train(vectors)
    return detector
