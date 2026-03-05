# Decisions

## 001 — Flask + JSON storage

**Date**: 2026-03-04
**Decision**: Use Flask to serve the site with a single JSON file for persistence.
**Rationale**: Meets the zip-and-run portability requirement. No database server needed. Flask is lightweight and in the Python standard ecosystem.

## 002 — Web-based admin panel

**Date**: 2026-03-04
**Decision**: Admin functionality lives at `/admin` behind password authentication, not a separate CLI tool.
**Rationale**: User preference. Keeps the interface unified.

## 003 — Vanilla frontend (no build step)

**Date**: 2026-03-04
**Decision**: No JS framework or CSS preprocessor. Jinja2 templates + plain CSS/JS.
**Rationale**: Portability — no Node.js or npm required. Reduces complexity.
