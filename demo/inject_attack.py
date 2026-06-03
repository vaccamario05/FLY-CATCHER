"""
demo/inject_attack.py
Purpose: Inject controlled attack scenarios into the ADS-B Secure pipeline.

Usage:
    python3.11 demo/inject_attack.py --attack ghost    # ghost aircraft (impossibile cinematicamente)
    python3.11 demo/inject_attack.py --attack replay   # replay attack (timestamp stale)
    python3.11 demo/inject_attack.py --attack flood    # packet flooding (100 pacchetti burst)
    python3.11 demo/inject_attack.py --attack tamper   # altitude tampering (HMAC fail)
    python3.11 demo/inject_attack.py --attack all      # tutti in sequenza

Outputs:
    - Mostra come ogni attacco viene rilevato
    - Stampa il log event generato
    - Verifica la catena hash del log forense
"""

import argparse
import json
import os
import sys
import time
import tempfile
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("demo")


def _pipeline(raw_records: list[dict], label: str) -> None:
    """Run records through the full pipeline and print results."""
    from adsb_secure.normalizer import build_from_dict, TraceStatus
    from security.validator import StructuralValidator
    from security.hmac_validator import HMACValidator
    from security.replay_detector import ReplayDetector
    from security.rate_limiter import TokenBucketRateLimiter
    from security.classifier import classify
    from security.forensic_logger import ForensicLogger, SecurityEvent, EventType, Severity

    log_file = tempfile.mktemp(suffix="_demo.jsonl")
    validator = StructuralValidator()
    hmac_v = HMACValidator()
    replay_d = ReplayDetector(window_seconds=30)
    rate_l = TokenBucketRateLimiter(pps=10, burst=10)  # low limit for demo — drop after 10
    flog = ForensicLogger(log_file)

    print(f"\n{'='*60}")
    print(f"ATTACK: {label}")
    print(f"{'='*60}")
    print(f"Injecting {len(raw_records)} packet(s)...")

    results = []
    for i, raw in enumerate(raw_records):
        # Rate check
        if not rate_l.allow():
            ev = flog.log(SecurityEvent(
                EventType.RATE_LIMIT_EXCEEDED, Severity.MEDIUM,
                details={"packet": i, "stats": rate_l.stats}
            ))
            print(f"  [{i}] DROPPED (rate limit) — event id={ev.id[:8]}")
            results.append(("rate_limit", raw.get("hex", "?")))
            continue

        # Structural validation
        ac = validator.validate(raw)
        if not ac.structural_valid:
            ev = flog.log(SecurityEvent(
                EventType.PACKET_INVALID, Severity.LOW,
                icao=ac.hex, details={"reasons": ac.structural_reasons}
            ))
            print(f"  [{i}] INVALID hex={ac.hex} reasons={ac.structural_reasons}")
            results.append(("invalid", ac.hex))
            continue

        # HMAC
        tag = raw.get("_hmac_tag")
        ac = hmac_v.validate(ac, tag)
        if ac.hmac_valid is False:
            ev = flog.log(SecurityEvent(
                EventType.HMAC_FAIL, Severity.HIGH, icao=ac.hex
            ))
            print(f"  [{i}] HMAC FAIL hex={ac.hex} → SUSPICIOUS | event id={ev.id[:8]}")
            results.append(("hmac_fail", ac.hex))
            continue

        # Replay
        ac = replay_d.check(ac)
        if ac.replay_detected:
            ev = flog.log(SecurityEvent(
                EventType.REPLAY_DETECTED, Severity.HIGH, icao=ac.hex,
                details={"seen": ac.seen}
            ))
            print(f"  [{i}] REPLAY hex={ac.hex} seen={ac.seen}s → SUSPICIOUS | event id={ev.id[:8]}")
            results.append(("replay", ac.hex))
            continue

        # Classification
        ac = classify(ac)
        print(f"  [{i}] hex={ac.hex} status={ac.status.value} hmac={ac.hmac_valid}")
        results.append((ac.status.value, ac.hex))

    # Chain verification
    ok, broken = flog.verify_chain()
    print(f"\nForensic log: {len(results)} events | Chain intact: {ok}")
    if broken:
        print(f"  WARNING: chain broken at line {broken}")

    # Print log
    events = flog.read_events(limit=10)
    if events:
        print(f"\nLog events (latest first):")
        for ev in events[:5]:
            print(f"  [{ev['severity'].upper()}] {ev['event_type']} icao={ev['icao']} "
                  f"id={ev['id'][:8]} hash={ev['hash'][:16]}...")

    try:
        os.unlink(log_file)
    except Exception:
        pass


def ghost_attack() -> None:
    """Ghost aircraft — cinematically impossible trajectory."""
    # Two records with same ICAO but 5-degree position jump in 2 seconds
    records = [
        {
            "hex": "ghost1",  # intentionally bad ICAO for demo visibility
            "flight": "GHOST  ",
            "lat": 45.0, "lon": 9.0,
            "alt_baro": 99999,   # above max → structural INVALID
            "gs": 9999,          # above max → structural INVALID
            "track": 90.0,
            "baro_rate": 0,
            "seen_pos": 1.0, "messages": 1, "seen": 1.0, "rssi": -5.0,
        }
    ]
    print("\nGhost aircraft: ICAO 'ghost1', alt=99999ft, gs=9999kt")
    print("Expected: INVALID (structural validator catches altitude + speed)")
    _pipeline(records, "Ghost Aircraft Injection (MC1)")


