# 05_MODULE_CONTRACTS — Module Boundaries, Responsibilities, and Safe Change Rules

This document defines practical contracts between the main structural parts of CLUBAL.

Purpose:

- Reduce architectural drift
- Make maintenance safer
- Clarify where new code should live
- Preserve behavior while modularizing

---

## Documentation policy (evergreen)

Docs under `docs/` should be **stable and low-maintenance**.

Update documentation only when there is a **real contract change**, such as:

- module boundary / public API changes
- significant architecture changes
- distribution, commercial, or legal requirements

Avoid updating docs for every roadmap step or minor refactor.

---

## 1) Architectural intent

CLUBAL should evolve toward predictable responsibility layers:

- `clubal.py` → entrypoint + high-level orchestration
- `app/` → runtime scheduling/orchestration helpers (refresh pipeline, ticks)
- `ui/` → Tkinter widgets, layout math, rendering helpers
- `core/` → pure logic (agenda, text/date helpers, metrics, models)
- `infra/` → IO + integrations (logging, Excel loading)
- `weather/` → canonical weather backend package

Compatibility shims exist to preserve imports:

- `weather_service.py` (repo root) → **shim** re-exporting the canonical API from `weather/`
- `ui/header_weather.py` → **shim** re-exporting `WeatherCard` from `ui/weather_card.py`

Shims must stay thin and stable.

---

## 2) Global rules

### 2.1 Preserve runtime behavior

When extracting/moving code:

1. Preserve visible behavior (UI output)
2. Preserve refresh rhythm / scheduling
3. Preserve AGORA / PRÓXIMAS semantics
4. Preserve offline-first behavior
5. Preserve portable / restricted-environment compatibility

A refactor is only “good” if the running app remains functionally equivalent (unless fixing a confirmed bug).

### 2.2 Prefer moving over rewriting

When reducing a large file:

- extract existing logic with minimal edits
- introduce wrappers before changing internals
- only normalize structure after stability is proven

### 2.3 Keep import compatibility

If an import path is used by multiple modules, prefer:

- keep the old import working via a **shim**
- move canonical code behind the shim

Do not remove shims unless a deliberate breaking change is accepted.

---

## 3) Safe dependency flow

Preferred direction:

- `clubal.py` and `app/` may call **everything** needed to orchestrate runtime.
- `ui/` may call `core/` for **pure formatting/metrics** helpers.
- `infra/` provides IO helpers used by orchestrators (and occasionally by `core/` only if the boundary remains clean).
- `core/` should not import `ui/` or Tkinter.
- `weather/` must not import `ui/`.

Avoid cyclic imports. If a cycle appears, introduce a small helper module in the correct layer.

---

## 4) Root entrypoint contract — `clubal.py`

### Purpose

- Instantiate the app
- Wire modules together
- Coordinate refresh cycles
- Schedule ticks
- Bind UI and domain

### Allowed responsibilities

- high-level orchestration
- calling `app/` runtime helpers
- composing UI widgets from `ui/`
- invoking domain logic from `core/`
- invoking IO from `infra/`

### Must avoid

- becoming a dumping ground for helper functions
- embedding domain rules that belong in `core/`
- embedding low-level IO that belongs in `infra/`

---

## 5) Runtime orchestration contract — `app/`

### Purpose

- Run the refresh/update pipeline
- Schedule ticks and housekeeping
- Hold runtime coordination helpers (state, timers)

### Allowed responsibilities

- orchestrate calls across `core/`, `infra/`, `ui/`, `weather/`
- handle tick scheduling (`after()` coordination)
- decide when to reload Excel and when to recompute

### Must avoid

- adding UI drawing/layout logic (belongs in `ui/`)
- absorbing domain rules (belongs in `core/`)
- duplicating IO implementations (belongs in `infra/`)

---

## 6) Core contract — `core/`

### Purpose

- Pure logic: deterministic functions/classes
- Agenda filtering and time-window logic
- Text/date formatting helpers
- Card metrics and calculations

### Allowed contents

- models / dataclasses
- time computations
- string normalization
- progress and metric calculations

### Must avoid

- Tkinter imports
- direct file IO (unless explicitly isolated and justified)
- network calls
- caching logic

---

## 7) Infrastructure contract — `infra/`

### Purpose

- IO and integrations

### Allowed responsibilities

- logging manager
- Excel reading/loading helpers
- runtime file operations

### Must avoid

- UI layout decisions
- embedding business/domain rules

---

## 8) UI contract — `ui/`

### Purpose

- Tkinter widgets and rendering
- layout math and geometry helpers
- extracted draw helpers

### Allowed responsibilities

- create/update Tkinter widgets
- perform canvas drawing
- keep UI caches (PhotoImage references, etc.)

### Must avoid

- schedule filtering logic
- Excel reading
- path policy / directory creation (belongs in bootstrap/infra)

### Stability note

UI refactors must preserve visual behavior unless there is a confirmed UX bug to fix.

---

## 9) Weather backend contract — `weather/` + `weather_service.py` shim

### Canonical implementation

- `weather/facade.py` is the canonical public API.
- `weather/*` contains the implementation (cache/net/icons/forecast/service).

### Shim rule

- `weather_service.py` (repo root) is a compatibility shim.
- It must keep `import weather_service as weather_mod` working.
- Do not add new logic to the shim.

### Must avoid

- importing Tkinter
- performing UI layout
- crashing the UI when offline (always degrade gracefully)

---

## 10) Spreadsheet contract

Repository reference:

- `grade_template.xlsx` (versioned)

Local runtime file:

- `grade.xlsx` (local only)

Rules:

- Never commit `grade.xlsx`.
- Parsing rules should live in `core/` (logic) + `infra/` (IO).

---

## 11) Assets contract — `graphics/`

### Purpose

- logos
- background images
- icon assets

Rules:

- Packaging must bundle `graphics/`.
- Prefer Pillow-compatible loading paths for reliability.

---

## 12) When to update this document

Update this file only when one of these changes happens:

- a new top-level layer is added/removed (`app/`, `weather/`, etc.)
- a public API path changes (imports used by multiple modules)
- shim/canonical roles change
- distribution/commercial/legal constraints change

Otherwise, keep it stable.

