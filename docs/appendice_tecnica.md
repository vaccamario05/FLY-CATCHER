# Appendice Tecnica — ADS-B Secure
## Project Work — Ingegneria e Scienze Informatiche per la Cybersecurity
### Università Parthenope Napoli — A.A. 2025/2026
### Docenti: Prof. Luigi Romano, Prof. Luigi Coppolino
### Gruppo: Rocco Rizzitano, Mario Vacca

---

# SEZIONE 1 — THREAT MODEL (STRIDE)

## 1.1 Asset identificati

| ID | Asset | Proprietà di sicurezza | Minacce principali |
|---|---|---|---|
| A1 | Messaggi ADS-B ricevuti | Integrità, Disponibilità | Tampering, Spoofing, Replay, Flooding |
| A2 | ICAO address | Integrità, Autenticità | Spoofing, Collisione identità |
| A3 | Posizione, quota, velocità | Integrità, Correttezza | Altitude tampering, Ghost aircraft |
| A4 | Timestamp e ordine messaggi | Integrità, Freschezza | Replay attack |
| A5 | Modulo HMAC (PoC) | Integrità, Autenticità | Bypass, Chiave compromessa |
| A6 | Anomaly Detection | Correttezza, Affidabilità | Evasione modello, FP/FN |
| A7 | Dashboard Flask | Disponibilità, Integrità | XSS, DoS, Accesso non autorizzato |
| A8 | Log forensi | Integrità, Non-ripudio | Log tampering, Cancellazione |
| A9 | Credenziali e sessioni | Riservatezza, Integrità | Credential theft, Session hijack |

## 1.2 Threat Model STRIDE

| Categoria STRIDE | Attacco concreto | Modulo ADS-B Secure | Controllo |
|---|---|---|---|
| **S**poofing | Ghost aircraft injection (MC1) | `ml/anomaly_detector.py` | Isolation Forest |
| **S**poofing | ICAO falsificato | `security/validator.py` | Format check |
| **T**ampering | Altitude/velocity tampering (MC3) | `security/hmac_validator.py` | HMAC-SHA256 PoC |
| **T**ampering | Log manipulation (MC6) | `security/forensic_logger.py` | Hash chaining |
| **R**epudiation | Log repudiation | `security/forensic_logger.py` | Append-only + SHA-256 |
| **I**nfo Disclosure | Unauthorized tracking (MC5) | `web/auth.py` | RBAC + session |
| **D**enial of Service | Packet flooding (MC4) | `security/rate_limiter.py` | Token bucket |
| **E**levation of Privilege | Dashboard unauth access (MC8) | `web/auth.py` | Login + RBAC |

## 1.3 Trust Boundary

```
[Internet / Radio RF]
        TB1 ← tutto ciò che attraversa questo confine è UNTRUSTED
[dump1090 / JSONSimulator]
        ↓ raw JSON
[RateLimiter] → scarta se flood
[StructuralValidator] → scarta se malformato
[HMACValidator] → SUSPICIOUS se payload alterato   ← PoC su dati simulati
[ReplayDetector] → SUSPICIOUS se timestamp stale o duplicato
[Classifier] → TraceStatus: VALID / SUSPICIOUS / UNVERIFIED / INVALID
[AnomalyDetector] → score > 0.7 → SUSPICIOUS
[ForensicLogger] → SHA-256 chain append-only
        TB2 ← dati interni verificati
[TraceStore] → [Flask Dashboard] → operatore autenticato
```

---

# SEZIONE 2 — ARCHITETTURA TARGET

## 2.1 Struttura moduli (directory layout)

```
fly-catcher/
├── adsb_secure/
│   ├── __main__.py         ← entrypoint: python -m adsb_secure
│   ├── acquisition.py      ← DataIngestion + URL scheme validation
│   ├── normalizer.py       ← AirCraftData dataclass + TraceStatus enum
│   └── trace_store.py      ← TraceStore thread-safe dict[icao → deque]
│
├── security/
│   ├── validator.py        ← StructuralValidator (12 check)
│   ├── hmac_validator.py   ← HMAC-SHA256 PoC (timing-safe)
│   ├── replay_detector.py  ← timestamp window + bounded dedup
│   ├── rate_limiter.py     ← token bucket (configurabile via env)
│   ├── forensic_logger.py  ← append-only JSONL + SHA-256 chain
│   └── classifier.py       ← aggrega check → TraceStatus finale
│
├── ml/
│   ├── feature_extractor.py ← haversine, delta cinematici, speed discrepancy
│   ├── anomaly_detector.py  ← Isolation Forest (scikit-learn), joblib persistence
│   └── train.py             ← CLI training su samples reali
│
├── web/
│   ├── app.py               ← Flask create_app() + Leaflet.js dashboard
│   └── auth.py              ← RBAC operator/analyst, PBKDF2-SHA256
│
├── simulator/
│   ├── replay.py            ← JSONSimulator (replay file senza SDR)
│   └── preprocessor.py      ← HMACPreprocessor (firma record per test)
│
└── tests/                   ← 97 test (10 file)
```

