# Chess Federation — Agent Rules

Authoritative governance contract for this repository.
This file takes precedence over `.cursor/rules/governance.mdc` on any conflict.

## Project

**Name:** Chess Federation

## Responsibility

The user describes intent. The agent decides execution.

**Agent decides:**
* Whether a change is a spec update, a task, or a cleanup.
* When a pivot requires cleanup before new work.
* When a change is too complex for a single slice (Complexity Guard).
* What to delete when replacing code.

**User decides:**
* What to build (intent, features, direction).
* Which governance mode to operate in (Full / Medium / Low).
* Whether to accept or reject the agent's recommendations.
* When to commit / push / deploy.

## Governance Modes

| Mode | On session start | Doc sync | Footer |
|------|-----------------|----------|--------|
| Full (default) | Read all 6 docs | After every change | `Mode: Full` |
| Medium | Read AGENT_RULES.md + ARCHITECTURE.md | Batch at end of task | `Mode: Medium` |
| Low | Skip reads | User requests catch-ups | `Mode: Low` |

## Core Rules

1. **Single System Rule** — No parallel systems.
2. **Search First** — Confirm it doesn't exist before creating.
3. **Delete Replaced Paths** — Remove old code immediately.
4. **Small Complete Slices** — Each change is a complete, working unit.
5. **Docs Stay Synchronized** — Keep governance docs current.
6. **No Secrets** — Never commit keys, tokens, or credentials.
7. **Portability** — Zip-and-run. Dependencies declared. Entrypoint bootstraps.
8. **Simplicity** — Incremental over rewrites. Deletion over layering. No scope creep.

## Architecture Constraints

* Backend: Python 3 / Flask. No other backend frameworks.
* Database: SQLite via SQLAlchemy. No external database servers for v1.
* Chess logic: python-chess library, wrapped behind `ChessEngine` service
  interface. Routes never import python-chess directly.
* Frontend: Jinja2 templates + vanilla JS + CSS. No frontend frameworks,
  no build step, no Node.js.
* Auth: Flask-Login + werkzeug hashing. No external auth providers.
* One run entrypoint: `run.bat` (Windows).

## Consistency

* All chess logic goes through `app/services/chess_engine.py`.
* All rating logic goes through `app/services/rating.py`.
* All database access goes through SQLAlchemy models in `app/models.py`.
* Routes live in `app/routes/` as separate modules by concern.
* Templates live in `app/templates/` matching route structure.
* Static assets in `app/static/` (css/, js/, img/).
