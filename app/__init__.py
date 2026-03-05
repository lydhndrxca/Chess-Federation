import os
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "chess-federation-dev-key")

    from . import routes
    app.register_blueprint(routes.bp)

    return app