## 2.2 Pipeline per pacchetto legittimo

```
fetch() → RateLimiter.allow() ✓
        → StructuralValidator.validate() ✓ → status=UNVERIFIED
        → HMACValidator.validate(tag) ✓ → hmac_valid=True
        → ReplayDetector.check() ✓ → replay_detected=False
        → classifier() → status=VALID
        → TraceStore.update()
        → AnomalyDetector.annotate() → anomaly_score=0.12
        → ForensicLogger.log(PACKET_ACCEPTED)
        → /api/traces → dashboard marker verde
```

## 2.3 Pipeline per ghost aircraft (attacco)

```
fetch() → RateLimiter.allow() ✓ (rate normale)
        → StructuralValidator.validate() ✓ (formato ok — ghost ben costruito)
        → HMACValidator.validate(None) ✗ → hmac_valid=False → status=SUSPICIOUS
        → ForensicLogger.log(HMAC_FAIL, severity=HIGH)
        → [oppure con HMAC firmato ma traiettoria impossibile:]
        → AnomalyDetector.annotate() → anomaly_score=0.85 → status=SUSPICIOUS
        → ForensicLogger.log(ANOMALY_DETECTED, severity=HIGH)
        → /api/traces → dashboard marker rosso
```

## 2.4 API Flask

| Method | Route | Auth | Ruolo | Descrizione |
|---|---|---|---|---|
| GET | `/health` | No | — | Liveness probe |
| GET | `/login` | No | — | Login form |
| POST | `/login` | No | — | Autenticazione |
| GET | `/` | Sì | operator+ | Dashboard Leaflet.js |
| GET | `/api/traces` | Sì | operator+ | JSON tracce con status/score |
| GET | `/api/aircraft/<icao>` | Sì | operator+ | Dettaglio + history |
| GET | `/api/audit/logs` | Sì | analyst | Log forensi filtrabili |
| GET | `/api/audit/verify` | Sì | analyst | Verifica integrità SHA-256 chain |
| GET | `/api/export/csv` | Sì | analyst | Export CSV audit log |

---

# SEZIONE 3 — FEASIBILITY ASSESSMENT

## 3.1 Classificazione requisiti

| Requisito | Livello | Implementato | Note |
|---|---|---|---|
| Ricezione da dump1090/simulator | **A — già presente** | ✅ | `acquisition.py` + `replay.py` |
| Decodifica ADS-B | **A — già presente** | ✅ | dump1090 fa decodifica, noi consumiamo JSON |
| Validazione strutturale | **C — nuovo codice** | ✅ | `validator.py`, 12 check |
| Dashboard base | **C — nuovo codice** | ✅ | Flask + Leaflet.js |
| HMAC verification | **D — solo PoC** | ✅ | Chiave pre-condivisa, solo dati simulati |
| Replay detection | **C — nuovo codice** | ✅ | Timestamp window + dedup |
| Rate limiting | **C — nuovo codice** | ✅ | Token bucket |
| Forensic logging | **C — nuovo codice** | ✅ | SHA-256 hash chaining |
| Auth / RBAC | **C — nuovo codice** | ✅ | PBKDF2 passwords, ruoli operator/analyst |
| Isolation Forest | **C — nuovo codice** | ✅ | scikit-learn, trainato su 8466 vettori |
| Ghost aircraft detection | **C/D** | ✅ | IF score > 0.7, ghost score = 0.734 |
| Export audit CSV | **C — nuovo codice** | ✅ | Analyst-only endpoint |
| TESLA completo | **E — fuori scope** | ❌ | Richiede sync temporale distribuita |
| PKI distribuita | **E — fuori scope** | ❌ | Richiede CA globale |
| MLAT | **E — fuori scope** | ❌ | Richiede rete fisica stazioni |

## 3.2 Limiti PoC dichiarati

1. **HMAC validation** opera solo su dati simulati preprocessati — NON modifica il protocollo ADS-B reale
2. Il sistema opera **solo in ricezione**, mai in trasmissione
3. Senza hardware SDR fisico: usa JSONSimulator + samples reali da ADSB Exchange
4. Training Isolation Forest su ~8666 campioni — in produzione servirebbe dataset più grande e etichettato

---

# SEZIONE 4 — DECISIONI ARCHITETTURALI (ADR)

## ADR-001 — Flask come UI principale (vs pygame)

**Problema**: Fly-catcher usava pygame su TFT screen RPi → incompatibile con RBAC, sessioni, log viewer web.

**Decisione**: Flask + HTML/JS come dashboard principale. pygame rimane disponibile come display legacy RPi.

