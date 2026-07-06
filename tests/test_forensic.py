"""Tests for security/forensic_logger.py."""

import json
import os
import tempfile
import pytest
from security.forensic_logger import ForensicLogger, SecurityEvent, EventType, Severity


def _make_logger() -> tuple[ForensicLogger, str]:
    tmp = tempfile.mktemp(suffix=".jsonl")
    return ForensicLogger(tmp), tmp


def test_log_creates_file():
    flog, path = _make_logger()
    try:
        flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        assert os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_log_appends_records():
    flog, path = _make_logger()
    try:
        flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        flog.log(SecurityEvent(EventType.HMAC_FAIL, Severity.HIGH, icao="3c4b12"))
        with open(path) as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 2
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_chain_intact_after_multiple_logs():
    flog, path = _make_logger()
    try:
        for i in range(5):
            flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW, icao=f"icao{i}"))
        ok, broken_at = flog.verify_chain()
        assert ok is True
        assert broken_at is None
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_chain_broken_after_record_modification():
    flog, path = _make_logger()
    try:
        flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        flog.log(SecurityEvent(EventType.HMAC_FAIL, Severity.HIGH))
        flog.log(SecurityEvent(EventType.REPLAY_DETECTED, Severity.HIGH))

        # Tamper record 2
        with open(path, "r") as f:
            lines = f.readlines()
        rec = json.loads(lines[1])
        rec["severity"] = "low"  # modify
        lines[1] = json.dumps(rec) + "\n"
        with open(path, "w") as f:
            f.writelines(lines)

        ok, broken_at = flog.verify_chain()
        assert ok is False
        assert broken_at is not None
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_read_events_filters_by_type():
    flog, path = _make_logger()
    try:
        flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        flog.log(SecurityEvent(EventType.HMAC_FAIL, Severity.HIGH, icao="abc"))
        flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        events = flog.read_events(event_type=EventType.HMAC_FAIL)
        assert len(events) == 1
        assert events[0]["icao"] == "abc"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_read_events_filters_by_icao():
    flog, path = _make_logger()
    try:
        flog.log(SecurityEvent(EventType.REPLAY_DETECTED, Severity.HIGH, icao="aaaaaa"))
        flog.log(SecurityEvent(EventType.REPLAY_DETECTED, Severity.HIGH, icao="bbbbbb"))
        events = flog.read_events(icao="aaaaaa")
        assert len(events) == 1
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_prev_hash_chained():
    flog, path = _make_logger()
    try:
        flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        flog.log(SecurityEvent(EventType.HMAC_FAIL, Severity.HIGH))
        with open(path) as f:
            records = [json.loads(l) for l in f if l.strip()]
        assert records[1]["prev_hash"] == records[0]["hash"]
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_empty_log_chain_ok():
    flog, path = _make_logger()
    try:
        ok, _ = flog.verify_chain()
        assert ok is True
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_seq_increments_sequentially():
    flog, path = _make_logger()
    try:
        e1 = flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        e2 = flog.log(SecurityEvent(EventType.HMAC_FAIL, Severity.HIGH))
        e3 = flog.log(SecurityEvent(EventType.REPLAY_DETECTED, Severity.HIGH))
        assert (e1.seq, e2.seq, e3.seq) == (1, 2, 3)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_seq_persists_across_logger_instances():
    """A new ForensicLogger opening an existing file continues the sequence."""
    tmp = tempfile.mktemp(suffix=".jsonl")
    try:
        flog1 = ForensicLogger(tmp)
        flog1.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        flog1.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))

        flog2 = ForensicLogger(tmp)
        e3 = flog2.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        assert e3.seq == 3
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def test_seq_gap_detected_as_broken_chain():
    """A missing record (sequence gap) must be detected even if per-record hashes are locally valid."""
    flog, path = _make_logger()
    try:
        flog.log(SecurityEvent(EventType.PACKET_ACCEPTED, Severity.LOW))
        flog.log(SecurityEvent(EventType.HMAC_FAIL, Severity.HIGH))
        flog.log(SecurityEvent(EventType.REPLAY_DETECTED, Severity.HIGH))

        with open(path) as f:
            lines = [l for l in f if l.strip()]
        # Delete the middle record entirely (not modify — a clean excision)
        del lines[1]
        with open(path, "w") as f:
            f.writelines(lines)

        ok, broken_at = flog.verify_chain()
        assert ok is False
    finally:
        if os.path.exists(path):
            os.unlink(path)