def ghost_attack_valid_format() -> None:
    """Ghost aircraft with valid format — demonstrates Isolation Forest detection directly."""
    print("\nGhost aircraft: Isolation Forest direct prediction")
    print("Expected: score > 0.7 → SUSPICIOUS")

    try:
        from ml.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        if not detector._trained:
            print("  [INFO] IF model not trained. Run: python3.11 -m ml.train first")
            print("  Showing synthetic prediction as fallback...")

        # Ghost vector: speed_kt, altitude_ft, vert_rate, track, delta_lat, delta_lon,
        #               delta_alt, computed_speed, speed_discrepancy, seen_pos
        ghost_vector = [9999.0, 200000.0, 99999.0, 720.0, 5.0, 5.0, 99999.0, 8000.0, 7999.0, 0.0]
        normal_vector = [450.0, 35000.0, 0.0, 180.0, 0.0002, 0.0003, 10.0, 448.0, 2.0, 1.0]

        ghost_score, ghost_reason = detector.predict(ghost_vector)
        normal_score, _ = detector.predict(normal_vector)

        print(f"\n{'='*60}")
        print(f"ATTACK: Ghost Aircraft — Isolation Forest (Sprint 3)")
        print(f"{'='*60}")
        print(f"  Ghost  vector score: {ghost_score:.3f} (threshold: 0.70)")
        print(f"  Normal vector score: {normal_score:.3f}")
        threshold = float(os.environ.get("IF_THRESHOLD", "0.7"))
        detected = ghost_score > threshold
        delta = ghost_score - normal_score
        print(f"  Delta (ghost-normal): +{delta:.3f} — ghost scores {delta/normal_score*100:.0f}% higher")
        if ghost_reason:
            print(f"  Explanation: {ghost_reason}")
        print(f"  IF threshold: {threshold} | Ghost DETECTED: {detected}")
        print(f"\n  IF decision: {'SUSPICIOUS — BLOCKED' if detected else 'Score below threshold (try: IF_THRESHOLD=0.6)'}")
    except Exception as e:
        print(f"  [ERROR] {e}")


def replay_attack() -> None:
    """Replay attack — old timestamp."""
    records = [
        {
            "hex": "3c4b12",
            "flight": "DLH400 ",
            "lat": 48.1, "lon": 11.6,
            "alt_baro": 32000, "gs": 480.0, "track": 270.0, "baro_rate": 0,
            "seen_pos": 1.0, "messages": 5000,
            "seen": 60.0,  # 60 seconds > window (30s) → REPLAY
            "rssi": -18.0,
        }
    ]
    print("\nReplay attack: seen=60s (window=30s)")
    print("Expected: REPLAY_DETECTED → SUSPICIOUS")
    _pipeline(records, "Replay Attack (MC2)")


def tamper_attack() -> None:
    """Altitude tampering — HMAC fail."""
    key = os.environ.get("ADSB_HMAC_KEY", "")
    if not key:
        print("\nWarning: ADSB_HMAC_KEY not set — HMAC validation disabled")
        print("Set with: export ADSB_HMAC_KEY=$(python3.11 -c 'import secrets; print(secrets.token_hex(32))')")
        print("Running anyway to show structural path...")

    # Sign a record, then modify altitude (simulates tampering)
    raw = {
        "hex": "a835c5",
        "flight": "UAL123 ",
        "lat": 40.0, "lon": -73.0,
        "alt_baro": 35000, "gs": 480.0, "track": 90.0, "baro_rate": 0,
        "seen_pos": 1.0, "messages": 2000, "seen": 1.0, "rssi": -22.0,
    }

    if key:
        from adsb_secure.normalizer import build_from_dict
        from security.hmac_validator import HMACValidator
        v = HMACValidator()
        ac = build_from_dict(raw)
        original_tag = v.sign(ac)
        # Tamper: change altitude after signing
        raw["alt_baro"] = 99  # attacker modifies altitude
        raw["_hmac_tag"] = original_tag  # but tag still covers original
        print(f"\nAltitude tampered: 35000ft → 99ft | Original HMAC tag preserved")
        print("Expected: HMAC_FAIL → SUSPICIOUS")
    else:
        raw["_hmac_tag"] = None
        print("\nHMAC key not set — showing structural path only")

    _pipeline([raw], "Altitude Tampering (MC3)")


def flood_attack() -> None:
    """Packet flooding — 25 packets against limit=10/s."""
    records = []
    for i in range(25):
        records.append({
            "hex": f"{i:06x}",
            "flight": f"FL{i:04d}",
            "lat": 40.0 + i * 0.1, "lon": 10.0,
            "alt_baro": 35000, "gs": 450.0, "track": 90.0, "baro_rate": 0,
            "seen_pos": 1.0, "messages": 100, "seen": 1.0, "rssi": -20.0,
        })
    print(f"\nPacket flood: 25 packets against limit=10/burst")
    print("Expected: first 10 accepted, remaining dropped (RATE_LIMIT_EXCEEDED)")
    _pipeline(records, "Packet Flooding / DoS (MC4)")


def main() -> None:
    parser = argparse.ArgumentParser(description="ADS-B Secure — Demo attack injector")
    parser.add_argument("--attack",
                        choices=["ghost", "ghost_valid", "replay", "tamper", "flood", "all"],
                        default="all", help="Attack type to inject")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║      ADS-B Secure — Demo Attack Injector                ║")
    print("║      Progettazione di Software Sicuro — Parthenope      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    attacks = {
        "ghost": ghost_attack,
        "ghost_valid": ghost_attack_valid_format,
        "replay": replay_attack,
        "tamper": tamper_attack,
        "flood": flood_attack,
    }

    if args.attack == "all":
        for name, fn in attacks.items():
            fn()
            time.sleep(0.5)
    else:
        attacks[args.attack]()

    print("\n" + "="*60)
    print("Demo complete. Check http://localhost:5000/api/audit/logs")
    print("(as analyst user) for forensic log entries.")


if __name__ == "__main__":
    main()
