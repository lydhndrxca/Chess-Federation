import hashlib
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask
from flask_login import LoginManager, current_user

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
    if 'is_bot' not in user_cols:
        cur.execute('ALTER TABLE user ADD COLUMN is_bot BOOLEAN DEFAULT 0')
    if 'enoch_points' not in user_cols:
        cur.execute('ALTER TABLE user ADD COLUMN enoch_points INTEGER DEFAULT 0')
    if 'enoch_wager_wins' not in user_cols:
        cur.execute('ALTER TABLE user ADD COLUMN enoch_wager_wins INTEGER DEFAULT 0')
    if 'enoch_wager_losses' not in user_cols:
        cur.execute('ALTER TABLE user ADD COLUMN enoch_wager_losses INTEGER DEFAULT 0')
    if 'enoch_wager_draws' not in user_cols:
        cur.execute('ALTER TABLE user ADD COLUMN enoch_wager_draws INTEGER DEFAULT 0')
    if 'last_seen' not in user_cols:
        cur.execute('ALTER TABLE user ADD COLUMN last_seen DATETIME')

    game_cols = {row[1] for row in cur.execute('PRAGMA table_info(game)').fetchall()}
    if 'power_holder_id' not in game_cols:
        cur.execute('ALTER TABLE game ADD COLUMN power_holder_id INTEGER')
    if 'is_practice' not in game_cols:
        cur.execute('ALTER TABLE game ADD COLUMN is_practice BOOLEAN DEFAULT 0')
    if 'custom_rule_name' not in game_cols:
        cur.execute('ALTER TABLE game ADD COLUMN custom_rule_name VARCHAR(100)')
    if 'game_type' not in game_cols:
        cur.execute("ALTER TABLE game ADD COLUMN game_type VARCHAR(10) DEFAULT 'weekly'")

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

    if 'player_collectible' not in tables:
        cur.execute('''CREATE TABLE player_collectible (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            game_id INTEGER,
            acquired_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(game_id) REFERENCES game(id)
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

    if 'enoch_wager' not in tables:
        cur.execute('''CREATE TABLE enoch_wager (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            mood VARCHAR(20) NOT NULL,
            wager_amount INTEGER NOT NULL,
            is_anomaly BOOLEAN DEFAULT 0,
            result VARCHAR(10),
            points_change INTEGER,
            created_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(game_id) REFERENCES game(id)
        )''')

    if 'four_player_game' not in tables:
        cur.execute('''CREATE TABLE four_player_game (
            id INTEGER PRIMARY KEY,
            south_id INTEGER, west_id INTEGER,
            north_id INTEGER, east_id INTEGER,
            board_state TEXT, status VARCHAR(20) DEFAULT 'waiting',
            eliminated TEXT DEFAULT '[]', result_order TEXT, scores TEXT,
            week_number INTEGER, season INTEGER DEFAULT 1,
            move_count INTEGER DEFAULT 0, current_turn VARCHAR(10) DEFAULT 'south',
            created_at DATETIME, started_at DATETIME,
            completed_at DATETIME, deadline DATETIME,
            FOREIGN KEY(south_id) REFERENCES user(id),
            FOREIGN KEY(west_id) REFERENCES user(id),
            FOREIGN KEY(north_id) REFERENCES user(id),
            FOREIGN KEY(east_id) REFERENCES user(id)
        )''')

    if 'four_player_move' not in tables:
        cur.execute('''CREATE TABLE four_player_move (
            id INTEGER PRIMARY KEY,
            game_id INTEGER NOT NULL,
            move_number INTEGER NOT NULL,
            color VARCHAR(10) NOT NULL,
            move_str VARCHAR(20) NOT NULL,
            captured VARCHAR(5),
            commentary TEXT,
            timestamp DATETIME,
            FOREIGN KEY(game_id) REFERENCES four_player_game(id)
        )''')

    if 'crypt_game' not in tables:
        cur.execute('''CREATE TABLE crypt_game (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            wave INTEGER DEFAULT 1,
            score INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 5,
            gold_earned INTEGER DEFAULT 5,
            gold_spent INTEGER DEFAULT 0,
            kills INTEGER DEFAULT 0,
            phase VARCHAR(20) DEFAULT 'placement',
            fen_current VARCHAR(100),
            inventory TEXT DEFAULT '["K","Q","P","P","P"]',
            rating_entry INTEGER DEFAULT 5,
            rating_result INTEGER,
            cashed_out BOOLEAN DEFAULT 0,
            started_at DATETIME,
            completed_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )''')
    else:
        crypt_cols = {r[1] for r in cur.execute(
            'PRAGMA table_info(crypt_game)').fetchall()}
        if 'rating_entry' not in crypt_cols:
            cur.execute('ALTER TABLE crypt_game ADD COLUMN rating_entry INTEGER DEFAULT 5')
        if 'rating_result' not in crypt_cols:
            cur.execute('ALTER TABLE crypt_game ADD COLUMN rating_result INTEGER')
        if 'cashed_out' not in crypt_cols:
            cur.execute('ALTER TABLE crypt_game ADD COLUMN cashed_out BOOLEAN DEFAULT 0')

    if 'challenge' not in tables:
        cur.execute('''CREATE TABLE challenge (
            id INTEGER PRIMARY KEY,
            challenger_id INTEGER NOT NULL,
            challenged_id INTEGER NOT NULL,
            status VARCHAR(10) DEFAULT 'pending',
            game_id INTEGER,
            created_at DATETIME,
            FOREIGN KEY(challenger_id) REFERENCES user(id),
            FOREIGN KEY(challenged_id) REFERENCES user(id),
            FOREIGN KEY(game_id) REFERENCES game(id)
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
    from app.routes.four_player import fp_bp
    from app.routes.crypt import crypt_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(players_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(decree_bp)
    app.register_blueprint(hall_bp)
    app.register_blueprint(fp_bp)
    app.register_blueprint(crypt_bp)

    from app.routes.challenge import challenge_bp
    app.register_blueprint(challenge_bp)

    _migrate_db(app)

    @app.context_processor
    def _inject_manifest_version():
        return {
            'manifest_version': app.config.get('MANIFEST_VERSION', '1'),
            'audio_cdn_base': 'https://raw.githubusercontent.com/lydhndrxca/Chess-Federation/main/app/static/audio/',
        }

    @app.after_request
    def _touch_last_seen(response):
        try:
            if current_user.is_authenticated and not current_user.is_bot:
                current_user.last_seen = datetime.now(timezone.utc)
                db.session.commit()
        except Exception:
            db.session.rollback()
        return response

    manifest_path = os.path.join(
        app.static_folder, 'audio', 'enoch', 'manifest.json')
    try:
        with open(manifest_path, 'rb') as f:
            app.config['MANIFEST_VERSION'] = hashlib.md5(f.read()).hexdigest()[:8]
    except OSError:
        app.config['MANIFEST_VERSION'] = '1'

    with app.app_context():
        db.create_all()
        _ensure_enoch_bot()

    return app


def _ensure_enoch_bot():
    """Create the Enoch bot user if it does not already exist."""
    enoch = User.query.filter_by(username='Enoch').first()
    if not enoch:
        import secrets
        enoch = User(
            username='Enoch',
            is_active_player=False,
            is_bot=True,
            bio='Steward Beneath the Board. Keeper of the scrap-ledger.',
            rating=550,
        )
        enoch.set_password(secrets.token_hex(32))
        db.session.add(enoch)
        db.session.commit()
