# CLUBAL — Vision & Foundations

## 1. Project Identity

CLUBAL (Club Agenda Live) is a lightweight institutional communication platform designed for resilient execution across diverse environments:

- Windows PCs (low-end or modern)
- Windows-based TVs
- Portable/pendrive execution
- Corporate restricted environments
- Fully offline scenarios

Official stack:

- Python
- Tkinter
- Pillow (image compatibility layer when required)

The core focus is stability, operational simplicity, and progressive scalability.

---

## 2. Core Philosophy

CLUBAL is:

- Offline-first
- Portable
- Lightweight
- Event-driven
- Resilient
- Modular by design
- Prepared for commercial evolution

The system must never strictly depend on:

- Internet connectivity
- APPDATA availability
- Complex installation processes
- External services for basic functionality

Local execution must always remain sufficient.

---

## 3. Permanent Technical Pillars

1. Never fail due to lack of write permission.
2. Always provide silent path fallback.
3. Never require constant internet access.
4. Avoid aggressive loops or polling.
5. Prefer event-driven updates.
6. Preserve layout stability during content rotation.
7. Minimize CPU usage.
8. Ensure portable compatibility.
9. Bundle required image dependencies during packaging.

These rules are permanent and non-negotiable.

---

## 4. Path Policy (Conceptual Contract)

The system resolves runtime paths through a centralized policy.

If a writable system directory is available:
- It may be used for logs and cache.

If no writable directory is available:
- The system falls back to safe local behavior.
- Logging and caching may be disabled.
- The application must continue running.

No fatal errors due to permission issues are allowed.

---

## 5. Internal Engineering Contract

All code evolution must follow these operational rules:

- Always specify exact search targets (Ctrl+F).
- Always specify the exact action:
  - delete
  - replace
  - paste before
  - paste after
- Provide complete, ready-to-paste code blocks.
- If multiple changes affect the same function:
  - deliver the entire function.
- Solve one structural problem at a time.
- Avoid broad refactors unless strategically required.

---

## 6. Strategic Direction

CLUBAL is not simply an agenda application.

It is a modular institutional communication platform.

Agenda, weather, holidays, and future modules are content.
The architecture is the core.

Evolution must always preserve:

- Lightweight execution
- TV compatibility
- Portable operation
- Offline resilience
- Architectural clarity