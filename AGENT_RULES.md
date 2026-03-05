# Agent Rules

This is the authoritative governance contract for the Chess Federation repository.

## Core Principles

1. **Single system**: one Flask app, one JSON data file, one run command.
2. **Search before creating**: check for existing modules before adding new ones.
3. **Delete replaced paths**: remove dead code immediately.
4. **Small complete slices**: each change should leave the app in a working state.
5. **Docs stay current**: update ARCHITECTURE.md, SPEC.md, and DECISIONS.md when the implementation changes.
6. **No secrets in source**: admin password comes from environment or is set at first launch.
7. **Portability**: `python run.py` must work on a fresh unzip with only Python 3 installed.

## File Authority

| Document | Governs |
|----------|---------|
| SPEC.md | What the app does |
| ARCHITECTURE.md | How it is built and run |
| DECISIONS.md | Why choices were made |
| TASKS.md | What to work on next |
| This file | How the agent must behave |
