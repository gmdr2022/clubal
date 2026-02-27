# CLUBAL — Product Roadmap

This document defines the long-term product direction of CLUBAL.
It focuses on value, differentiation, operational fit, and scalability.
It avoids implementation details and should remain stable over time.

---

## 1. Positioning

CLUBAL is not “an agenda with weather”.

CLUBAL is a:

> Lightweight, resilient institutional communication platform

Agenda, weather, and holidays are content modules.
The core value is a stable delivery system for institutional information.

---

## 2. Primary Use Cases

CLUBAL is designed to operate reliably in environments where typical solutions fail:

- TVs running Windows
- low-end or aging PCs
- restricted corporate environments
- offline or unstable networks
- portable/pendrive deployments

Primary display use cases:

- daily schedule of activities
- weather indicators (optional)
- monthly holidays/calendar highlights
- institutional notices
- urgent announcements

---

## 3. Core Product Principles

These principles must remain true as the product evolves:

- Offline-first by default
- Portable-friendly operation
- No dependency on constant internet
- Minimal resource usage
- Simple operation (TV-ready)
- Graceful degradation (never crash)
- Expandable via modular content
- Commercial packaging readiness

---

## 4. Modular Content Strategy

CLUBAL treats each information type as a module.

Examples of modules:

- Daily Agenda
- Weather Indicators
- Holiday Calendar
- Institutional Notices
- Campaigns / Banners
- QR Code / Link Call-to-Action
- Emergency Alerts

Adding a module must not require restructuring the entire application.

---

## 5. Priority & Emergency System

A mature institutional platform needs content priority.

Priority levels (conceptual):

- Normal (default)
- Highlight (more frequent / more visible)
- Urgent (interrupt rotation)
- Blocking (full-screen takeover)

Emergency mode must be activatable locally (offline-safe), for example:

- local flag file
- configuration field
- admin action

Behavior:

- interrupts normal rotation
- shows a dedicated emergency screen or message
- remains stable without internet

---

## 6. Multi-Profile Branding

A single build should support multiple institutions.

Profiles should enable:

- customer logo and branding assets
- location and weather settings (optional)
- theme choices and layout variations
- local holidays configuration

Profile selection should be possible without complex setup.

---

## 7. Operator Experience (TV-Ready UX)

The system must work even without a keyboard.

Design direction:

- large touch-friendly controls (if interaction is enabled)
- optional welcome screen
- configurable auto-start
- safe shutdown options for controlled environments
- clear visual hierarchy for distance viewing

---

## 8. Local Administration (Lightweight)

CLUBAL should provide a lightweight local administration mode:

- change basic settings
- import or refresh schedule data
- clear cache/logs (if writable)
- view system status (offline-safe)
- activate emergency mode

This mode must not require a web server.

---

## 9. Local Telemetry (Optional, Offline-Safe)

CLUBAL may record minimal local telemetry for support and maintenance:

- uptime counters
- last boot timestamps
- crash counters
- last known network state (optional)

No external server dependency is required.

---

## 10. Commercial Direction (After Stability)

After technical stability and modularization maturity:

- professional packaging
- licensing strategy (optional)
- offline update packages
- customer profiles distribution
- support-oriented diagnostics

Commercial growth must not compromise:

- portability
- offline resilience
- stability
- low resource usage

---

## 11. Long-Term Direction

CLUBAL grows in capability, not in fragility.

The product must always preserve:

- lightweight execution
- offline-first behavior
- portable compatibility
- TV readiness
- modular content expansion
- operational simplicity