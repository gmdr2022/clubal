# CLUBAL — Current Architecture

This document describes the architectural structure and runtime behavior of CLUBAL.
It focuses on **principles and stable structure**, not temporary implementation details.

---

## Documentation policy (evergreen)

Docs under `docs/` should be **stable and low-maintenance**.

Update documentation only when there is a **real contract change**, such as:

- module boundary / public API changes
- significant architecture changes
- distribution, commercial, or legal requirements

Avoid updating docs for every roadmap step or minor refactor.

---

## 1. Architectural Overview

CLUBAL follows a **centralized runtime context** model.

At startup, a bootstrap layer:

- detects the execution environment
- resolves path policy
- determines real write capability
- establishes logging and caching behavior (when possible)

Infrastructure decisions derive from runtime context instead of being re-implemented across modules.

---

## 2. Responsibility Layers

CLUBAL is structured by layers of responsibility:

- `core/` → pure logic (agenda rules, metrics, text/date helpers)
- `infra/` → IO/integration (logging, Excel loading)
- `ui/` → Tkinter widgets, layout and rendering helpers
- `app/` → orchestration helpers (refresh pipeline, tick scheduling)
- `weather/` → canonical weather backend package (cache/net/icons/forecast/service)

Compatibility shims exist to preserve stable imports:

- `weather_service.py` (repo root) → shim re-exporting canonical API from `weather/`
- `ui/header_weather.py` → shim re-exporting `WeatherCard` from `ui/weather_card.py`

---

## 3. Runtime Context Pattern

At startup:

- the application initializes a runtime context
- the context exposes resolved paths and capabilities
- modules consume context instead of resolving paths independently

This prevents environment-specific logic from spreading across the codebase.

---

## 4. Environment Detection

Execution modes are determined dynamically:

- installed execution
- portable execution
- restricted / no-write environment

The system performs **real write validation** to determine writable capability.

If writing is not possible:

- logs and cache may be disabled
- the application must continue safely
- no permission-related fatal errors are allowed

---

## 5. Path Resolution Policy

Path resolution is centralized for:

- application directory
- asset directory
- data directory
- writable root (if available)
- log directory (if available)
- cache directory (if available)

Rules:

- no feature module creates directories independently
- path decisions are derived from centralized policy

---

## 6. UI Structure

CLUBAL runs under a single Tkinter root.

Layout pattern:

HEADER
- logo
- date
- clock
- status widgets (including WeatherCard when enabled)

BODY
- two primary columns:
  - current activities (AGORA)
  - upcoming activities (PRÓXIMAS)

Update pattern:

- event scheduling via `after()`
- no aggressive loops or tight polling
- reuse existing widgets/canvas items where possible
- redraw only when necessary

---

## 7. Agenda System

Agenda is:

- data-driven
- local-first
- fully functional offline

Responsibilities:

- parse schedule data (via IO layer)
- filter by day and time windows
- determine active and upcoming activities
- compute temporal progress metrics
- update event-driven

Agenda behavior must remain stable during modularization unless fixing a confirmed bug.

---

## 8. Weather System (Backend + UI)

### Backend (`weather/`)

Behavior:

- online source when available
- local cache fallback
- short timeouts
- graceful degradation when offline

Weather failure must never crash the UI.

Canonical API:

- `weather/facade.py` is the public API of the weather package
- `weather_service.py` is a compatibility shim to preserve legacy imports

### UI (`ui/`)

- `ui/weather_card.py` provides the `WeatherCard` widget
- `ui/header_weather.py` is a compatibility shim re-exporting `WeatherCard`

UI concerns (rendering, marquee, icon placement) must not leak into the backend package.

---

## 9. Logging & IO

Logging and IO follow centralized path resolution.

If no writable directory exists:

- logging becomes a no-op
- caching may be disabled
- execution continues safely

This ensures compatibility with:

- corporate restricted PCs
- portable deployments
- Windows TVs / constrained environments

---

## 10. Stability rules (non-negotiable)

- never fail due to lack of write permission
- never depend on constant internet
- avoid aggressive loops (event-driven scheduling only)
- preserve UI stability during rotation
- preserve import compatibility via shims when necessary
- prefer small refactors that move code without rewriting behavior