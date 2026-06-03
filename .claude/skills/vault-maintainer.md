---
name: vault-maintainer
description: Keeps docs/vault/ accurate and current. Use at end of every session, after architectural decisions, after bug discoveries, and after sprint completions.
---

# Vault Maintainer Skill

## Purpose

The Vault at `docs/vault/` is the project's persistent memory across Claude Code sessions. Without it, context is lost between conversations. Keep it accurate.

## Trigger → Action mapping

| Event | Required update |
|---|---|
| Architecture decision made | `09_Decisions_Log.md` — add ADR |
| New module designed or built | `04_Target_Architecture.md` — add to diagram + table |
| Bug found | `11_Bugs_and_Fixes.md` — add entry with `[SECURITY-NNN]` or `[BUG-NNN]` |
| Bug fixed | `11_Bugs_and_Fixes.md` — update status to Risolto |
| Sprint task started | `05_Sprint_Plan.md` — mark in_progress |
| Sprint task done | `05_Sprint_Plan.md` + `10_TODO_and_Backlog.md` |
| New command discovered | `12_Commands_and_Runbook.md` — add under correct section |
| Session ending | `14_Session_Handoff.md` — full update |
| Feasibility changes | `03_Feasibility_Assessment.md` |
| Security control added | `06_Security_Model.md` — update "Controlli implementati" |
| Test case added | `08_Testing_Strategy.md` — add to table |
| Important commit | `13_Commit_History_Summary.md` — add summary |

## Session handoff (end of every session)

Always update `14_Session_Handoff.md` with:

1. Date + session title
2. What was accomplished (specific files changed)
3. Files created or modified
4. Decisions made (ADR references)
5. Risks still open
6. Exact next steps for next session (in priority order)

## Index maintenance

`00_Index.md` must reflect:
- Current sprint status
- Quick project status (Foundation/Security/Intelligence checkboxes)
- Critical open decisions

## Consistency checks

Before writing, verify:
- Sprint task IDs match between `05_Sprint_Plan.md` and `10_TODO_and_Backlog.md`
- Bug IDs are sequential (SECURITY-001, 002; BUG-001, 002...)
- ADR numbers are sequential
- All new modules appear in `04_Target_Architecture.md`

## Rule

**Read the file before editing.** Use Read tool to get current content, then Edit for targeted updates.