**Motivazione**: RBAC richiede sessioni HTTP. Log viewer e export CSV sono naturali via browser. Flask è già nello stack Python.

**Impatto**: Nuovo modulo `web/`. Pipeline dati completamente separata dalla UI — `security/` e `ml/` testabili standalone.

## ADR-002 — Isolation Forest (vs CNN Keras)

**Problema**: Fly-catcher aveva `Spoof_Detection.h5` (CNN Keras, offline). ADS-B Secure specifica IF per anomaly detection real-time.

**Decisione**: Isolation Forest come componente principale. CNN disponibile come riferimento accademico.

**Motivazione**: IF è non-supervisionato → funziona senza dataset etichettato. Più interpretabile (anomaly_score continuo). scikit-learn già presente. TensorFlow troppo pesante per pipeline real-time.

## ADR-003 — HMAC key via env var

**Problema**: Chiave HMAC deve essere gestita senza hardcoding.

**Decisione**: `os.environ.get("ADSB_HMAC_KEY")` — nessun default nel codice.

**Motivazione**: Niente hardcoded secrets. Pattern standard per secrets in sviluppo. Key generation: `secrets.token_hex(32)`.

## ADR-004 — Estensione modulare (no fork)

**Problema**: Come integrare ADS-B Secure senza rompere Fly-catcher.

**Decisione**: Nuovi package `adsb_secure/`, `security/`, `web/`, `ml/` nella stessa repo. `device-rpi/` intatto.

**Motivazione**: Un repo = un contesto di team. Fly-catcher `device-rpi/` rimane funzionante su RPi fisico. Nuovi moduli non dipendono da pygame → testabili standalone.

## ADR-005 — JSONSimulator come sorgente dati

**Problema**: Sviluppo e test senza hardware SDR fisico.

**Decisione**: `simulator/replay.py` fa replay di `notebook/samples/*.json` (dati reali da ADSB Exchange).

**Motivazione**: Riproducibilità dei test. Samples già presenti nel repo. `Spoofed_Aircraft_Generator.ipynb` per sintetici.

---

# SEZIONE 5 — PRINCIPI DI SECURE DESIGN APPLICATI

| Principio | Applicazione concreta |
|---|---|
| **Secure by Design** | Ogni modulo della pipeline nasce per mitigare una minaccia specifica |
| **Defense in Depth** | validator → hmac → replay → rate → ML → log: 5 layer indipendenti |
| **Fail-Safe Defaults** | Default = `UNVERIFIED`. Ambiguità → `SUSPICIOUS`. Mai `VALID` senza superare tutti i check |
| **Least Privilege** | `operator` solo view. `analyst` view + log + export. Pipeline non accede a web layer |
| **Complete Mediation** | Ogni pacchetto attraversa tutta la pipeline. Nessuna corsia preferenziale |
| **Economy of Mechanism** | HMAC-SHA256 pre-shared key (semplice, sufficiente per PoC) |
| **Open Design** | Architettura documentata nel Vault, verificabile pubblicamente |
| **Psychological Acceptability** | Dashboard con colori chiari, badge status, aggregazione alert |

---

# SEZIONE 6 — METRICHE DI QUALITÀ

| Metrica | Target | Risultato |
|---|---|---|
| Test passing | 100% | **97/97 (100%)** |
| Bandit High severity | 0 | **0** |
| Bandit Medium severity | 0 | **0** (fix pickle→joblib) |
| IF anomaly score ghost aircraft | > 0.7 | **0.734** |
| IF false positive rate | ≤ 5% | **≤ 5% su test sintetici** |
| Latenza pipeline | < 50ms | **< 5ms su simulator** |
| Log chain integrity | 100% verificabile | **SHA-256 chain + verify_chain()** |
| Sprint completati | 3/3 | **3/3** |

---

# SEZIONE 7 — COMANDI RAPIDI PER DEMO

```bash
# 1. Variabili d'ambiente
export ADSB_HMAC_KEY=$(python3.11 -c 'import secrets; print(secrets.token_hex(32))')

# 2. Training modello (una tantum)
python3.11 -m ml.train --samples notebook/samples --augment 200

# 3. Avvio sistema
python3.11 -m adsb_secure --mode simulator --interval 3

# 4. Dashboard: http://localhost:5000
#    Login: operator/operator123 (view) | analyst/analyst123 (view+log)

# 5. Demo attacco (in altro terminale — vedi demo/demo_script.md)
python3.11 demo/inject_attack.py --attack ghost
python3.11 demo/inject_attack.py --attack replay
python3.11 demo/inject_attack.py --attack flood

# 6. Verifica log forense (come analista)
curl -b cookies.txt http://localhost:5000/api/audit/verify
curl -b cookies.txt "http://localhost:5000/api/audit/logs?severity=high"
```
