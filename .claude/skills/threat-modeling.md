---
name: threat-modeling
description: Links STRIDE threats to misuse cases, mitigations, and implementing modules. Use when reviewing security architecture, adding new features, or preparing the threat model section of the project document.
---

# Threat Modeling Skill

## STRIDE reference for ADS-B Secure

| Category | ADS-B Example | Severity | Mitigation | Sprint |
|---|---|---|---|---|
| **S**poofing | Ghost aircraft injection (MC1) | High | Isolation Forest + conservative classification | 3 |
| **S**poofing | ICAO address falsification | High | Structural validator + IF | 1+3 |
| **T**ampering | Altitude/velocity tampering (MC3) | Critical | HMAC PoC + range validation | 2 |
| **T**ampering | Log manipulation (MC6) | High | SHA-256 hash chaining | 2 |
| **R**epudiation | Log repudiation (MC6) | High | Append-only + hash chain | 2 |
| **I**nfo Disclosure | Unauthorized tracking (MC5) | Medium | Auth + RBAC | 2 |
| **D**enial of Service | Packet flooding (MC4) | High | Rate limiting | 2 |
| **E**levation of Privilege | Dashboard unauth access (MC8) | High | RBAC + session timeout | 2 |

## Misuse case → mitigation → module

| MC | Attack | Mitigation module | Test |
|---|---|---|---|
| MC1 | Ghost aircraft | `ml/anomaly_detector.py` | TC-S3-03, TC-S3-04 |
| MC2 | Replay attack | `security/replay_detector.py` | TC-S2-04, TC-S2-05 |
| MC3 | Altitude tampering | `security/hmac_validator.py` | TC-S2-02 |
| MC4 | Packet flooding | `security/rate_limiter.py` | TC-S2-07, TC-S2-08 |
| MC5 | Unauthorized tracking | `web/auth.py` + RBAC | TC-S2-13, TC-S2-14 |
| MC6 | Log repudiation | `security/forensic_logger.py` | TC-S2-10 |
| MC7 | False alert triggering | Alert aggregation in web dashboard | TC-S3 |
| MC8 | Dashboard unauth access | `web/auth.py` session | TC-S2-11, TC-S2-12 |

## Residual risk (after all mitigations)

| Threat | Residual level | Reason |
|---|---|---|
| Ghost aircraft | Medium | Structural: no native ADS-B authentication |
| Unauthorized tracking | Medium | Structural: broadcast protocol |
| Altitude tampering | Medium | HMAC applies only to PoC data |
| Packet flooding (physical) | Medium | Rate limit helps but physical DoS unblockable |

## When adding a new feature — threat impact check

For any new module, answer:
1. Does it accept external input? → add validation
2. Does it store data? → add integrity check
3. Does it expose an endpoint? → add auth check
4. Does it log? → use ForensicLogger, not plain print
5. Does it use a secret? → env var only

## Output format

For new feature threat assessment:

```
Feature: [name]
New attack surface: [what could an attacker now target]
STRIDE categories affected: [S/T/R/I/D/E]
Mitigations needed: [list]
Existing mitigations that cover this: [modules]
Residual risk: [level + reason]
```
