#!/usr/bin/env python3
"""
Chess Federation — run entrypoint.

Usage:  python run.py

Automatically creates a local virtual environment, installs dependencies,
and launches the Flask development server.
"""

import os
import sys
import subprocess
import venv

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(ROOT, ".venv")
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")

IS_WIN = sys.platform == "win32"
PYTHON = os.path.join(VENV_DIR, "Scripts" if IS_WIN else "bin", "python")
PIP = os.path.join(VENV_DIR, "Scripts" if IS_WIN else "bin", "pip")


def ensure_venv():
    if not os.path.isdir(VENV_DIR):
        print("[setup] Creating virtual environment …")
        venv.create(VENV_DIR, with_pip=True)

    subprocess.check_call(
        [PIP, "install", "-q", "-r", REQUIREMENTS],
        stdout=subprocess.DEVNULL,
    )


def main():
    ensure_venv()

    os.environ.setdefault("FLASK_APP", "app")
    os.environ.setdefault("FLASK_ENV", "development")

    subprocess.check_call(
        [PYTHON, "-m", "flask", "run", "--host", "0.0.0.0", "--port", "5000"],
        cwd=ROOT,
    )


if __name__ == "__main__":
    main()
