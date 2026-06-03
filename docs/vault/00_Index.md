# ADS-B Secure — Vault Index

## Stato progetto

| Campo | Valore |
|---|---|
| **Fase corrente** | Sprint 1 — Foundation (non ancora iniziata) |
| **Ultimo aggiornamento Vault** | 2026-06-03 |
| **Repository base** | Fly-catcher (ANG13T) |
| **Sessione corrente** | Prima sessione — Feasibility Analysis + Vault Bootstrap |

## Mappa del Vault

| File | Contenuto |
|---|---|
| [[01_Project_Overview]] | Scopo, relazione con Fly-catcher, obiettivi tecnici |
| [[02_Current_State_of_Repository]] | Stack reale, architettura osservata, moduli |
| [[03_Feasibility_Assessment]] | Analisi fattibilità per requisito |
| [[04_Target_Architecture]] | Architettura target ADS-B Secure |
| [[05_Sprint_Plan]] | Sprint 1/2/3 con task concreti |
| [[06_Security_Model]] | Minacce, mitigazioni, STRIDE |
| [[07_Data_Model]] | Strutture dati: pacchetti, tracce, log, utenti |
| [[08_Testing_Strategy]] | Test plan per ogni sprint |
| [[09_Decisions_Log]] | ADR — decisioni architetturali tracciate |
| [[10_TODO_and_Backlog]] | Task aperte, priorità, blockers |
| [[11_Bugs_and_Fixes]] | Bug trovati, root cause, fix |
| [[12_Commands_and_Runbook]] | Setup, avvio, test, debug |
| [[13_Commit_History_Summary]] | Riassunto semantico commit rilevanti |
| [[14_Session_Handoff]] | Stato sessione corrente e next steps |
| [[15_Glossary]] | Termini ADS-B, security, progetto |
| [[16_Migration_Plan]] | Piano migrazione Fly-catcher → Flask backend |

## Quick Status

```
Foundation Layer  [x] COMPLETATO — commit 3e094c5
Security Layer    [ ] Non iniziato (Sprint 2)
Intelligence Layer[ ] Non iniziato (Sprint 3)
Vault             [x] Aggiornato
Feasibility       [x] Completato
Sprint Plan       [x] Approvato
Claude OS         [x] CLAUDE.md + agents + skills + hooks
ADR-001 Flask     [x] APPROVATO — implementato
Tests             [x] 35/35 passing
Bandit            [x] 1 Medium residuo (B104, accettato)
```

## Architettura confermata

Flask = dashboard/API principale. pygame = legacy opzionale su RPi.
Pipeline modulare: `security/` → `ml/` → `web/`
Vedi [[04_Target_Architecture]] per diagramma aggiornato.
