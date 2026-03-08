# Chess Federation — Decisions

## DEC-001: Governance Model

Adopted repo-resident governance model (RRGM) with Full/Medium/Low modes.
All governance docs live at repo root.

## DEC-002: Backend — Python / Flask

Flask 3.1.3 for the web framework. Lightweight, well-documented, good
ecosystem for chess libraries.

## DEC-003: Database — SQLite via SQLAlchemy

SQLite for zero-config, file-based portability. SQLAlchemy ORM makes
a future migration to PostgreSQL trivial (connection string swap).

## DEC-004: Chess Logic — python-chess library

Wrapped behind `ChessEngine` service interface so routes never import
python-chess directly. v2 can swap in a custom variant engine without
changing routes.

## DEC-005: Frontend — Jinja2 + vanilla JS

No build step, no frontend framework. Board rendered via custom JS using
Unicode chess characters. Responsive CSS for mobile.

## DEC-006: Auth — Flask-Login + werkzeug hashing

Simple session-based authentication. Sufficient for a small trusted group.

## DEC-007: Rating System — Modified Elo with Material Modifier

`base result + expectation adjustment + material modifier`. Material
modifier capped at 20% of base change. Forfeit results skip material
modifier. K-factor = 32.

## DEC-008: Board Rendering — Custom JS with Unicode Pieces

Built a custom board renderer using CSS Grid and Unicode chess symbols
instead of external libraries (chessground, chessboard.js). Keeps the
project dependency-free on the frontend and makes future variant board
support (non-8x8) straightforward.

## DEC-009: Forfeit Detection — Lazy Evaluation

Forfeits are checked lazily when the dashboard loads, rather than via a
background scheduler. Sufficient for a small group where someone checks
the dashboard at least once per day. APScheduler can be added later if
needed.

## DEC-010: Deployment — Render.com with Persistent Disk

`render.yaml` configures a web service with a persistent 1GB disk for
SQLite. Gunicorn serves the app. SECRET_KEY is auto-generated.
Alternative: PythonAnywhere free tier.

## DEC-011: MVP Scope

v1: Standard chess, accounts, weekly scheduling, ratings, dashboard,
profiles, history. Power Position system and variant engine deferred to v2.
