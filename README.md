# CLUBAL — Club Agenda Live

CLUBAL is a lightweight digital signage application built with **Python + Tkinter** for institutional screens, TVs, low-end PCs, and portable/offline environments.

It is designed to remain operational in places where heavier dashboard stacks are a bad fit:

- Windows TVs
- older or restricted corporate PCs
- unstable or offline environments
- portable / pendrive-style deployments

---

## Current project status

Current architectural direction is defined in:

- `docs/02_ROADMAP_TECHNICAL.md`
- `docs/03_ROADMAP_PRODUCT.md`

The current implementation priority is:

1. preserve runtime stability
2. preserve offline-first behavior
3. continue controlled modularization
4. reduce `clubal.py` into orchestration over time

---

## Tech stack

- **Python**
- **Tkinter**
- **openpyxl**
- **Pillow** (optional but important for better PNG/image compatibility)
- local Excel-based content source (`grade.xlsx` at runtime)

---

## Repository structure

```text
app/                 runtime/bootstrap integration helpers
core/                pure logic, domain helpers, metrics, text/date utilities, paths, models
docs/                roadmap and project documentation
graphics/            logos, icons and visual assets
infra/               IO/integration helpers such as logging and xlsx loading
ui/                  extracted UI modules and layout helpers
clubal.py            main application entrypoint / orchestrator
weather_service.py   weather backend module
grade_template.xlsx  repository spreadsheet template
```

---

## Entry points by concern

### Main runtime

- `clubal.py`
- `core/bootstrap.py`

Use these first when the task involves:

- app startup
- environment detection
- top-level wiring
- screen orchestration
- integration between modules

### Header UI

- `clubal.py`
- `ui/header_layout.py`
- `core/date_text.py`
- `core/ptbr_text.py`

Use these first when the task involves:

- header geometry
- date card text
- clock/date rendering
- logos
- top section layout

### Agenda / schedule logic

- `core/agenda.py`
- `core/card_metrics.py`
- `infra/xlsx_loader.py`

Use these first when the task involves:

- AGORA / PRÓXIMAS logic
- schedule filtering
- progress / remaining time
- Excel loading and reload flow

### Weather

- `weather_service.py`

Use this first when the task involves:

- forecast fetching
- weather cache
- offline weather fallback
- weather icon handling

### Logging / runtime diagnostics

- `infra/logging_manager.py`

Use this first when the task involves:

- logs
- rotation
- runtime diagnostics
- operational tracing

### Assets / branding

- `graphics/`

Use this first when the task involves:

- logos
- icons
- institutional branding
- client-specific image assets

---

## Runtime spreadsheet model

Repository reference:

- `grade_template.xlsx`

Local runtime file:

- `grade.xlsx`

Important:

- `grade_template.xlsx` is the versioned spreadsheet model kept in the repository
- `grade.xlsx` is the local working spreadsheet used by the application at runtime
- `grade.xlsx` must stay out of version control

---

## Local-only / ignored artifacts

The repository is intended to ignore local operational artifacts such as:

- `grade.xlsx`
- `.zip` artifacts
- temporary runtime outputs
- machine-specific generated files

---

## Rules for safe maintenance

### Prefer editing these first

- `core/` for pure logic
- `infra/` for IO/integration
- `ui/` for extracted UI modules

### Avoid expanding these responsibilities

- `clubal.py` should gradually become an orchestrator, not a dumping ground
- `weather_service.py` should not be reopened without real regression evidence
- stable agenda behavior should not be rewritten without a confirmed bug

### Preserve at all times

- offline-first execution
- portable compatibility
- Windows compatibility
- TV-friendly operation
- graceful degradation
- low resource usage

---

## Current modularization strategy

The current controlled modularization direction is:

1. keep behavior unchanged
2. move pure helpers out of `clubal.py`
3. move layout/math into dedicated UI modules
4. keep feature boundaries clear
5. only then reduce main-screen orchestration

This repository should evolve toward:

- thin entrypoint
- clearer module contracts
- safer maintenance
- lower regression risk

---

## Practical guidance for future edits

If the task is about...

- **startup / wiring** → start in `clubal.py`
- **header sizing/layout** → start in `ui/header_layout.py`
- **date strings / PT-BR formatting** → start in `core/date_text.py` and `core/ptbr_text.py`
- **schedule loading** → start in `infra/xlsx_loader.py`
- **AGORA / PRÓXIMAS behavior** → start in `core/agenda.py` and `core/card_metrics.py`
- **weather** → start in `weather_service.py`
- **logs** → start in `infra/logging_manager.py`

---

## Operational philosophy

CLUBAL is not just an “agenda with weather”.

It is a lightweight, resilient institutional communication runtime intended to support modular information delivery in constrained environments.

Agenda, weather, and future content blocks should remain replaceable modules over a stable runtime base.

