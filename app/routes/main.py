from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import Game, User, WeeklySchedule
from app.services.matchmaking import check_forfeits, get_current_season, get_current_week

main_bp = Blueprint('main', __name__)


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

    my_games = [
        g for g in weekly_games
        if current_user.id in (g.white_id, g.black_id)
    ]

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
