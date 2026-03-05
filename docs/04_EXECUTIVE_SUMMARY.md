# CLUBAL — Executive Summary

This document provides a concise, stable overview of CLUBAL for stakeholders and maintainers.
It avoids temporary implementation status and focuses on what should remain true over time.

---

## Documentation policy (evergreen)

Docs under `docs/` should be **stable and low-maintenance**.

Update documentation only when there is a **real contract change**, such as:

- significant architecture changes
- distribution, commercial, or legal requirements
- changes that affect how the product is used or operated

Avoid updating docs for every roadmap step or minor refactor.

---

## 1. What CLUBAL is

CLUBAL (Club Agenda Live) is a lightweight digital signage application built with Python + Tkinter.

It is designed to display schedule information on institutional screens, focusing on:

- clarity at distance
- stable continuous operation
- offline-first behavior
- low resource usage

---

## 2. What it shows

CLUBAL provides a simple screen model:

- **AGORA**: items currently active
- **PRÓXIMAS**: items coming next (within a configured time window)
- header information (date/time/status)
- optional weather (with cache and graceful offline fallback)

---

## 3. Why it exists (business value)

CLUBAL fits contexts where heavier dashboard stacks are not viable:

- low-end or older machines
- restricted corporate environments
- TVs with limited compute
- unreliable or offline networks
- portable deployments

It favors reliability and maintainability over feature breadth.

---

## 4. Operational model

Primary update flow:

- schedule updates are driven by a local Excel file (runtime `grade.xlsx`)
- the repository provides `grade_template.xlsx` as a versioned model
- the application runs continuously and updates the view on a tick schedule

Weather (optional):

- uses online forecast when available
- caches results locally (when writable)
- does not crash the UI when offline

---

## 5. Engineering principles

Non-negotiable engineering constraints:

- do not require constant internet
- never crash due to lack of write permission
- keep runtime event-driven (Tkinter `after()` scheduling)
- preserve behavior when refactoring (move code before rewriting)
- preserve import compatibility with thin shims when necessary

---

## 6. When documentation changes are acceptable

Documentation should remain evergreen and only be updated for:

- contract changes between modules
- major architecture shifts
- distribution/commercial/legal requirements

Roadmaps live in:

- `docs/02_ROADMAP_TECHNICAL.md`
- `docs/03_ROADMAP_PRODUCT.md`

This executive summary should remain stable unless the product meaningfully changes.