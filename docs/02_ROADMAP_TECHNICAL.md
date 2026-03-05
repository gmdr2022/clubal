# 02_ROADMAP_TECHNICAL — Technical Roadmap (Evergreen)

This document defines the **technical sequencing and guardrails** for CLUBAL.

It is intentionally **not** a progress tracker. Progress should be inferred from:
- the Git history (commits)
- issues/tasks (if used)

---

## Documentation policy (evergreen)

Docs under `docs/` should be **stable and low-maintenance**.

Update documentation only when there is a **real contract change**, such as:
- module boundary / public API changes
- significant architecture changes
- distribution, commercial, or legal requirements

Avoid updating docs for every completed step.

---

## 1) Roadmap philosophy

CLUBAL must stay:

- **offline-first**
- **portable / restricted-environment tolerant**
- **low resource usage**
- **event-driven** (Tkinter `after()` scheduling)
- **behavior-preserving** during refactors (move → wrap → verify → only then improve)

Refactors should be incremental and reversible.

---

## 2) Non-negotiable engineering constraints

- Never crash due to missing permissions (no-write environments must still run).
- Internet is optional (network failures must degrade gracefully).
- Avoid tight loops and aggressive polling.
- Maintain import compatibility when multiple modules depend on a path (use thin shims).
- Keep `clubal.py` trending toward **orchestration**, not a helper dump.
- Keep UI concerns in `ui/`, domain logic in `core/`, IO in `infra/`, orchestration in `app/`, backend weather in `weather/`.

---

## 3) Preferred sequencing (major workstreams)

This order is designed to reduce risk and avoid refactor churn.

### A) Foundation & Runtime Safety
Goals:
- stable boot/runtime context
- path policy + write validation
- logging behavior that never breaks runtime

Typical scope:
- environment detection + path resolution
- “no-write” fallbacks
- logging manager integration

### B) UI System Foundations
Goals:
- consistent UI layout rules
- safe rendering primitives

Typical scope:
- shared layout metrics/constants
- extracted UI helpers (frames, drawing)
- reduce duplicate UI logic

### C) Domain & IO Separation (Agenda)
Goals:
- keep schedule logic pure and testable
- keep Excel IO isolated

Typical scope:
- parsing in `infra/`
- filtering/metrics in `core/`
- UI rendering in `ui/`

### D) Weather Backend Packageization
Goals:
- backend weather logic isolated from UI
- canonical API with compatibility shims

Typical scope:
- `weather/` canonical implementation
- `weather_service.py` shim preserved
- caching + network timeouts + graceful offline behavior

### E) Widget Modularization (UI WeatherCard and other cards)
Goals:
- reduce large UI files without behavior changes
- move helpers into focused modules

Typical scope:
- split marquee / drawing / icon UI
- keep `ui/header_weather.py` shim stable
- preserve WeatherCard public API

### F) Main Screen Orchestration
Goals:
- consolidate refresh/update pipeline
- consolidate tick scheduling

Typical scope:
- `app/refresh_pipeline.py`
- `app/tick_runtime.py`
- clear boundaries between “compute” and “render”

### G) Packaging & Distribution Readiness
Goals:
- reliable EXE build (Windows + TV)
- asset bundling
- minimal external dependencies

Typical scope:
- PyInstaller build rules
- include Pillow when needed for PNG compatibility
- ensure Windows trust store / SSL behavior is reliable where applicable
- bundle `graphics/` and required assets
- portable mode considerations

### H) Operational Hardening
Goals:
- long uptime
- graceful recovery from transient failures

Typical scope:
- cache housekeeping
- defensive network handling
- safe reload flows
- diagnostics improvements without polluting UI logic

---

## 4) Definition of “done” for a technical refactor

A refactor step is done only when:

- app runs normally on at least one target environment
- UI behavior is unchanged (unless a confirmed bug fix)
- “Problems” / lint is clean enough for the project standard
- change is committed with a clear message

---

## 5) What belongs in docs vs code

Docs should define:
- stable structure
- stable contracts/boundaries
- stable sequencing rules

Docs should NOT attempt to track:
- exact “phase completion”
- current TODO lists
- daily progress notes

Those should live in:
- Git commits / issues / task notes (if used)

---

## 6) When to update this file

Update only if:
- the sequencing changes materially
- a new major workstream is added/removed
- distribution constraints change (commercial/legal/packaging)

Otherwise, keep it evergreen.