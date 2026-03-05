# CLUBAL — Vision

CLUBAL (Club Agenda Live) is a lightweight digital signage application designed for institutional environments that require **reliability, simplicity, and low resource usage**.

This document defines the **stable product intent** of CLUBAL and should remain evergreen.

---

## Documentation policy (evergreen)

Docs under `docs/` should be **stable and low-maintenance**.

Update documentation only when there is a **real contract change**, such as:

- significant product direction changes
- distribution, commercial, or legal requirements
- major architectural shifts that change what the product fundamentally is

Avoid updating docs for every roadmap step or minor refactor.

---

## 1. Core product intent

CLUBAL exists to provide a dependable, easily operated screen experience for schedules and informational content in constrained environments.

Primary outcomes:

- show what is happening now and what comes next
- keep the screen readable from distance
- remain stable across devices and monitors
- degrade gracefully when offline

---

## 2. Target environments

CLUBAL is designed to run in environments such as:

- Windows PCs (including low-end machines)
- Windows TVs
- corporate / restricted environments (limited permissions)
- portable “pendrive-style” deployments
- unstable or offline networks

---

## 3. Non-negotiable priorities

### 3.1 Reliability over novelty

The app must remain stable and predictable.

- avoid fragile dependencies
- prefer simple, proven approaches
- keep runtime behavior deterministic

### 3.2 Offline-first execution

Internet is optional. The app must stay functional without it.

- local data source for schedule
- cached data for optional integrations (weather)
- safe behavior when network fails

### 3.3 Low resource usage

CLUBAL should remain light enough for:

- old PCs
- TVs with limited compute
- long uptime

### 3.4 Simple operation

Operators should not need technical knowledge to keep the system running.

- minimal steps to update schedule content
- clear failure behavior (no crashes)
- compatibility with keyboard-less scenarios when applicable

---

## 4. Content philosophy

CLUBAL is a runtime for modular content blocks.

Core block:

- schedule (AGORA / PRÓXIMAS)

Optional blocks:

- weather
- hours/status
- future informational cards

All blocks should remain replaceable modules over a stable runtime base.

---

## 5. Long-term positioning

CLUBAL should remain suitable for:

- internal institutional usage
- portable deployments
- future commercial distribution

If the project evolves into a commercial product, docs may be expanded for:

- licensing
- distribution constraints
- legal protection
- operational support requirements

---

## 6. What this document is not

- It is not a roadmap.
- It is not an implementation plan.
- It should not contain temporary status or phase notes.

It should remain stable unless the product itself changes.