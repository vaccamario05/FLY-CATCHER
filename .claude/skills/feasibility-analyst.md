---
name: feasibility-analyst
description: Produces gap analysis and feasibility assessment for ADS-B Secure requirements. Use when evaluating new features, assessing sprint scope, or responding to new spec changes.
---

# Feasibility Analyst Skill

## When to activate

- Evaluating a new requirement against the codebase
- Deciding whether to implement, mock, or defer a feature
- Updating `docs/vault/03_Feasibility_Assessment.md`
- Before proposing a new sprint task

## Classification system

| Level | Label | Meaning |
|---|---|---|
| A | **Already present** | Fly-catcher already does this |
| B | **Reusable with minor refactor** | Exists, needs adaptation |
| C | **Directly implementable** | New code, straightforward |
| D | **PoC / simulation only** | Requires missing infra or hardware |
| E | **Out of scope** | Infeasible in academic prototype context |

## Feasibility analysis template

For each requirement, answer:

```
Requirement: [ID and name]
Level: [A/B/C/D/E]
Evidence: [what in the codebase supports this assessment]
Dependencies: [what must exist first]
Risk: [Low/Medium/High + why]
Sprint: [which sprint this belongs to]
PoC note: [if D — what is simulated, what is real]
```

## Domain constraints (always apply)

1. ADS-B protocol is broadcast and unauthenticated — cannot be changed
2. HMAC applies only to simulated/preprocessed data in PoC context
3. System operates ONLY in receive+analyze mode, never transmit
4. Without SDR hardware: use `simulator/replay.py` + `notebook/samples/`
5. MLAT requires distributed physical infrastructure — always Level E
6. TESLA requires distributed time-sync infrastructure — always Level E

## Risk evaluation criteria

**High risk**:
- Requires hardware (SDR, RPi) not available in dev environment
- Requires external infrastructure (PKI, MLAT network, distributed time sync)
- Introduces TensorFlow in production pipeline (heavy dependency)
- Requires labeled attack dataset not available

**Medium risk**:
- ML model performance depends on training data quality
- Feature engineering for IF requires domain expertise
- Flask dashboard requires design + auth wiring

**Low risk**:
- Pure Python, stdlib or scikit-learn
- Deterministic logic (validator, replay detector, rate limiter)
- Standard logging patterns

## Quick wins (always consider)

1. Fix existing bugs in `device-rpi/` — immediate value, minimal risk
2. `requirements.txt` — zero risk, high value
3. `security/validator.py` — pure Python, testable, no external deps
4. `simulator/replay.py` — enables all Sprint 2+3 development without hardware

## Output format

Produce a table for `docs/vault/03_Feasibility_Assessment.md`:

| Requirement | ID | Level | Notes | Dependencies | Risk | Sprint |
|---|---|---|---|---|---|---|
| ... | ... | C | ... | ... | Low | 2 |
