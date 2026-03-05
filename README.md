# The Chess Federation

A web application for the Chess Federation — a privy covenant of degree amongst the brethren, governed by a sacred hierarchy of ten ranks.

## Quick Start

```
python run.py
```

Open **http://localhost:5000** in your browser.

The run command automatically creates a virtual environment, installs dependencies, and starts the server. Only **Python 3** is required.

## Admin Panel

Navigate to **http://localhost:5000/admin** and enter the password (default: `federation`).

Set a custom password via the `ADMIN_PASSWORD` environment variable.

From the admin panel you can:

- Record match results (winner gains 1 rank, loser drops 1 rank).
- Add or remove players.
- Edit player profiles, ranks, and status.
