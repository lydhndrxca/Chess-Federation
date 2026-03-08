from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rating = db.Column(db.Integer, default=200)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    forfeits = db.Column(db.Integer, default=0)
    avatar_filename = db.Column(db.String(120))
    is_active_player = db.Column(db.Boolean, default=True)
    can_name_openings = db.Column(db.Boolean, default=True)
    bio = db.Column(db.Text, default='')
    is_bot = db.Column(db.Boolean, default=False)
    enoch_points = db.Column(db.Integer, default=0)
    enoch_wager_wins = db.Column(db.Integer, default=0)
    enoch_wager_losses = db.Column(db.Integer, default=0)
    enoch_wager_draws = db.Column(db.Integer, default=0)
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
    power_holder_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)
    is_practice = db.Column(db.Boolean, default=False)
    custom_rule_name = db.Column(db.String(100))

    white = db.relationship('User', foreign_keys=[white_id], backref='games_as_white')
    black = db.relationship('User', foreign_keys=[black_id], backref='games_as_black')
    power_holder = db.relationship('User', foreign_keys=[power_holder_id])
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


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_bot = db.Column(db.Boolean, default=False)
    bot_name = db.Column(db.String(80))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id])


class PowerRotationOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id])


class Commendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kind = db.Column(db.String(10), nullable=False)  # 'commend' or 'condemn'
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    game = db.relationship('Game', foreign_keys=[game_id])
    author = db.relationship('User', foreign_keys=[author_id])
    subject = db.relationship('User', foreign_keys=[subject_id])


class NamedSequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    moves = db.Column(db.Text, nullable=False)
    half_moves = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    creator = db.relationship('User', foreign_keys=[creator_id])


class SeasonMaterialStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    season_year = db.Column(db.Integer, nullable=False)
    season_month = db.Column(db.Integer, nullable=False)
    total_diff = db.Column(db.Float, default=0)
    games_count = db.Column(db.Integer, default=0)
    avg_diff = db.Column(db.Float, default=0)

    user = db.relationship('User', foreign_keys=[user_id])


class PlayerCollectible(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=True)
    acquired_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id])
    game = db.relationship('Game', foreign_keys=[game_id])


class FourPlayerGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    south_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    west_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    north_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    east_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    board_state = db.Column(db.Text)
    status = db.Column(db.String(20), default='waiting')
    eliminated = db.Column(db.Text, default='[]')
    result_order = db.Column(db.Text)
    scores = db.Column(db.Text)
    week_number = db.Column(db.Integer)
    season = db.Column(db.Integer, default=1)
    move_count = db.Column(db.Integer, default=0)
    current_turn = db.Column(db.String(10), default='south')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)

    south = db.relationship('User', foreign_keys=[south_id])
    west = db.relationship('User', foreign_keys=[west_id])
    north = db.relationship('User', foreign_keys=[north_id])
    east = db.relationship('User', foreign_keys=[east_id])
    fp_moves = db.relationship('FourPlayerMove', backref='fp_game',
                               order_by='FourPlayerMove.id')

    def seat_for_user(self, user_id):
        if self.south_id == user_id:
            return 'south'
        if self.west_id == user_id:
            return 'west'
        if self.north_id == user_id:
            return 'north'
        if self.east_id == user_id:
            return 'east'
        return None

    def player_ids(self):
        return [self.south_id, self.west_id, self.north_id, self.east_id]

    def filled_seats(self):
        return sum(1 for pid in self.player_ids() if pid is not None)


class FourPlayerMove(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('four_player_game.id'), nullable=False)
    move_number = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(10), nullable=False)
    move_str = db.Column(db.String(20), nullable=False)
    captured = db.Column(db.String(5))
    commentary = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class EnochWager(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    mood = db.Column(db.String(20), nullable=False)
    wager_amount = db.Column(db.Integer, nullable=False)
    is_anomaly = db.Column(db.Boolean, default=False)
    result = db.Column(db.String(10))
    points_change = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id])
    game = db.relationship('Game', foreign_keys=[game_id])
