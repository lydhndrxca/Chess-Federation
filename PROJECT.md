# Chess Federation

**Status:** MVP complete — ready for deployment.

## Overview

A private, link-access online correspondence chess platform for a small group
of players. Features weekly scheduled matches, persistent federation ratings
with a custom 10-tier ranking system, full match history with notation, and
a rotating "Power Position" authority that can modify the game rules over time.

## Current Phase

MVP (v1) is implemented: accounts, weekly scheduling, correspondence play,
interactive chess board, ratings with material modifier, dashboard, profiles,
and match history. Power Position system (v2) is next.

## Stack

Python / Flask / SQLite / Jinja2 + vanilla JS

## Run

```
double-click run.bat
```

## Deploy

Push to GitHub, connect to Render.com. Uses `render.yaml` for auto-config.
