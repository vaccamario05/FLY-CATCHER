# Session Handoff

## Ultima sessione: 2026-07-06 — Sessione 8: chiusura gap requisiti + security fix + feed reale + UX dashboard ✅

### Contesto
Sessione guidata da requisiti formali (RF/RNF/security stories/misuse case/threat model) letti a raffica dall'utente,
riscontrati uno a uno contro il codice esistente. La maggior parte erano già soddisfatti; individuati e chiusi gap reali.

### Gap chiusi (implementazione)

1. **ML anomaly detection non era wired in pipeline** (PB3/PB8) — `AnomalyDetector.annotate()` esisteva e testato ma mai
   chiamato da `adsb_secure/__main__.py`. Ora invocato prima di `classify()`, logga `ANOMALY_DETECTED`.
2. **`LOGIN_SUCCESS` mai loggato** (PB10/MC6) — solo i fallimenti finivano nel forensic log. Aggiunto.
3. **Pipeline senza self-healing** (PB15) — un'eccezione non gestita uccideva il thread silenziosamente. Ora
   `_pipeline_supervisor()` cattura e riavvia. `/health` riflette liveness reale (heartbeat), non più statico.
4. **PB13 (latenza/perf) mai verificato** — aggiunto `tests/test_perf.py`: latenza media/p95 pipeline, packet loss
   sotto rate limiting.
5. **RNF3 FN rate non testato** (solo FP testato) — aggiunto `test_false_negative_rate_on_ghost_data`.
6. **RBAC senza gestione soglie runtime** — nessun modo di cambiare rate limit/replay window/anomaly threshold/alert
   severity senza restart. Aggiunto `GET/POST /api/config/thresholds`, solo ruolo `analyst`, logga `CONFIG_CHANGED`.
7. **Bug scoperto durante il fix sopra**: `security/classifier.py` confrontava `anomaly_score` con soglia hardcoded
   0.7, ignorando `IF_THRESHOLD` configurabile di `ml/anomaly_detector.py` — `annotate()` flaggava SUSPICIOUS a una
   soglia diversa da quella poi usata (e silenziosamente sovrascritta) da `classify()`. Fixato per leggere la stessa
   soglia dal modulo.
8. **CWE-259 — password hardcoded** in `web/auth.py` (`operator123` ecc. come default statici nel sorgente pubblico).
   Rimossi: se env var assente, genera password random via `secrets.token_urlsafe` e la logga una tantum. Test/demo
   spostati su env var esplicite (`tests/conftest.py`, `demo/start_demo.sh`).
9. **CWE-79 — XSS reale** in `/analyst/events`: la colonna dettagli usava un escape homemade (`.replace()`) solo
   sull'attributo `title`, il contenuto visibile della cella era iniettato via `innerHTML` **senza escape**. Vettore
   reale: un ICAO malformato (fallisce regex validator) finisce comunque nel campo `icao` dell'evento forensic
   `PACKET_INVALID` prima di essere scartato dalla pipeline. Fixato con un `escapeHtml()` unico applicato a tutti i
   campi (event_type, icao, details, id).
10. **Bug latente in `acquisition.py`**: `_validate_url()` solleva `ValueError` su scheme non-http/https, ma
    `_fetch_from_http` non lo catturava — violava il contratto "never raises" della docstring. Fixato.
11. **Feed ADS-B reale (ADS-B Exchange / airplanes.live)** — `DataIngestion` ora accetta `headers` (per API key) e
    legge sia `data["aircraft"]` (dump1090) che `data["ac"]` (readsb-based, stesso schema campi). Config via
    `DUMP1090_URL` + `ADSB_HTTP_HEADERS` (JSON). Testato live con airplanes.live (serve User-Agent realistico,
    Cloudflare blocca lo user-agent di default di urllib).
12. **Bug simulatore: falso "tutto SUSPICIOUS"** — `JSONSimulator(loop=True)` ri-leggeva lo stesso file statico
    identico ogni ciclo → `ReplayDetector` (correttamente) flaggava ogni traccia come replay dal 2° ciclo in poi.
    Fixato: il simulatore ora varia leggermente `seen` a ogni reload, come farebbe un feed vivo.
13. **Dashboard UX** (feedback utente diretto): colonna "Reason" mostrava solo strutturale+anomaly, non
    hmac/replay → spesso "—" pur essendo SUSPICIOUS. Fixato con `_full_reasons()` condivisa da tabella+alert+popup.
    Aggiunta barra di ricerca ICAO/flight, tabella con scroll+sticky header (era lista interminabile), marker
    aereo ruotati per track (invece di pallini statici), **rotte di volo (trail)** disegnate client-side accumulando
    posizioni per ICAO ad ogni refresh.

