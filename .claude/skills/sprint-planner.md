---
name: sprint-planner
description: Translates requirements and feasibility into concrete sprint backlogs. Use when scoping a new sprint, reprioritizing tasks, or breaking down a large feature into implementable increments.
---

# Sprint Planner Skill

## Reference documents

Before planning, read:
- `docs/vault/03_Feasibility_Assessment.md` — what is implementable
- `docs/vault/05_Sprint_Plan.md` — current sprint backlogs
- `docs/vault/10_TODO_and_Backlog.md` — open tasks and blockers
- `docs/vault/09_Decisions_Log.md` — architectural decisions

## Sprint structure

Each sprint must have:
- **Goal**: one sentence — what does this sprint deliver?
- **Backlog**: table with ID, task, type, priority
- **Definition of Done**: measurable criteria
- **Dependencies**: what must be done first

## Task types

| Type | Definition |
|---|---|
| Foundation | Core data flow, parsing, normalization |
| Security | Validation, HMAC, replay, rate limit, logging, auth |
| ML | Feature extraction, model, scoring |
| Web | Dashboard, routes, frontend |
| Testing | Unit tests, integration tests, misuse case tests |
| DevSecOps | Bandit, pip-audit, requirements.txt |
| Hygiene | Bug fixes, dead code removal, refactoring |
| Docs | Vault updates, runbook, commit history |

## Sizing rules

- A task should be completable in < 4 hours
- If bigger → split into subtasks
- No task touches more than 3 files
- Every security task has a corresponding test task

## Priority rules

1. **Alta** — blocks other tasks, or fixes active security issue
2. **Media** — needed for sprint goal but not blocking
3. **Bassa** — nice to have, can defer

## Sprint 1 checklist (Foundation)

Before closing Sprint 1, verify:
- [ ] requirements.txt exists with pinned versions
- [ ] `simulator/replay.py` works with sample data
- [ ] `security/validator.py` rejects malformed packets
- [ ] `AirCraftData.status` field exists and is always set
- [ ] Bandit scan done, findings documented
- [ ] pip-audit done, findings documented
- [ ] ≥ 5 unit tests for validator passing

## Sprint 2 checklist (Security Layer)

Before closing Sprint 2, verify:
- [ ] HMAC check works on preprocessed data
- [ ] Replay detection rejects duplicate/old packets
- [ ] Rate limiter active at configured threshold
- [ ] Forensic logger: hash chain verified
- [ ] Flask dashboard: tracce con status colorato
- [ ] Login: 2 ruoli (operator, analyst) funzionanti
- [ ] All security layer tests passing

## Sprint 3 checklist (Intelligence Layer)

Before closing Sprint 3, verify:
- [ ] IF trained on available samples
- [ ] Ghost aircraft detected in simulation test
- [ ] FP rate ≤ 5% on validation set
- [ ] Dashboard: anomaly_score + reason visible
- [ ] Audit API with filters working
- [ ] CSV export for analyst role
- [ ] All MC test cases passing

## Output format

When producing a sprint plan, output:

```markdown
## Sprint N — [Name] ([duration])

**Goal**: [one sentence]

### Backlog

| ID | Task | Type | Priority |
|---|---|---|---|
| SN-01 | ... | Security | Alta |

### Definition of Done
- [ ] criterion 1
- [ ] criterion 2

### Dependencies
- Requires: Sprint N-1 complete
- Blocks: Sprint N+1
```
