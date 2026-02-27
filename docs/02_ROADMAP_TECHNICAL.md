# CLUBAL — Technical Roadmap

This roadmap defines architectural evolution phases.
It represents direction, not temporary task lists.

Phases are sequential and must preserve stability.

---

## Phase 1 — Runtime Foundation

Goal:
Establish centralized bootstrap, environment detection, and path resolution.

Outcome:
- No scattered path logic.
- No direct directory creation in feature modules.
- Safe fallback when no writable directory exists.

This phase establishes structural stability.

---

## Phase 2 — Controlled Modularization

Goal:
Separate responsibilities without altering behavior.

Target separation order:

1. UI theme utilities
2. Logging abstraction
3. Agenda engine
4. Weather service
5. Header UI
6. Content cards
7. Main screen orchestration

The main application file gradually becomes an orchestrator.

---

## Phase 3 — TV Readiness

Goal:
Ensure complete compatibility with keyboard-less TV environments.

- Optional welcome screen
- Auto-start logic
- Large interactive areas
- Safe fallback when no keyboard exists

---

## Phase 4 — Universal Performance

Goal:
Guarantee stable performance across:

- Low-end PCs
- Modern PCs
- TVs

Rules:
- No aggressive loops
- Event-driven UI
- Cached measurements
- Minimal redraws

---

## Phase 5 — Configuration Layer

Goal:
Centralized configuration management.

- Structured config file
- Safe load/save
- Default configuration fallback

---

## Phase 6 — Data Independence

Goal:
Remove structural dependency on Excel.

- JSON-based data
- Optional import layer
- Local editing capability

---

## Phase 7+ — Advanced Platform Capabilities

Future phases include:

- Content engine
- Priority system
- Emergency mode
- Multi-profile branding
- Watchdog & auto-recovery
- Offline update capability

Each phase must preserve:

- Offline-first execution
- Portable compatibility
- Runtime resilience