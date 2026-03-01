# 04_REPO_MAP — Structural Map of CLUBAL

This document provides a fast structural understanding of the project.

It is not product documentation.
It is an engineering navigation guide.

---

## 1. High-Level Architecture

CLUBAL is structured in layered responsibility blocks:

- core → pure logic, no UI side-effects
- infra → IO and integration helpers
- ui → extracted layout and visual logic
- app/bootstrap → runtime wiring and environment setup
- root entrypoint → orchestration

The long-term goal is to keep `clubal.py` as a thin orchestrator.

---

## 2. Directory Responsibilities

### core/

Contains:
- agenda filtering logic
- date and PT-BR text formatting
- card metrics
- domain models
- environment detection helpers

Rules:
- no Tkinter imports here
- no UI drawing
- no direct file IO except clearly isolated helpers

---

### infra/

Contains:
- logging manager
- Excel loader
- integration utilities

Rules:
- can perform IO
- should not perform layout decisions
- should not contain UI widget code

---

### ui/

Contains:
- header layout logic
- layout math
- visual helpers
- card rendering helpers (when extracted)

Rules:
- can use Tkinter
- must not contain business rules
- must not perform Excel reading
- must not embed schedule logic

---

### weather_service.py

Standalone weather backend.

Rules:
- no UI drawing
- no Tkinter widget construction
- only returns structured data and cached results

---

### clubal.py

Main runtime entrypoint.

Responsibilities:
- instantiate app
- wire modules together
- coordinate refresh cycles
- schedule ticks
- bind UI and domain

Should gradually:
- delegate layout math to `ui/`
- delegate logic to `core/`
- delegate IO to `infra/`

---

## 3. Spreadsheet Model

Repository version:
- grade_template.xlsx

Runtime version:
- grade.xlsx (local only)

Never commit:
- grade.xlsx

---

## 4. Safe Refactor Rules

When refactoring:

1. Move, do not rewrite.
2. Preserve behavior.
3. Keep module boundaries clean.
4. Never mix UI drawing and domain logic.
5. Avoid re-opening stable modules without regression evidence.

---

## 5. Current Modularization Stage

Phase 2 — Controlled Extraction

Status:
- core helpers partially extracted
- header layout partially extracted
- further separation required

Next direction:
- reduce clubal.py surface
- increase clarity of module contracts
- avoid cross-import coupling

---

This file must stay short, structural, and pragmatic.

