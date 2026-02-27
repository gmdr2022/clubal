# CLUBAL — Current Architecture

This document describes the architectural structure and runtime behavior of CLUBAL.
It focuses on principles and structure rather than temporary implementation details.

---

## 1. Architectural Overview

CLUBAL follows a centralized runtime context model.

The system initializes through a bootstrap layer that:

- Detects execution environment
- Resolves path policy
- Determines writable capabilities
- Establishes logging and caching behavior

All infrastructure decisions derive from a runtime context.

---

## 2. Runtime Context Pattern

At startup:

- The application initializes a runtime context.
- The context exposes resolved path information.
- Modules consume context instead of resolving paths independently.

This prevents path duplication and environment-specific logic from spreading across the codebase.

---

## 3. Environment Detection

Execution modes are determined dynamically:

- Installed execution
- Portable execution
- Restricted/no-write environment

The system performs real write validation to determine writable capability.

If writing is not possible:
- Logs and cache may be disabled.
- The application must continue safely.

---

## 4. Path Resolution Policy

The architecture centralizes:

- Application directory
- Asset directory
- Data directory
- Writable root (if available)
- Log directory (if available)
- Cache directory (if available)

No module creates directories independently.
All path resolution flows through the centralized policy.

---

## 5. UI Structure

CLUBAL operates within a single Tkinter root.

Layout pattern:

HEADER
- Logo
- Date
- Clock
- Weather card

BODY
- Two primary columns:
  - Current activities
  - Upcoming activities

Content rotation uses event scheduling (`after()`).
No aggressive loops are allowed.

Layout is reused instead of rebuilt.

---

## 6. Agenda System

- Data-driven
- Local-first
- Filters by day
- Determines active and upcoming activities
- Calculates temporal progress
- Updates event-driven

Agenda must function fully offline.

---

## 7. Weather System

- Online source when available
- Local cache fallback
- Icon management with image compatibility layer
- Short timeouts
- Graceful degradation when offline

Weather failure must never crash the UI.

---

## 8. Logging & IO

Logging and IO follow centralized path resolution.

If no writable directory exists:
- Logging becomes a no-op.
- Execution continues safely.

This ensures compatibility with:

- Corporate PCs
- Restricted environments
- Portable deployments
- TV execution

---

## 9. Current Structural Reality

The application remains partially centralized in a primary file.

However:

- Infrastructure is already abstracted.
- Runtime context is centralized.
- Path logic is no longer scattered.

The next architectural phase focuses on controlled modularization without breaking runtime stability.