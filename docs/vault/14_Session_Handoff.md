# Session Handoff

## Ultima sessione: 2026-06-03 — Sessione 3: ADR-001 approvato + architettura Flask

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
