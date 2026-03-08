from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, and_

from app.models import Game, User, WeeklySchedule
from app.services.matchmaking import check_forfeits, get_current_season, get_current_week

main_bp = Blueprint('main', __name__)


def _head_to_head(user_id, opponent_id):
    """Return (wins, losses, draws) for user_id vs opponent_id across all games."""
    games = Game.query.filter(
        Game.status.in_(['completed', 'forfeited']),
        or_(
            and_(Game.white_id == user_id, Game.black_id == opponent_id),
            and_(Game.white_id == opponent_id, Game.black_id == user_id),
        ),
    ).all()

    w, l, d = 0, 0, 0
    for g in games:
        if g.result == '1/2-1/2':
            d += 1
        elif g.result == '0-0':
            l += 1
        elif g.result == '1-0':
            if g.white_id == user_id:
                w += 1
            else:
                l += 1
        elif g.result == '0-1':
            if g.black_id == user_id:
                w += 1
            else:
                l += 1
    return w, l, d


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.standings'))
    return render_template('home.html')


@main_bp.route('/standings')
@login_required
def standings():
    check_forfeits()

    week = get_current_week()
    year, month = get_current_season()
    season_key = year * 100 + month

    weekly_games = Game.query.filter_by(
        week_number=week, season=season_key
    ).all()

    my_games = []
    for g in weekly_games:
        if current_user.id not in (g.white_id, g.black_id):
            continue
        my_color = 'white' if current_user.id == g.white_id else 'black'
        opponent = g.black if my_color == 'white' else g.white
        is_my_turn = (g.status in ('pending', 'active') and g.current_turn == my_color)
        h2h = _head_to_head(current_user.id, opponent.id)
        my_games.append({
            'game': g,
            'opponent': opponent,
            'my_color': my_color,
            'is_my_turn': is_my_turn,
            'h2h': h2h,
        })

    # Sort: games where it's your turn first, then active, then completed
    turn_order = {True: 0, False: 1}
    status_order = {'pending': 0, 'active': 1, 'completed': 2, 'forfeited': 3}
    my_games.sort(key=lambda x: (turn_order.get(x['is_my_turn'], 1), status_order.get(x['game'].status, 9)))

    other_games = [g for g in weekly_games if current_user.id not in (g.white_id, g.black_id)]

    standings_list = User.query.filter_by(
        is_active_player=True
    ).order_by(User.rating.desc()).all()

    schedule = WeeklySchedule.query.filter_by(
        week_number=week, season=season_key
    ).first()

    return render_template(
        'standings.html',
        week=week,
        season_year=year,
        season_month=month,
        weekly_games=weekly_games,
        my_games=my_games,
        other_games=other_games,
        standings=standings_list,
        schedule=schedule,
    )


@main_bp.route('/board')
@login_required
def board_redirect():
    """Redirect to the player's active game where it's their turn, or first active, or standings."""
    week = get_current_week()
    year, month = get_current_season()
    season_key = year * 100 + month

    active = Game.query.filter(
        Game.week_number == week,
        Game.season == season_key,
        Game.status.in_(['pending', 'active']),
        (Game.white_id == current_user.id) | (Game.black_id == current_user.id),
    ).all()

    if not active:
        return redirect(url_for('main.standings'))

    for g in active:
        my_color = 'white' if g.white_id == current_user.id else 'black'
        if g.current_turn == my_color:
            return redirect(url_for('game.view_game', game_id=g.id))

    return redirect(url_for('game.view_game', game_id=active[0].id))
