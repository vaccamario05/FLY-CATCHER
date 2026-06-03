# Sprint Plan

> Architettura aggiornata post ADR-001: Flask UI principale, pipeline modulare separata.
> Vedi [[04_Target_Architecture]] e [[16_Migration_Plan]] per dettagli.

## Sprint 1 — Foundation (2 settimane)

**Obiettivo**: struttura progetto Flask + pipeline base funzionante + simulatore + validator + fix Fly-catcher.

### Backlog Sprint 1 (aggiornato post-ADR-001)

| ID | Task | Tipo | Priorità |
|---|---|---|---|
| S1-00 | Creare struttura directory `adsb_secure/`, `security/`, `web/`, `ml/`, `simulator/`, `tests/` | Setup | Alta |
| S1-01 | Creare `requirements.txt` con dipendenze versionate | Setup | Alta |
| S1-02 | Creare `simulator/replay.py` — replay JSON per sviluppo senza SDR | Foundation | Alta |
| S1-03 | Creare `security/validator.py` — validazione strutturale pacchetti | Security | Alta |
| S1-04 | Creare `adsb_secure/normalizer.py` — `AirCraftData` con `status`, `anomaly_score`, etc. | Foundation | Alta |
| S1-05 | Creare `adsb_secure/acquisition.py` — `DataIngestion` (HTTP + simulator mode) | Foundation | Alta |
| S1-06 | Creare `adsb_secure/trace_store.py` — `TraceStore` dict per ICAO | Foundation | Media |
| S1-07 | Fix `device-rpi/flightdata.py` — debug prints + error handling + URL fix | Hygiene | Alta |
| S1-08 | Eseguire Bandit static analysis e documentare findings | DevSecOps | Alta |
| S1-09 | Eseguire pip-audit e documentare CVE trovati | DevSecOps | Alta |
| S1-10 | Scrivere test unitari per `validator.py` (≥7 test) | Testing | Alta |
| S1-11 | Scrivere test per `simulator/replay.py` | Testing | Media |

### Definition of Done — Sprint 1
- `python3 -m pytest tests/test_validator.py tests/test_simulator.py -v` → tutto verde
- Simulator produce AirCraftData da `notebook/samples/testing/sample.json`
- Validator rifiuta: ICAO malformato, lat>90, alt>60000ft, campo hex non hex
- `AirCraftData.status` sempre valorizzato (default `UNVERIFIED`)
- Bandit run con findings documentati in [[11_Bugs_and_Fixes]]
- `requirements.txt` con flask, scikit-learn, pytest, bandit

---

## Sprint 2 — Security Layer (2 settimane)

**Obiettivo**: HMAC PoC, replay detection, rate limiting, logging forense, auth base, web dashboard iniziale.

### Backlog Sprint 2

| ID | Task | Tipo | Priorità |
|---|---|---|---|
| S2-01 | Creare `security/hmac_validator.py` — HMAC-SHA256, chiave da env | Security | Alta |
| S2-02 | Creare `security/replay_detector.py` — finestra temporale + dedup set | Security | Alta |
| S2-03 | Creare `security/rate_limiter.py` — token bucket o sliding window | Security | Alta |
| S2-04 | Creare `security/classifier.py` — aggrega esiti, assegna stato finale | Security | Alta |
| S2-05 | Creare `security/forensic_logger.py` — append-only, SHA-256 chain | Security | Alta |
| S2-06 | Creare `web/app.py` — Flask app base con route `/` e `/api/aircraft` | Web | Alta |
| S2-07 | Creare `web/auth.py` — login, password hashata (werkzeug), RBAC | Web | Alta |
| S2-08 | Frontend dashboard base: lista tracce con colore per stato | Web | Alta |
| S2-09 | Test HMAC: modifica payload → verifica fallimento | Testing | Alta |
| S2-10 | Test replay: reinvio pacchetto duplicato → verifica scarto | Testing | Alta |
| S2-11 | Test flooding: N pacchetti/sec → verifica rate limit attivo | Testing | Media |
| S2-12 | Test log chaining: modifica record → verifica rottura chain | Testing | Alta |
| S2-13 | Documentare chiave HMAC setup in [[12_Commands_and_Runbook]] | Docs | Alta |

### Definition of Done — Sprint 2
- HMAC check funziona su dati simulati preprocessati
- Replay detection scarta pacchetti con timestamp > soglia configurabile
- Rate limiter attivo: N pacchetti/sec → excess scartati/loggati
- Log forensi: rottura chain rilevata automaticamente
- Dashboard web accessibile, mostra tracce con status colorato
- Login funzionante con 2 ruoli (operatore, analista)

---

## Sprint 3 — Intelligence Layer (3 settimane)

**Obiettivo**: anomaly detection ML, scoring tracce, dashboard avanzata, export report, debito tecnico.

### Backlog Sprint 3

| ID | Task | Tipo | Priorità |
|---|---|---|---|
| S3-01 | Creare `ml/feature_extractor.py` — delta pos/speed/alt tra messaggi consecutivi | ML | Alta |
| S3-02 | Creare `ml/anomaly_detector.py` — Isolation Forest, fit su samples legittimi | ML | Alta |
| S3-03 | Addestrare modello IF su `samples/` + dati generati da notebook | ML | Alta |
| S3-04 | Integrare `AnomalyDetector` nella pipeline post-classifier | ML | Alta |
| S3-05 | Aggiungere `anomaly_score` e `anomaly_reason` a `AirCraftData` | ML | Alta |
| S3-06 | Dashboard avanzata: alert panel, severità, motivazione classificazione | Web | Alta |
| S3-07 | API `/api/audit/logs` — log forensi filtrabili per tipo, data, severità | Web | Alta |
| S3-08 | Export CSV dei log di audit (solo analista) | Web | Media |
| S3-09 | Aggregazione alert: stessa traccia/finestra → alert singolo | Web | Media |
| S3-10 | Test IF: ghost aircraft simulato → verifica classificazione SUSPICIOUS | Testing | Alta |
| S3-11 | Test misuse case: tutti gli MC documentati nel [[06_Security_Model]] | Testing | Alta |
| S3-12 | Valutazione FP rate IF su dataset di validazione (target: <5%) | Testing | Alta |
| S3-13 | Documentare debito tecnico in [[10_TODO_and_Backlog]] | Docs | Media |
| S3-14 | Aggiornare Vault completo per consegna | Docs | Alta |

### Definition of Done — Sprint 3
- IF rileva ghost aircraft con traiettoria impossibile (test su dati simulati)
- FP rate ≤ 5% su validation set
- Dashboard mostra score anomalia + motivazione per tracce sospette
- API audit log funzionante con filtri
- Export CSV funzionante per ruolo analista
- Tutti i misuse case coperti da test

---

## Gantt semplificato

```
Settimana:  1   2   3   4   5   6   7
Sprint 1:  [=======]
Sprint 2:          [=======]
Sprint 3:                  [===========]
```
