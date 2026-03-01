# 05_MODULE_CONTRACTS — Module Boundaries, Responsibilities, and Safe Change Rules

This document defines the practical contracts between the main structural parts of CLUBAL.

Its purpose is to reduce architectural drift, make maintenance safer, and clarify where future code should live.

It is intentionally operational.
It should help answer questions such as:

- Where should this logic go?
- What is safe to change here?
- What must not be mixed in this module?
- What can call what?
- What should remain stable during Phase 2 modularization?

---

## 1. Architectural Intent

CLUBAL should evolve toward a predictable layered structure:

- **`clubal.py`** → application entrypoint, runtime orchestration, UI wiring
- **`ui/`** → layout logic, widget behavior, geometry helpers, rendering support
- **`core/`** → pure logic, domain helpers, text/date helpers, calculations, models
- **`infra/`** → file IO, logging, Excel integration, runtime support utilities
- **`weather_service.py`** → isolated weather backend with cache and offline fallback

The long-term objective is not aggressive abstraction.
The objective is **controlled separation with stable runtime behavior**.

That means:

- move code only when the destination is clearly better
- preserve behavior while modularizing
- avoid rewriting stable logic just to make files look cleaner
- reduce `clubal.py` gradually, not ideologically

---

## 2. Global Rules

These rules apply across the entire repository.

### 2.1 Preserve Runtime Behavior

When extracting or moving code:

1. preserve visible behavior
2. preserve refresh rhythm
3. preserve AGORA / PRÓXIMAS logic
4. preserve offline-first operation
5. preserve portable / constrained-environment compatibility

A refactor is only good if the running app stays functionally equivalent unless a real bug is being fixed.

---

### 2.2 Prefer Moving Over Rewriting

When reducing a large file:

- first extract existing logic with minimal changes
- only normalize structure after the extraction is stable
- only redesign APIs if the current boundary is clearly harmful

This repository favors **low-regression extraction** over elegant-but-risky rewrites.

---

### 2.3 Keep Responsibilities Narrow

Every file or module should become more legible over time.

That means avoiding:

- UI code performing domain decisions
- IO helpers performing layout decisions
- business logic embedded inside widget paint/update code
- runtime orchestration mixed with pure calculations

---

### 2.4 Respect Stable Areas

Do not reopen stable subsystems without evidence.

This is especially important for:

- `weather_service.py`
- already-stable agenda behavior
- Excel reload flow if working correctly
- proven runtime fallback behavior

A stable subsystem should only be touched if one of these is true:

- confirmed bug
- confirmed regression
- required architectural extraction with low risk
- clear maintenance win that does not destabilize runtime

---

## 3. Root Entrypoint Contract — `clubal.py`

## Purpose

`clubal.py` is the main application runtime entrypoint.

It is allowed to:

- instantiate the application
- bind modules together
- schedule ticks / refresh cycles
- coordinate UI updates
- hold transitional glue while modularization is still in progress

It should gradually become:

- thinner
- more declarative
- easier to reason about
- more orchestration-oriented

## Allowed Responsibilities

- top-level application bootstrap and lifecycle
- connection between UI, core logic, and infra helpers
- screen-level orchestration
- refresh scheduling and timing coordination
- transitional adapter methods during extractions

## Responsibilities That Should Leave Over Time

- pure calculations
- reusable formatting helpers
- layout math
- large widget-specific behavior blocks
- direct IO helpers not specific to runtime wiring

## Should Not Become

`clubal.py` should **not** become a permanent home for:

- new domain logic
- reusable card metrics
- PT-BR text helper collections
- spreadsheet parsing logic
- low-level asset utility functions when extraction is feasible

## Dependency Direction

`clubal.py` may depend on:

- `core/`
- `infra/`
- `ui/`
- `weather_service.py`

Other modules should avoid depending on `clubal.py`.

---

## 4. Core Contract — `core/`

## Purpose

`core/` contains pure or mostly pure logic.

This is the preferred home for logic that can be tested, reasoned about, or reused without needing Tkinter widgets or file reads.

## Typical Contents

- schedule filtering rules
- card metric calculations
- domain models
- date/text formatting helpers
- environment/path-related pure helpers
- small adapters that transform data without side effects

## Must Avoid

- widget creation
- canvas drawing
- Tkinter layout code
- direct Excel reads unless intentionally isolated and clearly justified
- view-specific rendering decisions

## Good Candidates for `core/`

If a piece of code answers any of these questions, it likely belongs in `core/`:

- Can this run without a window?
- Can this be reasoned about from inputs/outputs only?
- Is this a reusable rule, formatter, mapper, or calculation?
- Would another module benefit from calling this without UI knowledge?

## Dependency Direction

`core/` should not depend on `ui/`.

Prefer:

- `core/` independent
- `ui/` consuming `core/`
- `clubal.py` orchestrating both

---

## 5. Infrastructure Contract — `infra/`

## Purpose

`infra/` contains side-effectful helpers related to integration and runtime support.

This includes things like:

- file loading
- Excel interaction
- logging
- operational IO support

## Allowed Responsibilities

- read/write integration helpers
- logging sinks / log rotation support
- spreadsheet loading and reload utilities
- thin runtime support utilities with external side effects

## Must Avoid

- UI widget code
- business rule ownership
- schedule decisions that belong to domain logic
- layout-specific choices

