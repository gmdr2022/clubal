# 03_ROADMAP_PRODUCT — Product Roadmap (Evergreen)

This document defines CLUBAL’s product direction and constraints.
It is intentionally **not** a progress tracker.

---

## Documentation policy (evergreen)

Docs under `docs/` should be **stable and low-maintenance**.

Update documentation only when there is a **real product contract change**, such as:
- a new supported deployment mode
- distribution/commercial/legal requirements
- major shifts in product positioning or operating model

Avoid updating docs for every roadmap milestone.

---

## 1) Product goals

CLUBAL is a schedule-first digital signage runtime optimized for:

- institutional environments
- long uptime
- simple operation
- offline-first behavior
- low resource usage

---

## 2) Primary user outcomes

The screen must reliably answer:

- What is happening now?
- What starts next?
- What is the current date/time?
- Is the facility open? (if configured)
- What is the weather? (optional)

---

## 3) Target environments (supported modes)

CLUBAL is intended to work in:

- Windows PCs (including low-end machines)
- Windows TVs
- restricted/corporate environments (limited permissions)
- unstable networks or offline usage
- portable deployments (pendrive-style or “copy folder and run”)

---

## 4) Operational principles

### 4.1 Simple content updates
- schedule is updated via a local Excel file (`grade.xlsx`)
- the repository provides a template model (`grade_template.xlsx`)
- operators should not need developer tools

### 4.2 Resilience by default
- never crash because of missing internet
- never crash because of missing write permissions
- treat all integrations as optional

### 4.3 Maintainability over feature sprawl
- prefer modular content blocks over monolithic growth
- isolate concerns: UI vs logic vs IO vs orchestration vs integrations

---

## 5) Content blocks (product model)

Core:
- Schedule (AGORA / PRÓXIMAS)

Optional:
- Weather (with cache and graceful offline fallback)
- Hours/status blocks (open/closed)
- Additional informational cards (future)

Blocks should remain independently replaceable.

---

## 6) UX rules (stable)

- readability from distance
- stable layout with predictable hierarchy
- avoid flicker and unnecessary redraws
- avoid small text that breaks on low resolutions
- degrade gracefully (placeholder UI instead of blank/crash)

---

## 7) Packaging and distribution (product constraints)

Product readiness requires:

- predictable startup behavior
- bundled assets (`graphics/`)
- safe handling of optional dependencies (Pillow)
- portability when required (no-install scenarios)
- clear versioning and changelog (if commercial distribution becomes relevant)

If the project evolves into a commercial product, this doc may expand to include:
- licensing policy
- support/operations model
- legal/protection requirements

---

## 8) What this document is not

- not a list of tasks
- not a sprint plan
- not a record of what is currently finished

Progress belongs in:
- Git history
- issues/tasks (if used)

---

## 9) When to update this file

Update only if:
- supported environments change materially
- operating model changes (how operators update/run it)
- distribution/commercial/legal constraints change
- major UX principles change

Otherwise, keep it evergreen.