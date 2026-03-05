# CHANGELOG

This changelog is intentionally **low-noise**.

It should track **meaningful user-visible or distribution-relevant changes**, not every internal refactor.
The Git history remains the source of truth for granular engineering changes.

---

## Documentation policy (evergreen)

Docs under `docs/` should be **stable and low-maintenance**.

Update documentation only when there is a **real contract change**, such as:

- user-visible behavior changes
- module boundary / public API changes
- significant architecture changes
- distribution, commercial, or legal requirements

Avoid updating docs for every roadmap step or minor refactor.

---

## How to use this changelog

Update this file only when at least one of the following is true:

- the operator/user experience changes (UI/behavior)
- the spreadsheet contract changes (`grade_template.xlsx` / parsing rules)
- packaging/distribution changes (PyInstaller, assets, portability, permissions)
- a public import path / shim contract changes
- legal/commercial notes require documentation

For internal refactors that preserve behavior, prefer commit history only.

---

## Unreleased

- (keep empty unless there is a user-visible change pending release)

---

## Releases

### v0.0.0
- Initial internal development baseline.