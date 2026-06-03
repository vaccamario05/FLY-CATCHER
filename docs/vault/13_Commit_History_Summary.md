# Commit History Summary

## Commit rilevanti Fly-catcher (upstream)

```
dadf7f5  Update README.md
808b741  feat: finish notebook        ← Notebook ML completato (CNN training + Fly_Catcher.ipynb)
563d861  Update README.md
83e38bb  Update README.md
cbf56e6  feat: update materials
```

**Osservazione**: L'ultimo commit significativo è `808b741` (notebook ML). 
Il repository è in stato stabile senza sviluppo attivo recente.
Tutto il codice sicurezza andrà nei commit successivi del team ADS-B Secure.

## Convenzioni commit ADS-B Secure

Usare Conventional Commits:

```
feat(validator): add structural validation for ADS-B packets
feat(hmac): add HMAC-SHA256 verification module (PoC)
feat(replay): add timestamp window and deduplication detection
feat(ratelimit): add token bucket rate limiter
feat(logging): add append-only forensic logger with SHA-256 chain
feat(web): add Flask dashboard with trace classification display
feat(auth): add RBAC with operator and analyst roles
feat(ml): add Isolation Forest anomaly detector
test(validator): add unit tests for structural validation
test(security): add misuse case integration tests
fix(flightdata): remove debug prints and add error handling
chore(deps): add requirements.txt with pinned versions
docs(vault): update session handoff and sprint progress
```

## Prossimi commit previsti (Sprint 1)

1. `chore(deps): add requirements.txt`
2. `fix(flightdata): remove debug prints, add error handling, fix URL usage`
3. `feat(validator): add structural validation module`
4. `feat(simulator): add JSON replay simulator`
5. `feat(data): extend AirCraftData with status and security fields`
6. `test(validator): add unit tests`
7. `docs(vault): update sprint 1 progress`
