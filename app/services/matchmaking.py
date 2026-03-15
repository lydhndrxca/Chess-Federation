from datetime import datetime, timedelta, timezone
from itertools import combinations
from zoneinfo import ZoneInfo

from app.models import Game, Move, User, WeeklySchedule, db
from app.services.chess_engine import ChessEngine
from app.services.rating import apply_result, RESULT_BASE, RATING_FLOOR

FEDERATION_TZ = ZoneInfo('America/Chicago')

MATCH_DEADLINE_HOUR = 17  # 5:00 PM CT
DECREE_DEADLINE_HOUR = 12  # noon CT
SEASON_START = datetime(2026, 3, 8, 17, 0, 0, tzinfo=ZoneInfo('America/Chicago'))


def _now_ct():
    return datetime.now(FEDERATION_TZ)


def get_current_week():
    """Federation week rolls over at Sunday 5 PM CT, not Monday midnight.
    Offset by 7 hours so Sunday 5 PM maps to Monday 00:00 (ISO boundary)."""
    shifted = _now_ct() + timedelta(hours=7)
    return shifted.isocalendar()[1]


def get_current_season():
    """Season = calendar month. Returns (year, month)."""
    now = _now_ct()
    return now.year, now.month


def get_week_deadline():
    """Next Sunday 5:00 PM Central Time."""
    now = _now_ct()
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now.hour >= MATCH_DEADLINE_HOUR:
        days_until_sunday = 7
    next_sunday = now.replace(
        hour=MATCH_DEADLINE_HOUR, minute=0, second=0, microsecond=0
    ) + timedelta(days=days_until_sunday)
    return next_sunday.astimezone(timezone.utc)


def get_decree_deadline():
    """Next Sunday 12:00 PM (noon) Central Time."""
    now = _now_ct()
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now.hour >= DECREE_DEADLINE_HOUR:
        days_until_sunday = 7
    next_sunday = now.replace(
        hour=DECREE_DEADLINE_HOUR, minute=0, second=0, microsecond=0
    ) + timedelta(days=days_until_sunday)
    return next_sunday.astimezone(timezone.utc)


def _count_white_games(user_id):
    """How many times this user has played as white."""
    return Game.query.filter_by(white_id=user_id).count()


def _assign_colors(player_a, player_b):
    """Assign white/black so the player who has been white less often gets white."""
    a_whites = _count_white_games(player_a.id)
    b_whites = _count_white_games(player_b.id)
    if a_whites <= b_whites:
        return player_a, player_b
    return player_b, player_a


def generate_weekly_pairings(week=None, season=None):
    if week is None:
        week = get_current_week()
    if season is None:
        year, month = get_current_season()
        season = year * 100 + month

    if _now_ct() < SEASON_START:
        return {'week': week, 'games_created': 0, 'message': 'Season has not started yet'}

    existing = Game.query.filter_by(week_number=week, season=season).first()
    if existing:
        return {'week': week, 'games_created': 0, 'message': 'Week already generated'}

    players = User.query.filter_by(is_active_player=True).all()
    if len(players) < 2:
        return {'week': week, 'games_created': 0, 'message': 'Not enough players'}

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

    schedule = WeeklySchedule.query.filter_by(week_number=week, season=season).first()
    if not schedule:
        schedule = WeeklySchedule(
            week_number=week,
            season=season,
            power_position_holder_id=power_holder_id,
        )
        db.session.add(schedule)

    active_rule = None
    try:
        from app.services.weekly_rule import RULE_ACTIVE, RULE_TITLE, RULE_DESCRIPTION
        if RULE_ACTIVE:
            active_rule = RULE_TITLE
            if not schedule.rule_declaration:
                schedule.rule_declaration = RULE_DESCRIPTION
    except ImportError:
        pass

    decree_text = schedule.rule_declaration or ''

    for pa, pb in combinations(players, 2):
        white, black = _assign_colors(pa, pb)

        game = Game(
            white_id=white.id,
            black_id=black.id,
            week_number=week,
            season=season,
            deadline=deadline,
            power_holder_id=power_holder_id,
            rule_snapshot=decree_text if decree_text else None,
            custom_rule_name=active_rule,
        )
        db.session.add(game)
        games_created += 1

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
        game.result_type = 'double_forfeit'
        game.result = '0-0'

        all_moves = Move.query.filter_by(game_id=game.id).order_by(Move.id).all()
        game.pgn = ChessEngine.build_pgn(all_moves, game)

        white = db.session.get(User, game.white_id)
        black = db.session.get(User, game.black_id)

        penalty = RESULT_BASE['forfeit_loss']
        game.rating_change_white = penalty
        game.rating_change_black = penalty

        white.losses += 1
        white.forfeits += 1
        white.rating = max(RATING_FLOOR, round(white.rating + penalty))

        black.losses += 1
        black.forfeits += 1
        black.rating = max(RATING_FLOOR, round(black.rating + penalty))

        try:
            from app.services.enoch import announce_double_forfeit
            announce_double_forfeit(white, black)
        except (ImportError, Exception):
            pass

        forfeited += 1

    if forfeited:
        db.session.commit()

    return {'forfeited': forfeited}
