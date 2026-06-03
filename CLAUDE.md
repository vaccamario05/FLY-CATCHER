# ADS-B Secure — Claude Operating Rules

## Vault — Memoria persistente

**Ogni sessione inizia leggendo:**
```
docs/vault/14_Session_Handoff.md   ← stato corrente
docs/vault/00_Index.md             ← mappa progetto
docs/vault/10_TODO_and_Backlog.md  ← task aperte
```

Ogni modifica significativa → aggiorna il Vault prima del commit.

## Regole di lavoro

1. **Leggi prima, scrivi dopo** — mai modificare un file senza averlo letto
2. **Patch piccole e verificabili** — no riscritture massive
3. **Estendi, non riscrivere** — `device-rpi/` è il foundation layer, preservalo
4. **Distingui sempre**: implementazione reale / PoC simulato / fuori scope
5. **Input ADS-B = untrusted** — ogni dato dal protocollo va validato

## Sicurezza (non negoziabile)

- Niente hardcoded secrets — chiavi via `os.environ`
- HMAC validation è PoC su dati simulati, **non** modifica il protocollo reale
- In caso di dubbio → classifica `SUSPICIOUS` o `UNVERIFIED`, mai `VALID`
- Vulnerabilità trovate → prefisso `[SECURITY]` + documentare in `docs/vault/11_Bugs_and_Fixes.md`
- Log append-only con SHA-256 hash chaining per eventi di sicurezza

## Subagents disponibili (`.claude/agents/`)

| Agent | Quando usarlo |
|---|---|
| `repo-explorer` | Prima di ogni modifica — mapping codebase |
| `security-auditor` | Review input validation, secrets, logging |
| `vault-scribe` | Aggiornamento documentazione persistente |
| `implementation-engineer` | Patch verificabili e commit semantici |
| `test-runner` | Lint, test, smoke test |

## Commit format

```
feat(validator): add structural validation for ADS-B packets
fix(flightdata): remove debug prints and add error handling
feat(hmac): add HMAC-SHA256 verification module (PoC)
test(security): add replay detection unit tests
docs(vault): update sprint 1 progress and handoff
chore(deps): add requirements.txt with pinned versions
```

## Stack reale (da non dimenticare)

- **Foundation**: Python 3 + pygame + dump1090 HTTP API
- **Dev without hardware**: `simulator/replay.py` → replay JSON da `notebook/samples/`
- **ML**: scikit-learn Isolation Forest (pipeline) + Keras CNN (offline, opzionale)
- **Web dashboard**: Flask + RBAC (Sprint 2+)

## Struttura directory

```
fly-catcher/
├── device-rpi/        ← Foundation Fly-catcher (non toccare senza motivo)
├── security/          ← Sprint 2: validator, hmac, replay, rate, forensic_logger
├── web/               ← Sprint 2: Flask app, auth, routes
├── ml/                ← Sprint 3: feature_extractor, anomaly_detector
├── simulator/         ← Sprint 1: replay.py
├── tests/             ← Sprint 1+: test unitari e integration
├── notebook/          ← Notebook ML esistenti (non modificare)
├── docs/vault/        ← Vault Obsidian (memoria persistente)
└── .claude/           ← Configurazione Claude Code
```

## Dettagli tecnici

→ Vedi `docs/vault/04_Target_Architecture.md`
→ Vedi `docs/vault/06_Security_Model.md`
→ Vedi `docs/vault/05_Sprint_Plan.md`