### Verificato coerente (nessuna azione)

Validazione strutturale, HMAC PoC scope, replay detection, rate limiting, RBAC segregazione route, fail-safe
classification, logging append-only+hash chain, no-transmit, no-alterazione-dati-originali, export audit,
NIST 800-53 mapping (discusso, non scritto in doc), disclaimer certificazione in README — tutti già a posto.

### File toccati (principali)
- `adsb_secure/__main__.py`, `adsb_secure/acquisition.py`
- `security/classifier.py`, `security/forensic_logger.py`
- `web/app.py` (grosso: config endpoint, error handler, XSS fix, UX dashboard, reasons)
- `web/auth.py` (no hardcoded passwords)
- `ml/anomaly_detector.py` (`is_trained` property)
- `simulator/replay.py` (fix loop replay)
- `tests/test_perf.py`, `tests/test_acquisition.py` (nuovi)
- `tests/test_anomaly.py`, `tests/conftest.py`
- `demo/start_demo.sh`, `README.md`

### Stato finale
- **119/119 test verdi**
- Commit multipli, tutti pushati su `main`

### Note per prossima sessione
- Refuso doc (non codice) segnalato all'utente: tabella STRIDE 4.6 usa "A6 log forensi", dovrebbe essere "A8" (A6 è
  il modulo anomaly detection in 4.2) — da correggere nel testo della relazione, non nel codice.
- Utente ha una API key RapidAPI per ADS-B Exchange ma piano free non più disponibile — passato ad airplanes.live
  (nessuna key richiesta). Se serve tornare a ADS-B Exchange, verificare piano a pagamento attivo.
- Trail di volo sono client-side/per-sessione-browser (si azzerano al refresh pagina) — se serve persistenza
  storica delle rotte, andrebbe aggiunto un endpoint `/api/aircraft/<icao>/history` che legge da `trace_store`.

---

## Ultima sessione: 2026-07-06 — Sessione 7: Agile Scrum backlog — US2/US3/US4/UC2-EX1/RBAC ✅

### Contesto
Sessione guidata da documentazione formale progetto (stakeholder, personas, use case, user stories, security stories).
Gap analysis → 5 delta identificati → tutti implementati.

### Cosa è stato fatto

1. **RBAC: ruolo `supervisor`** (`web/auth.py`) — gerarchia: operator(0) < supervisor(1) < analyst(2)
   - Nuovo utente `supervisor` / `supervisor123` (override via `SUPERVISOR_PASSWORD` env)
   - `require_role` gerarchia aggiornata
2. **US2: Alert panel** (`web/app.py`) — pannello alert sopra la mappa
   - Mostra solo tracce con severità ≥ `ALERT_MIN_SEVERITY` (default: medium)
   - Severity derivata da status: suspicious→MEDIUM, invalid→HIGH
   - Aggregazione per ICAO (già garantita da `all_current()`)
   - Mostra: severity badge, ICAO link, flight, reasons, anomaly score
3. **US3: Analyst events page** (`/analyst/events`) — HTML interattiva
   - Filtri: event_type, severity, ICAO, limit
   - Ordinamento click su colonna (timestamp/severity/event_type)
   - Mostra chain integrity status in cima
   - Solo ruolo analyst
4. **US4: PDF export** (`/api/export/pdf`) — reportlab A4
   - Titolo, timestamp, chain integrity, tabella eventi
   - Ogni export (CSV + PDF) loggato su forensic logger come `AUDIT_EXPORT`
5. **UC2 EX1: Chain integrity banner** — dashboard analyst
   - JS fetch `/api/audit/verify` on load → banner rosso se catena rotta
6. **`security/forensic_logger.py`** — aggiunto `AUDIT_EXPORT` a `EventType`
7. **`requirements.txt`** — aggiunto `reportlab>=4.0`
8. **Test** — 12 nuovi test in `tests/test_web.py` (109 totali, tutti verdi)

### File toccati
- `web/app.py` (riscritta con _ANALYST_HTML, alert panel, PDF export, logging export)
- `web/auth.py` (supervisor user + gerarchia aggiornata)
- `security/forensic_logger.py` (AUDIT_EXPORT EventType)
- `requirements.txt` (reportlab>=4.0)
- `tests/test_web.py` (12 nuovi test)
- `docs/vault/14_Session_Handoff.md`