## Design Principle

`infra/` should do the operational work and return structured data.
It should not decide how that data is rendered.

---

## 6. UI Contract — `ui/`

## Purpose

`ui/` is the home for extracted visual and layout-oriented logic.

This includes:

- geometry calculations
- widget-specific layout support
- view composition helpers
- rendering-side utility code

## Allowed Responsibilities

- Tkinter-dependent helpers
- layout math
- widget rendering support
- screen composition helpers
- visual state transitions that do not redefine business logic

## Must Avoid

- Excel parsing
- persistent IO
- weather fetching
- schedule/domain rules
- unrelated formatting logic that is better placed in `core/`

## Key Boundary Rule

`ui/` may depend on `core/` for values, labels, metrics, and decisions.
But `core/` must not depend on `ui/`.

---

## 7. Weather Backend Contract — `weather_service.py`

## Purpose

`weather_service.py` is an isolated backend module for weather acquisition, cache handling, and offline fallback.

## Allowed Responsibilities

- fetch remote weather data
- normalize weather payloads
- manage cache and fallback behavior
- manage weather icon/cache support related to backend concerns

## Must Avoid

- creating Tkinter widgets
- screen-specific rendering
- hard-wiring app layout behavior
- becoming a general-purpose UI helper module

## Stability Rule

This module should be considered **stable by default**.
Do not reopen it unless there is:

- a confirmed regression
- a confirmed operational need
- a contained extraction that reduces risk rather than increases it

---

## 8. Spreadsheet Contract

## Repository File

- `grade_template.xlsx`

## Local Runtime File

- `grade.xlsx`

## Rules

- `grade_template.xlsx` is the repository reference model
- `grade.xlsx` is local operational data
- `grade.xlsx` must not be committed
- runtime should continue to expect `grade.xlsx` locally unless intentionally redesigned later

## Practical Principle

The repository should preserve a clean reference spreadsheet without polluting commits with day-to-day schedule edits.

---

## 9. Asset Contract — `graphics/`

## Purpose

`graphics/` is the home for static visual assets such as:

- logos
- icons
- branding images
- client-specific graphic files

## Rules

- asset lookup may be handled in runtime/UI layers
- branding should stay externalized in assets when practical
- avoid hardcoding multiple alternative branding assets directly into logic when a path/lookup strategy is enough

## Must Avoid

- mixing generated operational files here
- keeping temporary archives or packaging artifacts here

---

## 10. Safe Dependency Flow

Preferred dependency direction:

```text
clubal.py -> ui/
clubal.py -> core/
clubal.py -> infra/
clubal.py -> weather_service.py
ui/ -> core/
infra/ -> core/   (only when truly useful and still clean)
```

Avoid or minimize:

```text
core/ -> ui/
ui/ -> infra/      (unless extremely justified)
weather_service.py -> ui/
weather_service.py -> clubal.py
```

The project does not need a rigid academic architecture.
It needs **clear enough flow to prevent drift**.

---

## 11. Phase 2 Refactor Priorities

Current Phase 2 direction should continue in this spirit:

1. extract pure helpers from `clubal.py`
2. extract layout/math into `ui/`
3. reduce file size and responsibility concentration
4. keep runtime behavior unchanged
5. only after stabilization, continue toward clearer screen orchestration boundaries

## Practical Priority Order

The current safest order is:

- Header UI
- Content cards
- Main screen orchestration

Do not jump ahead just because another area looks “ugly”.
Sequence matters because runtime stability matters.

---

## 12. What a Good Refactor Looks Like Here

A good CLUBAL refactor usually has these characteristics:

- smaller responsibility surface in `clubal.py`
- fewer duplicated calculations
- clearer ownership of logic vs rendering
- no visible regression
- no unnecessary redesign
- easier future maintenance
- safer next extraction step

A bad refactor here usually looks like:

- large rewrite disguised as cleanup
- touching stable subsystems unnecessarily
- moving code without clear destination responsibility
- spreading one concept across too many modules too early
- increasing abstraction while decreasing clarity

---

## 13. Decision Heuristics

When deciding where code should go, ask:

### Question 1
Can this run without Tkinter?
- yes → likely `core/` or `infra/`
- no → likely `ui/` or `clubal.py`

### Question 2
Does this read/write files, logs, or external resources?
- yes → likely `infra/`
- no → keep evaluating

### Question 3
Is this mostly layout, geometry, or rendering support?
- yes → likely `ui/`

### Question 4
Is this top-level scheduling, coordination, or integration glue?
- yes → likely `clubal.py`

### Question 5
Is this weather-backend-specific and operationally stable?
- yes → keep it in `weather_service.py`

---

## 14. Maintenance Notes for Future Contributors

Anyone touching this repository should understand:

- the app is optimized for constrained real-world runtime environments
- simplicity and predictability matter more than novelty
- modularization is ongoing, but should remain controlled
- readability is important, but not at the cost of regressions
- the best next move is usually the smallest safe move that improves structure

---

## 15. Final Principle

CLUBAL should evolve as a **stable runtime first** and a **clean architecture second**.

Clean architecture is valuable here only when it improves:

- maintenance safety
- responsibility clarity
- regression resistance
- long-term evolvability

If a structural change does not improve at least one of these in a practical way, it is probably not worth making.

