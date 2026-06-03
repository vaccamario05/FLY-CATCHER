# Testing Strategy

## Obiettivi

- Verificare correttezza di ogni controllo di sicurezza
- Testare tutti i misuse case documentati in [[06_Security_Model]]
- Verificare che dati ambigui vengano classificati conservativamente
- Mantenere FP rate anomaly detection ≤ 5%

## Test Suite per Sprint

### Sprint 1 — Foundation Tests

| ID | Test | Input | Expected | File |
|---|---|---|---|---|
| TC-S1-01 | Validazione pacchetto corretto | JSON con tutti i campi validi | status=UNVERIFIED, structural_valid=True | `tests/test_validator.py` |
| TC-S1-02 | CRC/formato ICAO non valido | hex="ZZZZZZ" | structural_valid=False, status=INVALID | `tests/test_validator.py` |
| TC-S1-03 | lat/lon fuori range | lat=200.0 | structural_valid=False | `tests/test_validator.py` |
| TC-S1-04 | Campi None critici | lat=None, lon=None | status=UNVERIFIED (non INVALID) | `tests/test_validator.py` |
| TC-S1-05 | Pacchetto malformato (JSON invalido) | stringa non JSON | eccezione catturata, scartato | `tests/test_validator.py` |
| TC-S1-06 | Simulatore replay JSON | file `samples/testing/sample.json` | lista AirCraftData non vuota | `tests/test_simulator.py` |
| TC-S1-07 | Range altitude anomala | altitude=150000 | structural_valid=False | `tests/test_validator.py` |

### Sprint 2 — Security Layer Tests

| ID | Test | Input | Expected | File |
|---|---|---|---|---|
| TC-S2-01 | HMAC valido | payload + chiave corretta | hmac_valid=True | `tests/test_hmac.py` |
| TC-S2-02 | HMAC fallito (tampering) | payload modificato post-HMAC | hmac_valid=False, status=SUSPICIOUS | `tests/test_hmac.py` |
| TC-S2-03 | HMAC fallito (chiave sbagliata) | chiave diversa | hmac_valid=False | `tests/test_hmac.py` |
| TC-S2-04 | Replay — stesso pacchetto | stesso (ICAO, ts, pos) x2 | secondo scartato, evento loggato | `tests/test_replay.py` |
| TC-S2-05 | Replay — timestamp obsoleto | timestamp > window_seconds fa | replay_detected=True | `tests/test_replay.py` |
| TC-S2-06 | Replay — pacchetto fresco | timestamp < window_seconds fa | non rilevato come replay | `tests/test_replay.py` |
| TC-S2-07 | Rate limit non superato | N-1 pacchetti/sec | tutti elaborati | `tests/test_rate.py` |
| TC-S2-08 | Rate limit superato | N+10 pacchetti/sec | excess scartati, evento loggato | `tests/test_rate.py` |
| TC-S2-09 | Log chain intatta | scrittura 5 eventi | verifica hash chaining OK | `tests/test_forensic.py` |
| TC-S2-10 | Log chain rotta (modifica manuale) | modifica record #3 | chain_broken rilevato | `tests/test_forensic.py` |
| TC-S2-11 | Login valido | username/password corretti | sessione creata | `tests/test_auth.py` |
| TC-S2-12 | Login fallito | password sbagliata | errore + evento loggato | `tests/test_auth.py` |
| TC-S2-13 | Accesso analista a log | ruolo=analyst | OK | `tests/test_auth.py` |
| TC-S2-14 | Accesso operatore a log | ruolo=operator | 403 Forbidden | `tests/test_auth.py` |

### Sprint 3 — Intelligence Layer Tests

| ID | Test | Input | Expected | File |
|---|---|---|---|---|
| TC-S3-01 | Feature extraction normale | traccia 5 messaggi consecutivi | dict feature non vuoto | `tests/test_features.py` |
| TC-S3-02 | IF su traccia normale | dati legittimi da samples/ | anomaly_score basso (<0.3) | `tests/test_anomaly.py` |
| TC-S3-03 | IF ghost aircraft (salto pos) | Δlat=5° in 1 sec | anomaly_score alto, SUSPICIOUS | `tests/test_anomaly.py` |
| TC-S3-04 | IF velocità impossibile | speed=5000 knots | anomaly_score alto | `tests/test_anomaly.py` |
| TC-S3-05 | FP rate su validation set | 100 tracce legittime | FP ≤ 5 (5%) | `tests/test_anomaly.py` |
| TC-S3-06 | Dashboard mostra stato | GET /api/aircraft | JSON con status, score per ogni traccia | `tests/test_api.py` |
| TC-S3-07 | Export CSV (analista) | GET /api/audit/export | CSV valido | `tests/test_api.py` |
| TC-S3-08 | Export CSV (operatore) | GET /api/audit/export | 403 Forbidden | `tests/test_api.py` |

## Test Misuse Case (non-functional)

| MC | Test scenario | Verifica |
|---|---|---|
| MC1 Ghost Aircraft | Inietta 10 ghost con traiettorie impossibili | IF li classifica SUSPICIOUS, log eventi generati |
| MC2 Replay | Ritrasmetti pacchetto valido dopo 60s | Replay detector scarta, log event |
| MC3 Tampering | Modifica altitude in pacchetto preprocessato | HMAC fail, SUSPICIOUS |
| MC4 Flooding | 1000 pacchetti/sec | Rate limiter attivo, dashboard stabile |
| MC6 Log Repudiation | Modifica riga log | Chain broken alert |
| MC7 False Alert | 100 anomalie minori stessa traccia | Aggregati in 1 alert aggregato |
| MC8 Unauth access | Accesso dashboard senza login | Redirect to login |

## Test non funzionali

| ID | Test | Soglia | Tool |
|---|---|---|---|
| TC-NF-01 | Latenza elaborazione pacchetto | < 50ms average | `time.perf_counter()` |
| TC-NF-02 | Disponibilità durante flooding test | ≥ 99% | monitoring loop |
| TC-NF-03 | FP rate ML | ≤ 5% | validation dataset |
| TC-NF-04 | Simulator compatibilità | replay JSON → pipeline OK | integration test |
