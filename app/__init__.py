import os
import sqlite3

from flask import Flask
from flask_login import LoginManager

from app.config import Config
from app.models import db, User

login_manager = LoginManager()

MIGRATION_FLAG = 'v2_rating_reset_done'


def _migrate_db(app):
    """Add columns / tables that may not exist in an older database."""
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    user_cols = {row[1] for row in cur.execute('PRAGMA table_info(user)').fetchall()}
    if 'avatar_filename' not in user_cols:
        cur.execute('ALTER TABLE user ADD COLUMN avatar_filename VARCHAR(120)')
    if 'can_name_openings' not in user_cols:
        cur.execute('ALTER TABLE user ADD COLUMN can_name_openings BOOLEAN DEFAULT 1')
    if 'bio' not in user_cols:
        cur.execute("ALTER TABLE user ADD COLUMN bio TEXT DEFAULT ''")

    game_cols = {row[1] for row in cur.execute('PRAGMA table_info(game)').fetchall()}
    if 'power_holder_id' not in game_cols:
        cur.execute('ALTER TABLE game ADD COLUMN power_holder_id INTEGER')

    tables = {row[0] for row in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if 'chat_message' not in tables:
        cur.execute('''CREATE TABLE chat_message (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            content TEXT NOT NULL,
            is_bot BOOLEAN DEFAULT 0,
            bot_name VARCHAR(80),
            timestamp DATETIME,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )''')

    if 'power_rotation_order' not in tables:
        cur.execute('''CREATE TABLE power_rotation_order (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )''')

    if 'commendation' not in tables:
        cur.execute('''CREATE TABLE commendation (
            id INTEGER PRIMARY KEY,
            game_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            kind VARCHAR(10) NOT NULL,
            text TEXT NOT NULL,
            created_at DATETIME,
            FOREIGN KEY(game_id) REFERENCES game(id),
            FOREIGN KEY(author_id) REFERENCES user(id),
            FOREIGN KEY(subject_id) REFERENCES user(id)
        )''')

    if 'named_sequence' not in tables:
        cur.execute('''CREATE TABLE named_sequence (
            id INTEGER PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            name VARCHAR(120) NOT NULL,
            moves TEXT NOT NULL,
            half_moves INTEGER NOT NULL,
            category VARCHAR(20) NOT NULL,
            created_at DATETIME,
            FOREIGN KEY(creator_id) REFERENCES user(id)
        )''')

    if 'season_material_stat' not in tables:
        cur.execute('''CREATE TABLE season_material_stat (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            season_month INTEGER NOT NULL,
            total_diff REAL DEFAULT 0,
            games_count INTEGER DEFAULT 0,
            avg_diff REAL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )''')

    if '_migration_flags' not in tables:
        cur.execute('''CREATE TABLE _migration_flags (
            flag VARCHAR(100) PRIMARY KEY
        )''')

    done = cur.execute(
        "SELECT 1 FROM _migration_flags WHERE flag=?", (MIGRATION_FLAG,)
    ).fetchone()
    if not done:
        cur.execute('UPDATE user SET rating=200, wins=0, losses=0, draws=0, forfeits=0')
        cur.execute("INSERT INTO _migration_flags(flag) VALUES(?)", (MIGRATION_FLAG,))

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
    from app.routes.decree import decree_bp
    from app.routes.hall import hall_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(players_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(decree_bp)
    app.register_blueprint(hall_bp)

    _migrate_db(app)

    with app.app_context():
        db.create_all()

    return app