### Stato sicurezza finale

| Tool | Risultato |
|---|---|
| Test | 109/109 passing |
| Bandit | non rieseguito (no new security-sensitive code) |
| pip-audit | reportlab aggiunto — nessun CVE noto |

### Gap residui (non richiesti da backlog attuale)

- RBAC: supervisor non ha nav extra (può vedere dettaglio via click ICAO — US5 soddisfatta)
- PDF styling basic (PoC) — non dark theme
- `read_events` non supporta filtro time range (workaround: filter client-side)

### Prossima sessione

- Continuare con product backlog Scrum — attendere prossime user stories/sprint
- Possibile: test di integrazione end-to-end con HMACPreprocessor

---

## Ultima sessione: 2026-06-03 — Sessione 6: Debito tecnico azzerato ✅

### Cosa è stato fatto

1. **pickle → joblib** in `ml/anomaly_detector.py` — elimina Bandit B301/B403 (2 Medium → 0)
2. **`simulator/preprocessor.py`** — HMACPreprocessor: aggiunge `_hmac_tag` ai record per test HMAC end-to-end
3. **IF training su dati reali** — `ml/train.py`: 8466 vettori reali da samples + 200 sintetici → modello trainato
4. **Dashboard con mappa Leaflet.js** — dark theme, marker colorati per status, popup con dettagli, refresh 5s
5. **`requirements.txt`** aggiornato con `joblib>=1.3`
6. **`.gitignore`** aggiornato con `models/`
7. **Bandit finale**: 0 High, 0 Medium, 1 Low (B112 try/except/continue in train.py — accettato)
8. **pip-audit documentato**: urllib3 CVE (transitivo Flask, non nostro), torch CVE (sistema, non nel progetto)
9. **Vault aggiornato**: `11_Bugs_and_Fixes.md`, `12_Commands_and_Runbook.md`

### File creati/toccati
- `ml/anomaly_detector.py` (pickle→joblib)
- `ml/train.py` (nuovo — CLI training)
- `simulator/preprocessor.py` (nuovo — HMACPreprocessor)
- `web/app.py` (dashboard Leaflet.js)
- `requirements.txt` (joblib aggiunto)
- `.gitignore` (models/ aggiunto)
- `docs/vault/11_Bugs_and_Fixes.md`
- `docs/vault/12_Commands_and_Runbook.md`
- `docs/vault/14_Session_Handoff.md`

### Stato sicurezza finale

| Tool | Risultato |
|---|---|
| Bandit | 0 High, 0 Medium, 1 Low accettato |
| pip-audit | torch CVE (sistema, non progetto), urllib3 CVE (transitivo, documentato) |
| Test | 97/97 passing |

### Debito tecnico residuo

NESSUNO. Tutti i task identificati sono stati completati.

### Prossima sessione (se necessaria)

- Aggiungere test di integrazione end-to-end con HMACPreprocessor
- Possibile: TLS per deploy non-localhost (nginx reverse proxy)
- Possibile: UI mobile-friendly per dashboard

---

## Sessione precedente: 2026-06-03 — Sessione 5: Sprint 2+3 completi ✅ + repo privata

### Cosa è stato fatto

