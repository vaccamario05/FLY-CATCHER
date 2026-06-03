---
name: security-reviewer
description: Reviews ADS-B Secure code for security correctness. Use before marking any security-related sprint task as done, or when reviewing input handling, secrets, logging, or classification logic.
---

# Security Reviewer Skill

## Core axiom

**Every byte from ADS-B / dump1090 is untrusted.**

## Review checklist (run on every security-related change)

### 1 — Input validation
- All JSON fields validated before use?
- Lat/lon: `-90 ≤ lat ≤ 90`, `-180 ≤ lon ≤ 180`
- Altitude: realistic range for civil aviation (e.g., -1500 to 60000 feet)
- Speed: realistic range (0 to 1500 knots for civil aviation)
- ICAO hex: exactly 6 hex characters
- String fields (flight, squawk): alphanumeric only, max length enforced
- None/missing fields handled without crash

### 2 — Secrets
- `grep -rn "key\|secret\|password\|token" <file> | grep -v "test\|#"` → no hardcoded values?
- All from `os.environ.get('NAME', None)` with fallback handled?
- `.env` in `.gitignore`?
- HMAC key never appears in logs?

### 3 — HMAC (Sprint 2)
- `hmac.compare_digest()` used (not `==`) to prevent timing attacks?
- Failure path → `SUSPICIOUS` not crash?
- PoC scope documented in docstring?

### 4 — Replay detection (Sprint 2)
- Dedup set uses bounded structure (e.g., `deque` with maxlen)?
- Clock used: `time.time()` consistently?
- Window configurable via env?

### 5 — Forensic logging (Sprint 2)
- File opened with `"a"` mode?
- `prev_hash` field present in every record?
- SHA-256 computed over deterministic serialization?
- Verification function tests the full chain?

### 6 — Classification defaults
- New packet starts as `UNVERIFIED` not `VALID`?
- Any exception in pipeline → `SUSPICIOUS` not propagated?
- No code path that skips validation and returns `VALID`?

### 7 — Web / Auth (Sprint 2)
- Passwords hashed with `werkzeug.security.generate_password_hash`?
- Session tokens are `secrets.token_urlsafe(32)`?
- RBAC check on every protected route?
- Session expiry enforced?

## PoC boundaries (not security issues — just document)

These are known limitations, NOT vulnerabilities:
- HMAC pre-shared key (no PKI) — ADR-003
- No TLS on localhost — acceptable for academic PoC
- Single-instance session store (in-memory) — acceptable for prototype

## Output

For each finding:

```
[SECURITY] or [PoC-LIMIT]
Severity: Critical / High / Medium / Low / Info
File: path:line
Finding: description
Evidence: code quote
Recommended fix: specific action
```

Document all `[SECURITY]` findings in `docs/vault/11_Bugs_and_Fixes.md`.
