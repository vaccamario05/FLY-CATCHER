# Feasibility Assessment

Legenda livelli:
- **A** = Già presente in Fly-catcher
- **B** = Riutilizzabile con refactoring minimo
- **C** = Implementabile direttamente (nuovo codice)
- **D** = Implementabile solo come PoC/simulazione
- **E** = Non implementabile ora / fuori scope

---

## Tabella fattibilità completa

| Requisito | ID | Livello | Note | Rischio | Sprint |
|---|---|---|---|---|---|
| Ricezione pacchetti ADS-B da SDR/dump1090 | RF1 | **A** | `flightdata.py` già fa fetch da dump1090 HTTP API | Basso | 1 |
| Simulatore dati ADS-B (senza hardware) | RF1-sim | **B** | `_refresh()` esiste già, serve adattare con replay di file JSON | Basso | 1 |
| Decodifica messaggi ADS-B | RF1-dec | **A** | dump1090 fa la decodifica, Fly-catcher consuma JSON | Basso | 1 |
| Validazione strutturale pacchetti (CRC, ICAO, length) | RF2 | **C** | Nuovo modulo `validator.py`, applicato pre-parse | Medio | 1 |
| Dashboard web real-time con classificazione tracce | RF6 | **C** | **Gap critico**: Fly-catcher usa pygame. Serve Flask/FastAPI + JS frontend | Alto | 1-3 |
| Display stato tracce (trusted/suspicious/unverified) | RF6-states | **C** | Nuovo: color coding, status field su AirCraftData | Basso | 1 |
| HMAC verification (PoC) | RF4 | **C/D** | Nuovo modulo `hmac_validator.py` — funziona solo su dati preprocessati con chiave pre-condivisa | Medio | 2 |
| Timestamp validation / replay detection | RF5 | **C** | Finestra temporale + deduplicazione — implementabile direttamente | Basso | 2 |
| Rate limiting / anti-flooding | SS4 | **C** | Token bucket o sliding window su fetch loop | Basso | 2 |
| Classificazione pacchetti (stato sicurezza) | RF2+RF4 | **C** | Enum: VALID/SUSPICIOUS/UNVERIFIED/INVALID | Basso | 2 |
| Audit log append-only + hash chaining | RF7 | **C** | `forensic_logger.py` con SHA-256 chaining | Basso | 2 |
| Auth / RBAC (operatore/analista) | PB1 | **C** | Flask-Login o basic auth + ruoli | Medio | 2 |
| Anomaly detection Isolation Forest | RF3 | **C** | scikit-learn già usato nei notebook — portare in pipeline real-time | Medio | 3 |
| Ghost aircraft / traiettorie non plausibili | SS3 | **C/D** | Regole euristiche + IF; dataset needed per training | Alto | 3 |
| Feature extraction cinematiche | Sprint3 | **C** | Delta posizione, velocità, quota tra messaggi consecutivi | Basso | 3 |
| Scoring anomalia + confidenza | Sprint3 | **C** | Output IF: score + motivazione | Basso | 3 |
| Export report PDF/CSV | US4 | **C** | Flask endpoint + pandas/csv | Basso | 3 |
| CNN Spoof_Detection.h5 (esistente) | ML-cnn | **B** | Modello già addestrato, usabile offline; va integrato nella pipeline | Medio | 3 |
| Bandit static analysis | DevSec | **C** | `pip install bandit && bandit -r .` | Basso | 1 |
| pip-audit dependency check | DevSec | **C** | `pip install pip-audit && pip-audit` | Basso | 1 |
| TESLA completo | — | **E** | Richiede sync temporale distribuita + infrastruttura | — | Fuori scope |
| PKI distribuita | — | **E** | Richiede CA, cert management globale | — | Fuori scope |
| MLAT cross-validation | — | **E** | Richiede rete fisica stazioni riceventi distribuite | — | Fuori scope |
| Trasmissione ADS-B | RE-01 | **E** | **Vietato per vincolo RE-01** | — | Sempre fuori scope |

---

## Gap analysis critica

### Gap #1 — Display: pygame vs Web Dashboard [CRITICO]
- **Fly-catcher**: pygame su TFT 3.5" — non accessibile via browser
- **ADS-B Secure target**: dashboard web real-time
- **Impatto**: richiede nuovo frontend; pygame diventa opzionale/legacy
- **Soluzione consigliata**: Flask/FastAPI backend + polling JS frontend (SSE o WebSocket)
- Vedi [[09_Decisions_Log#ADR-001]]

### Gap #2 — ML: offline notebook vs pipeline real-time
- **Fly-catcher**: CNN usata offline nel notebook dopo raccolta dati
- **ADS-B Secure target**: anomaly detection in-process su ogni messaggio
- **Impatto**: serve refactoring da notebook → modulo Python standard
- **Soluzione**: estrarre logica inferenza da `Fly_Catcher.ipynb`, wrappare in classe `AnomalyDetector`

### Gap #3 — Nessuna validazione input [SECURITY]
- Tutti i campi JSON accettati raw senza controllo
- Serve validation layer prima di qualunque elaborazione

### Gap #4 — Nessun logging
- Zero tracciabilità eventi
- Ogni security event deve essere loggato

### Gap #5 — Requirements.txt mancante
- Dipendenze non dichiarate esplicitamente
- Serve creare `requirements.txt` con versioni fissate

---

## Classificazione rapida

### Implementa subito (Sprint 1)
- Validation layer strutturale
- requirements.txt
- Simulatore dati (replay JSON)
- Refactoring `AirCraftData` con campo `status`
- Bandit + pip-audit

### Implementa dopo (Sprint 2)
- HMAC PoC module
- Replay detection / timestamp window
- Rate limiting
- Forensic logger (hash chaining)
- Auth + RBAC base
- Web dashboard (Flask)

### Solo PoC / simulazione (Sprint 2-3)
- HMAC validation (solo su dati preprocessati)
- Dati sintetici per addestramento IF

### Fuori scope
- TESLA, PKI, MLAT, trasmissione ADS-B

---

## Rischi tecnici

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| Dashboard pygame→web: migrazione complessa | Alta | Alto | Architettura dual: mantieni pygame, aggiungi web layer |
| Dataset mancante per IF training | Media | Medio | Usa `samples/` + Spoofed_Aircraft_Generator.ipynb |
| dump1090 assente su macOS dev | Alta | Medio | Simulatore JSON (replay file) come stub |
| Latenza pipeline con security checks | Bassa | Medio | Benchmark post-implementazione |
| Dipendenze TensorFlow pesanti | Media | Basso | Isolation Forest (scikit-learn) prioritario; CNN opzionale |
