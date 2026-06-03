# Target Architecture — ADS-B Secure (Flask, aggiornato 2026-06-03)

> ADR-001 approvato: Flask = UI principale. pygame = legacy opzionale su RPi fisico.

## Principio architetturale

**Separazione totale pipeline dati / presentazione.**

La pipeline ADS-B Secure è indipendente da qualsiasi UI.
Flask consuma la pipeline via API interna — la pipeline non sa nulla di Flask.

```
┌─────────────────────────────────────────────────────────────┐
│  UNTRUSTED SOURCES (Trust Boundary TB1)                      │
│  [dump1090 :8080/data/aircraft.json] / [simulator/replay.py] │
└──────────────────────────┬──────────────────────────────────┘
                           │ raw JSON (untrusted)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  ACQUISITION LAYER                                           │
│  adsb_secure/acquisition.py                                  │
│  - DataIngestion: fetch HTTP or read from simulator          │
│  - RateLimiter: token bucket, blocks flood before parsing    │
│  - outputs: raw_packet dict (still untrusted)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  VALIDATION LAYER (Sprint 1 + 2)                             │
│  security/validator.py                                        │
│  - StructuralValidator: CRC, ICAO hex, lat/lon range,        │
│    altitude range, speed range, string sanitization          │
│  - outputs: validated_packet | INVALID (→ log + drop)        │
│                                                              │
│  security/hmac_validator.py          [PoC — simulated only]  │
│  - HMACValidator: HMAC-SHA256, key from env                  │
│  - outputs: hmac_valid bool                                  │
│                                                              │
│  security/replay_detector.py                                 │
│  - ReplayDetector: timestamp window + bounded dedup set      │
│  - outputs: replay_detected bool                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  NORMALIZATION + CLASSIFICATION (Sprint 1 + 2)               │
│  adsb_secure/normalizer.py                                   │
│  - builds AirCraftData with status field                     │
│  - Classifier: aggregates validator + hmac + replay results  │
│    → TraceStatus: VALID / SUSPICIOUS / UNVERIFIED / INVALID  │
│  adsb_secure/trace_store.py                                  │
│  - TraceStore: dict[icao → deque[AirCraftData]]              │
│  - maintains history per aircraft for feature extraction     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  INTELLIGENCE LAYER (Sprint 3)                               │
│  ml/feature_extractor.py                                     │
│  - FeatureExtractor: delta lat/lon/alt/speed/heading         │
│    between consecutive messages per ICAO                     │
│                                                              │
│  ml/anomaly_detector.py                                      │
│  - AnomalyDetector: Isolation Forest (scikit-learn)          │
│  - inputs: feature vector                                    │
│  - outputs: anomaly_score float, anomaly_reason str          │
│                                                              │
│  ml/trace_scorer.py                                          │
│  - merges classifier status + anomaly_score → final state    │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┴──────────────┐
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌────────────────────────────────┐
│  FORENSIC LOGGING     │    │  WEB LAYER (Sprint 2+3)        │
│  security/forensic_  │    │  web/app.py  (Flask)            │
│  logger.py           │    │  web/auth.py (RBAC)             │
│                      │    │  web/routes/                    │
│  - append-only JSONL │    │    aircraft.py  → /api/aircraft  │
│  - SHA-256 chain     │    │    audit.py     → /api/audit/   │
│  - all pipeline      │    │    export.py    → /api/export   │
│    events logged     │    │  web/templates/ (Jinja2)        │
│  - chain verify fn   │    │    dashboard.html               │
└──────────────────────┘    │    login.html                   │
                            │    audit_log.html               │
                            └────────────────────────────────┘
```

## Directory layout definitivo

