import os
import functools
from flask import session, redirect, url_for, request

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "federation")


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if not session.get("admin"):
            return redirect(url_for("main.admin_login"))
        return view(**kwargs)
    return wrapped


def check_password(password: str) -> bool:
    return password == ADMIN_PASSWORD
