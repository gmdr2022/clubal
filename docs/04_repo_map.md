# 04_REPO_MAP — Structural Map of CLUBAL

This document provides a fast structural understanding of the repository.

- It is **not** product documentation.
- It is an engineering **navigation guide**.

---

## Documentation policy (evergreen)

Docs under `docs/` should be **stable and low-maintenance**.

Update documentation only when there is a **real contract change**, such as:

- module boundary / public API changes
- significant architecture changes
- distribution, commercial, or legal requirements

Avoid updating docs for every roadmap step or minor refactor.

---

## 1. High-Level Architecture

CLUBAL is structured in responsibility layers:

- `core/` → pure logic (no UI side-effects)
- `infra/` → IO and integrations (logs, Excel loading)
- `ui/` → Tkinter UI modules and extracted rendering helpers
- `app/` → runtime orchestration helpers (refresh pipeline, tick scheduling)
- `weather/` → canonical weather backend package (cache/net/icons/forecast/service)
- root shims → compatibility re-exports to preserve imports (`weather_service.py`, `ui/header_weather.py`)
- root entrypoint → `clubal.py` orchestrates wiring and the main screen

Long-term goal: keep `clubal.py` thin and delegate responsibilities to the folders above.

---

## 2. Directory Responsibilities

### `core/`

Contains:
- agenda filtering logic
- date and PT-BR text formatting
- card metrics
- domain models
- environment/bootstrap helpers (pure)

Rules:
- no Tkinter imports
- no UI drawing
- no direct file IO (except clearly isolated helpers)

---

### `infra/`

Contains:
- logging manager
- Excel loader
- integration utilities

Rules:
- can perform IO
- should not perform layout decisions
- should not contain UI widget code

---

### `ui/`

Contains:
- header layout logic
- layout math
- UI widgets/cards
- extracted rendering helpers

Rules:
- can use Tkinter
- must not contain business rules
- must not perform Excel reading
- must not embed schedule filtering logic

Notes:
- `ui/header_weather.py` is a **compatibility shim** that re-exports `WeatherCard`.

---

### `app/`

Contains:
- refresh/update pipeline helpers
- tick scheduling and housekeeping helpers
- runtime state helpers

Rules:
- may coordinate across `core/`, `infra/`, `ui/`, `weather/`
- should not accumulate UI drawing/layout logic
- should not absorb domain rules that belong to `core/`

---

### `weather/`

Canonical weather backend package.

Contains:
- cache IO
- network helpers
- official icon resolution
- forecast parsing
- service/facade API

Rules:
- no UI widget construction
- no Tkinter drawing/layout
- returns structured data and cached results

Compatibility:
- `weather_service.py` (repository root) is a **shim** that re-exports the canonical API from `weather/`.

---

### `graphics/`

Contains:
- logos
- UI images
- icon assets

Rule:
- packaging must include these assets for TV/Windows deployments.

---

### `docs/`

Contains:
- roadmap and engineering documentation

Rule:
- keep docs evergreen; update only when contracts/architecture/distribution require it.

---

## 3. Key Root Files

### `clubal.py`

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
- delegate runtime orchestration to `app/`

### `weather_service.py`

Compatibility shim (do not expand).

Rules:
- preserve import compatibility (`import weather_service as weather_mod`)
- canonical implementation lives in `weather/`

---

## 4. Spreadsheet Model

Repository version:
- `grade_template.xlsx`

Runtime version:
- `grade.xlsx` (local only)

Never commit:
- `grade.xlsx`

---

## 5. Safe Refactor Rules

When refactoring:

1. Move, do not rewrite.
2. Preserve behavior.
3. Keep module boundaries clean.
4. Never mix UI drawing and domain logic.
5. Avoid reopening stable modules without regression evidence.

---

## 6. When to update this document

Update this file only when one of these changes happens:

- new top-level folder/responsibility added/removed
- a shim becomes canonical (or canonical becomes shim)
- a public module contract changes
- distribution/packaging constraints change

Otherwise, keep it short and structural.