```
fly-catcher/
├── adsb_secure/              ← package principale
│   ├── __init__.py
│   ├── __main__.py           ← entrypoint: python -m adsb_secure
│   ├── acquisition.py        ← DataIngestion + RateLimiter
│   ├── normalizer.py         ← AirCraftData builder + Classifier
│   ├── trace_store.py        ← TraceStore (in-memory per ICAO)
│   └── pipeline.py           ← orchestratore pipeline completa
│
├── security/
│   ├── __init__.py
│   ├── validator.py          ← StructuralValidator [Sprint 1]
│   ├── hmac_validator.py     ← HMACValidator PoC [Sprint 2]
│   ├── replay_detector.py    ← ReplayDetector [Sprint 2]
│   ├── rate_limiter.py       ← RateLimiter [Sprint 2]
│   └── forensic_logger.py    ← ForensicLogger hash chain [Sprint 2]
│
├── ml/
│   ├── __init__.py
│   ├── feature_extractor.py  ← FeatureExtractor [Sprint 3]
│   ├── anomaly_detector.py   ← Isolation Forest [Sprint 3]
│   └── trace_scorer.py       ← final classification [Sprint 3]
│
├── web/
│   ├── __init__.py
│   ├── app.py                ← Flask app factory [Sprint 2]
│   ├── auth.py               ← login/RBAC/session [Sprint 2]
│   ├── routes/
│   │   ├── aircraft.py       ← /api/aircraft [Sprint 2]
│   │   ├── audit.py          ← /api/audit/logs [Sprint 3]
│   │   └── export.py         ← /api/export/csv [Sprint 3]
│   └── templates/
│       ├── base.html
│       ├── login.html        ← [Sprint 2]
│       ├── dashboard.html    ← trace map + status colors [Sprint 2]
│       └── audit_log.html    ← forensic log viewer [Sprint 3]
│
├── simulator/
│   ├── __init__.py
│   └── replay.py             ← JSON replay (no hardware) [Sprint 1]
│
├── tests/
│   ├── test_validator.py     ← [Sprint 1]
│   ├── test_simulator.py     ← [Sprint 1]
│   ├── test_hmac.py          ← [Sprint 2]
│   ├── test_replay.py        ← [Sprint 2]
│   ├── test_rate_limiter.py  ← [Sprint 2]
│   ├── test_forensic.py      ← [Sprint 2]
│   ├── test_auth.py          ← [Sprint 2]
│   ├── test_features.py      ← [Sprint 3]
│   ├── test_anomaly.py       ← [Sprint 3]
│   └── test_api.py           ← [Sprint 3]
│
├── device-rpi/               ← legacy Fly-catcher (non toccare)
│   ├── piawareradar.py       ← pygame display (opzionale su RPi)
│   ├── flightdata.py         ← da patchare in Sprint 1
│   └── ...
│
├── notebook/                 ← notebook ML originali (read-only)
├── docs/vault/               ← Vault Obsidian
├── .claude/                  ← Claude OS
├── CLAUDE.md
└── requirements.txt          ← [Sprint 1]
```

## API Flask — endpoints previsti

| Method | Route | Auth | Ruolo | Descrizione |
|---|---|---|---|---|
| GET | `/` | Sì | operator+ | Dashboard principale |
| GET | `/login` | No | — | Login form |
| POST | `/login` | No | — | Autenticazione |
| GET | `/logout` | Sì | any | Logout |
| GET | `/api/aircraft` | Sì | operator+ | JSON: lista tracce con status/score |
| GET | `/api/aircraft/<icao>` | Sì | operator+ | JSON: dettaglio singola traccia |
| GET | `/api/audit/logs` | Sì | analyst | JSON: log forensi filtrabili |
| GET | `/api/audit/verify` | Sì | analyst | JSON: stato integrità chain |
| GET | `/api/export/csv` | Sì | analyst | CSV download log eventi |

## Trust Boundary

- **TB1**: dump1090 / simulator output → untrusted fino a StructuralValidator
- **TB2**: post-validation (struttura ok, range ok)
- **TB3**: post-HMAC+replay (PoC trusted in ambiente controllato)
- **TB4**: post-IF (classificazione finale con confidence score)

## Pipeline per pacchetto legittimo (happy path)

```
RateLimiter(ok) → StructuralValidator(ok) → HMACValidator(ok) →
ReplayDetector(not_duplicate) → Classifier(VALID) →
TraceStore.update() → FeatureExtractor → AnomalyDetector(score=0.05) →
TraceScorer(VALID, confidence=high) →
ForensicLogger(packet_accepted) → /api/aircraft update
```

## Pipeline per pacchetto malevolo (replay)

```
RateLimiter(ok) → StructuralValidator(ok) → HMACValidator(ok) →
ReplayDetector(DUPLICATE, Δt=45s > window=30s) →
Classifier(SUSPICIOUS, reason="replay_detected") →
ForensicLogger(replay_detected, severity=HIGH) →
/api/aircraft: traccia marcata SUSPICIOUS
  (pacchetto non aggiorna TraceStore)
```

## Componenti legacy (pygame)

`device-rpi/piawareradar.py` rimane funzionante ma non è più l'entrypoint strategico.
Usabile per:
- Demo su RPi fisico con TFT screen
- Visualizzazione locale senza web server
- Non richiede refactoring — basta non romperlo

Fix necessari a `device-rpi/flightdata.py` (Sprint 1):
- Rimuovere debug prints
- Aggiungere error handling
- Correggere URL hardcoded
