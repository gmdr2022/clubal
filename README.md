# CLUBAL — Club Agenda Live

CLUBAL is a lightweight **Python + Tkinter** digital signage application built for institutional screens (PCs/TVs), including low-end or restricted Windows machines and offline/unstable networks.

Design goals:

- **Offline-first** (graceful degradation)
- **Fast startup** and low resource usage
- **Simple operation** (TV-friendly)
- **Modular, maintainable codebase** (incremental refactors without behavior changes)

---

## What it does

- Reads an Excel schedule and shows **AGORA** (Now) and **PRÓXIMAS** (Next) items.
- Shows a header with date/time and operational info.
- Optionally shows weather with local cache and icon handling.

---

## Tech stack

- Python
- Tkinter
- openpyxl
- Pillow (optional, recommended for better PNG compatibility)

---

## Repository structure

```text
app/                 runtime orchestration helpers (refresh/ticks/scheduling)
core/                domain logic (agenda, text/date helpers, metrics, bootstrap helpers)
docs/                documentation (prefer stable/evergreen docs)
graphics/            logos and visual assets
infra/               IO/integration helpers (logging, xlsx loading)
ui/                  UI modules and widgets
weather/             modularized weather backend package (canonical implementation)

clubal.py            main application entrypoint / orchestrator
weather_service.py   weather backend compatibility shim (re-exports from weather/)
grade_template.xlsx  repository spreadsheet template (versioned)
```

---

## Key entry points (where to change what)

### App startup / orchestration

- `clubal.py`
- `app/` (tick scheduling + refresh pipeline)

Use when working on:
- startup wiring
- screen orchestration
- tick timing / scheduling

### Agenda (AGORA / PRÓXIMAS)

- `core/agenda.py`
- `infra/xlsx_loader.py`
- `core/card_metrics.py`

Use when working on:
- schedule parsing
- filtering / time windows
- progress/remaining-time bars

### Weather (backend)

Canonical implementation:
- `weather/facade.py` (public API)
- `weather/*` (cache/net/icons/forecast/service)

Compatibility:
- `weather_service.py` keeps legacy imports working (shim)

Use when working on:
- fetching forecast
- cache policy
- offline fallback

### Weather (UI)

- `ui/weather_card.py` (WeatherCard widget)
- `ui/header_weather.py` (compat shim → WeatherCard)
- `ui/weather_card_marquee.py` (marquee helpers)
- `ui/weather_card_draw.py` (drawing helpers)
- `ui/weather_card_icons_ui.py` (icon UI helpers)

Use when working on:
- WeatherCard layout/render
- marquee behavior
- icon placement

### Logging / diagnostics

- `infra/logging_manager.py`

Use when working on:
- log paths
- rotation
- operational traces

---

## Spreadsheet model

- `grade_template.xlsx` is the **versioned** template kept in the repository.
- `grade.xlsx` is the **local runtime** schedule file.

Important:
- Do **not** commit `grade.xlsx`.

---

## Documentation philosophy (important)

Docs in `docs/` should be **stable and evergreen** whenever possible.

- Avoid updating docs for every roadmap step.
- Update docs only for **real contract changes**:
  - breaking API/module boundaries
  - significant architecture changes
  - distribution/commercial/legal requirements

This keeps production moving and prevents docs becoming a maintenance tax.

---

## Operational principles

CLUBAL prioritizes stability over novelty:

- Preserve offline-first behavior.
- Prefer small, low-risk refactors.
- Keep `clubal.py` as an orchestrator (avoid turning it into a monolith).
- Keep shims (`weather_service.py`, `ui/header_weather.py`) to preserve import compatibility.

---

## Assets

- `graphics/` contains logos and UI images.
- For TV/Windows packaging, ensure assets are bundled with the build.

