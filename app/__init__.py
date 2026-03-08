import os
import sqlite3

from flask import Flask
from flask_login import LoginManager

from app.config import Config
from app.models import db, User

login_manager = LoginManager()


def _migrate_db(app):
    """Add columns that may not exist in an older database."""
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute('PRAGMA table_info(user)').fetchall()}
    if 'avatar_filename' not in cols:
        conn.execute('ALTER TABLE user ADD COLUMN avatar_filename VARCHAR(120)')
        conn.commit()
    conn.close()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.game import game_bp
    from app.routes.players import players_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(players_bp)
    app.register_blueprint(admin_bp)

    _migrate_db(app)

    with app.app_context():
        db.create_all()

    return app
