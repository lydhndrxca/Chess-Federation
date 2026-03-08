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

No build step, no frontend framework. Responsive CSS for mobile.
Dark/ominous ceremonial theme.

## DEC-006: Auth — Flask-Login + werkzeug hashing

Simple session-based authentication. Sufficient for a small trusted group.
Remember-me cookie lasts 90 days.

## DEC-007: Rating System — Modified Elo with Material Modifier

`base result + expectation adjustment + material modifier`. Material
modifier capped at 20% of base change. Forfeit results skip material
modifier. K-factor = 32.

## DEC-008: Board Rendering — Chessground (vendored)

Originally built a custom board renderer using CSS Grid and Unicode chess
symbols. Replaced with Chessground library (vendored `chessground.min.js`)
for drag-and-drop, SVG pieces, and animations. The library is included in
`app/static/js/` with no build step required.

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

## DEC-012: Matchmaking — All-Play-All

Changed from one-match-per-week to all-play-all: every active player plays
every other player each week. Matches auto-generate at Sunday 5 PM CST.
Unfinished matches are forfeited for both players.

## DEC-013: Enoch NPC System

Introduced "Enoch" as a sub-basement steward NPC. Practice matches against
Enoch are unrated and do not affect federation standings. Enoch has a
mood-based AI (Chill ~500, Annoyed ~800, Angry ~1200 Elo) using a
deterministic daily schedule seeded from the date.

## DEC-014: Enoch Wager System

Optional daily rated wagers against Enoch. Mood determines stake range
(5–25 pts). 1% anomaly chance for 30–50 pts at ~1500 Elo. One rated wager
per player per day. Wins/losses apply directly to the player's main rating.
Tracked separately via `EnochWager` model.

## DEC-015: Collectibles — Physical Item Theme

170 items across 12 collections with a damp, physical, unsettling aesthetic.
Triggers include game-analysis (board positions, move patterns), engagement
milestones (chat, career stats), lore (beating Enoch), and gambling
(wager wins/losses/streaks). Items stack with multipliers on duplicates.

## DEC-016: Federation Hall Chat

Persistent chat room at `/hall`. Enoch lurks and occasionally interjects
during periods of high activity. Players can use `@Enoch` commands.
Chat messages are stored permanently.

## DEC-017: Named Openings/Variations

Players can opt-in to naming new move sequences they discover in games.
Named sequences are stored permanently and displayed whenever any player
replays the same sequence in a future game.

## DEC-018: DB Migrations — Inline ALTER TABLE

Using raw SQL `ALTER TABLE` with column-existence checks in
`app/__init__.py` rather than a formal migration framework (Alembic).
Sufficient for the current pace of schema changes. May need to adopt
Alembic if schema evolution accelerates.
