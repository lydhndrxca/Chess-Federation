import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models import Game, User, WeeklySchedule, db
from app.services.rating import apply_result

FEDERATION_TZ = ZoneInfo('America/Chicago')


def _now_ct():
    return datetime.now(FEDERATION_TZ)


def get_current_week():
    return _now_ct().isocalendar()[1]


def get_current_season():
    """Season = calendar month. Returns (year, month)."""
    now = _now_ct()
    return now.year, now.month


def get_week_deadline():
    """Next Sunday 12:00 PM Central Time."""
    now = _now_ct()
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now.hour >= 12:
        days_until_sunday = 7
    next_sunday = now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
    return next_sunday.astimezone(timezone.utc)


def generate_weekly_pairings(week=None, season=None):
    if week is None:
        week = get_current_week()
    if season is None:
        year, month = get_current_season()
        season = year * 100 + month

    existing = Game.query.filter_by(week_number=week, season=season).first()
    if existing:
        return {'week': week, 'games_created': 0, 'message': 'Week already generated'}

    players = User.query.filter_by(is_active_player=True).all()
    if len(players) < 2:
        return {'week': week, 'games_created': 0, 'message': 'Not enough players'}

    random.shuffle(players)
    deadline = get_week_deadline()
    games_created = 0

    power_holder_id = None
    try:
        from app.services.power import get_current_holder
        holder = get_current_holder()
        if holder:
            power_holder_id = holder.id
    except (ImportError, Exception):
        pass

    for i in range(0, len(players) - 1, 2):
        if random.random() < 0.5:
            white, black = players[i], players[i + 1]
        else:
            white, black = players[i + 1], players[i]

        game = Game(
            white_id=white.id,
            black_id=black.id,
            week_number=week,
            season=season,
            deadline=deadline,
            power_holder_id=power_holder_id,
        )
        db.session.add(game)
        games_created += 1

    schedule = WeeklySchedule.query.filter_by(week_number=week, season=season).first()
    if not schedule:
        schedule = WeeklySchedule(
            week_number=week,
            season=season,
            power_position_holder_id=power_holder_id,
        )
        db.session.add(schedule)

    db.session.commit()
    return {'week': week, 'games_created': games_created}


def check_forfeits():
    now = datetime.now(timezone.utc)
    overdue = Game.query.filter(
        Game.status.in_(['pending', 'active']),
        Game.deadline < now,
    ).all()

    forfeited = 0
    for game in overdue:
        game.status = 'forfeited'
        game.completed_at = now
        game.fen_final = game.fen_current
        game.result_type = 'timeout'

        if game.current_turn == 'white':
            game.result = '0-1'
        else:
            game.result = '1-0'

        material = {}
        try:
            from app.services.chess_engine import ChessEngine
            material = ChessEngine.get_material(game.fen_current)
        except Exception:
            material = {'white': 0, 'black': 0}
        game.material_white = material.get('white', 0)
        game.material_black = material.get('black', 0)

        apply_result(game)
        forfeited += 1

    if forfeited:
        db.session.commit()

    return {'forfeited': forfeited}