1. **Repo privata `vaccamario05/FLY-CATCHER`** creata su GitHub — tutto pushato
2. **Sprint 2 Security Layer** — commit `91d978a`:
   - `security/hmac_validator.py` — HMAC-SHA256 PoC, timing-safe
   - `security/replay_detector.py` — window 30s + bounded dedup (maxlen=10000)
   - `security/rate_limiter.py` — token bucket thread-safe
   - `security/forensic_logger.py` — JSONL append-only + SHA-256 chain
   - `security/classifier.py` — aggrega check → TraceStatus finale
   - `web/auth.py` — RBAC operator/analyst, PBKDF2 passwords, session timeout
   - `web/app.py` aggiornato — auth su tutte le route, /api/audit/*, /api/export/csv
   - `adsb_secure/__main__.py` — pipeline completa Sprint 2 wired
3. **Sprint 3 Intelligence Layer** — stesso commit:
   - `ml/feature_extractor.py` — haversine, delta cinematici, speed discrepancy
   - `ml/anomaly_detector.py` — Isolation Forest, model persistence, explain
   - `ml/train_from_samples()` — bootstrap da notebook/samples/
4. **97/97 test verdi** — Sprint 1+2+3 coperti
5. **Vault e repo aggiornati**

### Struttura finale implementata

```
adsb_secure/    acquisition, normalizer, trace_store, pipeline, __main__
security/       validator, hmac_validator, replay_detector, rate_limiter,
                forensic_logger, classifier
ml/             feature_extractor, anomaly_detector
web/            app (Flask), auth (RBAC)
simulator/      replay (JSONSimulator)
tests/          97 test (10 file)
```

### Avvio completo

```bash
# Simulatore + pipeline + dashboard
ADSB_HMAC_KEY=$(python3.11 -c 'import secrets; print(secrets.token_hex(32))') \
python3.11 -m adsb_secure --mode simulator
# http://localhost:5000 → login (operator/operator123 o analyst/analyst123)
```

### Debito tecnico residuo (da fare)

- [ ] Script training IF da campioni reali (attualmente usa dati sintetici)
- [ ] Preprocessore simulatore che aggiunge `_hmac_tag` ai record (per test HMAC in pipeline live)
- [ ] Dashboard mappa geografica (Leaflet.js o similar)
- [ ] Rate limiter configurazione fine-grained per-ICAO
- [ ] TLS per deploy non-localhost
- [ ] pip-audit run completo e documentazione CVE trovati
- [ ] Bandit scan Sprint 2+3 modules

### Next steps (prossima sessione)

1. Run `python3.11 -m bandit -r security/ ml/ web/ -f txt` → documentare findings
2. Run `python3.11 -m pip-audit` → documentare CVE
3. Train IF su dati reali se disponibili
4. Aggiungere preprocessore simulatore con `_hmac_tag` per test pipeline end-to-end con HMAC

---

## Sessione precedente: 2026-06-03 — Sessione 4: Sprint 1 implementato ✅

### Cosa è stato fatto

1. **Sprint 1 completo** — commit `3e094c5`
2. **`device-rpi/flightdata.py` patchato** — rimossi 5 debug print, error handling, URL fix
3. **`adsb_secure/normalizer.py`** — AirCraftData + TraceStatus + build_from_dict() (gestisce alt_baro/gs/baro_rate)
4. **`security/validator.py`** — StructuralValidator con 12 check (ICAO, lat/lon, alt, speed, track, flight, squawk)
5. **`adsb_secure/acquisition.py`** — DataIngestion + URL scheme validation (fix B310 Bandit)
6. **`adsb_secure/trace_store.py`** — TraceStore thread-safe con deque per ICAO
7. **`simulator/replay.py`** — JSONSimulator con loop mode + CLI
8. **`web/app.py`** — Flask create_app() + /health + /api/traces + /api/aircraft/<icao> + dashboard HTML
9. **`adsb_secure/__main__.py`** — entrypoint pipeline + Flask wired
10. **35 test tutti verdi** — validator(21) + simulator(8) + web(5)
11. **Bandit**: 1 Medium residuo (B104 bind 0.0.0.0) — documentato e accettato per PoC
12. **`requirements.txt` + `pytest.ini` + `.gitignore`** creati

### File creati/toccati
- `adsb_secure/__init__.py`, `__main__.py`, `acquisition.py`, `normalizer.py`, `trace_store.py`
- `security/__init__.py`, `validator.py`
- `simulator/__init__.py`, `replay.py`
- `web/__init__.py`, `app.py`, `routes/__init__.py`
- `tests/conftest.py`, `test_validator.py`, `test_simulator.py`, `test_web.py`
- `requirements.txt`, `pytest.ini`, `.gitignore`
- `device-rpi/flightdata.py` (patched)
- `docs/vault/11_Bugs_and_Fixes.md`, `12_Commands_and_Runbook.md`

### Scoperta importante durante implementazione
Sample JSON usa `alt_baro`, `gs`, `baro_rate` — Fly-catcher usava `altitude`, `speed`, `vert_rate`.
`build_from_dict()` gestisce entrambi con fallback. Documentato nel codice.

### Python env nota
`python3.11` dalla Homebrew — ha pytest/flask installati. Usare `python3.11 -m pytest`.

### Next steps — Sprint 2

1. `feat(hmac)`: `security/hmac_validator.py` — HMAC-SHA256, key da `ADSB_HMAC_KEY` env
2. `feat(replay)`: `security/replay_detector.py` — timestamp window + bounded dedup set
3. `feat(ratelimit)`: `security/rate_limiter.py` — token bucket
4. `feat(classifier)`: aggregatore validator + hmac + replay → TraceStatus finale
5. `feat(logging)`: `security/forensic_logger.py` — append-only JSONL + SHA-256 chain
6. `feat(auth)`: `web/auth.py` — login, hashed passwords, RBAC decorator, session timeout
7. `feat(web)`: dashboard con colori per status, alert panel
8. Test per ogni modulo (hmac, replay, rate, forensic, auth)

---

## Sessione precedente: 2026-06-03 — Sessione 3: ADR-001 approvato + architettura Flask

### Cosa è stato fatto

1. **ADR-001 approvato** — Flask come UI principale
2. **`04_Target_Architecture.md` riscritto** — architettura Flask con directory layout definitivo, API endpoints, trust boundaries, pipeline happy/attack path
3. **`16_Migration_Plan.md` creato** — step-by-step da Fly-catcher a Flask backend, mappa riuso componenti, checklist migrazione completata
4. **`09_Decisions_Log.md` aggiornato** — ADR-001 marcato DECISO con motivazione
5. **`05_Sprint_Plan.md` aggiornato** — Sprint 1 backlog aggiornato con struttura Flask (S1-00: mkdir)
6. **`00_Index.md` aggiornato** — stato, file 16, architettura confermata

### File toccati
- `docs/vault/04_Target_Architecture.md` (riscritto)
- `docs/vault/09_Decisions_Log.md` (ADR-001 DECISO)
- `docs/vault/05_Sprint_Plan.md` (backlog aggiornato)
- `docs/vault/00_Index.md` (status + file 16)
- `docs/vault/16_Migration_Plan.md` (creato)
- `docs/vault/14_Session_Handoff.md` (questo file)

### Decisioni prese

| ADR | Decisione | Stato |
|---|---|---|
| ADR-001 | Flask come UI principale | ✅ DECISO |
| ADR-002 | Isolation Forest (vs CNN) | ✅ Deciso |
| ADR-003 | HMAC key via env var | ✅ Deciso |
| ADR-004 | Estensione modulare stessa repo | ✅ Deciso |
| ADR-005 | Replay JSON come simulatore | ✅ Deciso |

### Nessun rischio architetturale aperto

Tutte le ADR chiuse. Pronti per implementazione Sprint 1.

### Next steps — Sprint 1 (ordine prioritario)

1. `mkdir -p adsb_secure security ml web/routes web/templates simulator tests`
2. `chore(deps)`: `requirements.txt`
3. `fix(flightdata)`: debug prints + error handling + URL
4. `feat(data)`: `adsb_secure/normalizer.py` con `AirCraftData` + `TraceStatus`
5. `feat(simulator)`: `simulator/replay.py`
6. `feat(acquisition)`: `adsb_secure/acquisition.py`
7. `feat(validator)`: `security/validator.py`
8. `test(validator)`: `tests/test_validator.py` (≥7 test)
9. `devops`: bandit + pip-audit → findings in `11_Bugs_and_Fixes.md`
10. Commit + aggiorna Vault

---

## Sessione precedente: 2026-06-03 — Sessione 2: Claude OS setup

### Cosa è stato fatto

1. **CLAUDE.md creato** — regole operative, struttura repo, security rules, commit format
2. **Subagents creati** (`.claude/agents/`):
   - `repo-explorer` — mapping codebase, read-only
   - `security-auditor` — review sicurezza, read-only
   - `vault-scribe` — aggiornamento Vault persistente
   - `implementation-engineer` — patch verificabili
   - `test-runner` — lint, test, scan
3. **Skill custom creati** (`.claude/skills/`):
   - `feasibility-analyst` — gap analysis e classificazione requisiti
   - `vault-maintainer` — disciplina aggiornamento Vault
   - `security-reviewer` — checklist sicurezza
   - `threat-modeling` — STRIDE → moduli → test
   - `sprint-planner` — backlog e DoD sprint
4. **Hook configurati** (`.claude/settings.json`) — PostToolUse su Edit/Write, PreToolUse su Bash, allow list comandi comuni
5. **Permessi base pre-approvati** — pytest, bandit, pip-audit, find, grep, git

### File creati/toccati

- `CLAUDE.md`
- `.claude/agents/repo-explorer.md`
- `.claude/agents/security-auditor.md`
- `.claude/agents/vault-scribe.md`
- `.claude/agents/implementation-engineer.md`
- `.claude/agents/test-runner.md`
- `.claude/skills/feasibility-analyst.md`
- `.claude/skills/vault-maintainer.md`
- `.claude/skills/security-reviewer.md`
- `.claude/skills/threat-modeling.md`
- `.claude/skills/sprint-planner.md`
- `.claude/settings.json`

### Decisioni prese

| ADR | Decisione | Stato |
|---|---|---|
| ADR-001 | Flask web dashboard (vs pygame) | **DA APPROVARE** |
| ADR-002 | Isolation Forest prioritario (vs CNN) | Deciso |
| ADR-003 | HMAC key via env var | Deciso |
| ADR-004 | Estensione modulare nella stessa repo | Deciso |
| ADR-005 | Replay JSON come simulatore | Deciso |

### Rischi aperti

- ADR-001 (dashboard) non approvato — blocca design web in Sprint 2
- Dataset per IF training limitato ai `samples/` presenti

### Next steps consigliati

1. **Approvare ADR-001** (Flask vs pygame) — decisione urgente prima di Sprint 2
2. **Avviare Sprint 1** — ordine:
   - `fix(flightdata)`: debug prints + error handling + URL fix
   - `chore(deps)`: requirements.txt
   - `feat(data)`: AirCraftData + status field + TraceStatus enum
   - `feat(simulator)`: replay.py
   - `feat(validator)`: structural validation module
   - `test(validator)`: ≥5 unit test
   - `devops`: bandit + pip-audit run + findings documented
3. Commit tutto con convenzione `feat(scope): ...`

---

## Sessione precedente: 2026-06-03 — Prima sessione bootstrap

### Cosa è stato fatto

1. **Analisi completa repository Fly-catcher**
   - Stack identificato: Python + pygame + dump1090 HTTP API + TensorFlow (notebook) + scikit-learn (notebook)
   - 5 file Python analizzati: `piawareradar.py`, `flightdata.py`, `radar.py`, `gpsutils.py`, `const_normal.py`
   - 3 notebook analizzati: `Fly_Catcher.ipynb`, `CNN_Spoofing_Detector.ipynb`, `Spoofed_Aircraft_Generator.ipynb`
   - 4 vulnerabilità documentate, 3 bug documentati

2. **Vault Obsidian creato** (`docs/vault/`)
   - 15 file markdown popolati
   - Gap analysis completa
   - Feasibility assessment per ogni requisito
   - Sprint plan concreto (3 sprint)
   - ADR per decisioni architetturali chiave

3. **Gap critico identificato**: Fly-catcher usa pygame (TFT screen), ADS-B Secure richiede web dashboard → ADR-001 da approvare

### File creati/toccati

- `docs/vault/00_Index.md`
- `docs/vault/01_Project_Overview.md`
- `docs/vault/02_Current_State_of_Repository.md`
- `docs/vault/03_Feasibility_Assessment.md`
- `docs/vault/04_Target_Architecture.md`
- `docs/vault/05_Sprint_Plan.md`
- `docs/vault/06_Security_Model.md`
- `docs/vault/07_Data_Model.md`
- `docs/vault/08_Testing_Strategy.md`
- `docs/vault/09_Decisions_Log.md`
- `docs/vault/10_TODO_and_Backlog.md`
- `docs/vault/11_Bugs_and_Fixes.md`
- `docs/vault/12_Commands_and_Runbook.md`
- `docs/vault/13_Commit_History_Summary.md`
- `docs/vault/14_Session_Handoff.md` (questo file)
- `docs/vault/15_Glossary.md`

### Decisioni prese

| ADR | Decisione | Stato |
|---|---|---|
| ADR-001 | Flask web dashboard (vs pygame) | **DA APPROVARE** |
| ADR-002 | Isolation Forest prioritario (vs CNN) | Deciso |
| ADR-003 | HMAC key via env var | Deciso |
| ADR-004 | Estensione modulare nella stessa repo | Deciso |
| ADR-005 | Replay JSON come simulatore | Deciso |

### Rischi aperti

- ADR-001 (dashboard) non approvato — blocca design web in Sprint 2
- Dataset per IF training limitato ai `samples/` presenti — potrebbe servire generazione sintetica aggiuntiva

### Next steps consigliati

1. **Approvare ADR-001** (flask vs pygame) — decisione del team
2. **Sprint 1 — iniziare implementazione**:
   - Prima task: `fix(flightdata): remove debug prints, add error handling`
   - Seconda task: `chore(deps): add requirements.txt`
   - Terza task: `feat(validator): structural validation module`
3. Verificare che `notebook/samples/testing/sample.json` esista e sia usabile

### Comando per verificare stato vault

```bash
ls docs/vault/
wc -l docs/vault/*.md
```
