from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import Game, User
from app.services.matchmaking import check_forfeits, get_current_season, get_current_week

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('home.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    check_forfeits()

    week = get_current_week()
    season = get_current_season()

    weekly_games = Game.query.filter_by(
        week_number=week, season=season
    ).all()

    current_game = None
    for g in weekly_games:
        if current_user.id in (g.white_id, g.black_id):
            current_game = g
            break

    standings = User.query.filter_by(
        is_active_player=True
    ).order_by(User.rating.desc()).all()

    return render_template(
        'dashboard.html',
        week=week,
        season=season,
        weekly_games=weekly_games,
        current_game=current_game,
        standings=standings,
    )
