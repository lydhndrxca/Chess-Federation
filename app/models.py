from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rating = db.Column(db.Integer, default=800)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    forfeits = db.Column(db.Integer, default=0)
    avatar_filename = db.Column(db.String(120))
    is_active_player = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def tier(self):
        from app.services.rating import get_tier
        return get_tier(self.rating)

    @property
    def total_games(self):
        return self.wins + self.losses + self.draws


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    white_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    black_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    season = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pending')
    result = db.Column(db.String(10))
    result_type = db.Column(db.String(20))
    pgn = db.Column(db.Text, default='')
    fen_current = db.Column(
        db.String(100),
        default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    )
    fen_final = db.Column(db.String(100))
    material_white = db.Column(db.Integer)
    material_black = db.Column(db.Integer)
    rating_change_white = db.Column(db.Float)
    rating_change_black = db.Column(db.Float)
    current_turn = db.Column(db.String(5), default='white')
    move_count = db.Column(db.Integer, default=0)
    rule_snapshot = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)

    white = db.relationship('User', foreign_keys=[white_id], backref='games_as_white')
    black = db.relationship('User', foreign_keys=[black_id], backref='games_as_black')
    moves = db.relationship('Move', backref='game', order_by='Move.id')


class Move(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    move_number = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(5), nullable=False)
    move_san = db.Column(db.String(10), nullable=False)
    move_uci = db.Column(db.String(10), nullable=False)
    fen_after = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class WeeklySchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week_number = db.Column(db.Integer, nullable=False)
    season = db.Column(db.Integer, default=1)
    power_position_holder_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rule_declaration = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    power_holder = db.relationship('User', foreign_keys=[power_position_holder_id])
