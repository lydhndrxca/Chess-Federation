import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import Game, User, db

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

players_bp = Blueprint('players', __name__)


@players_bp.route('/players')
@login_required
def player_list():
    players = User.query.order_by(User.rating.desc()).all()
    return render_template('players.html', players=players)


@players_bp.route('/player/<username>')
@login_required
def player_profile(username):
    player = User.query.filter_by(username=username).first_or_404()
    games = Game.query.filter(
        (Game.white_id == player.id) | (Game.black_id == player.id)
    ).filter(
        Game.status.in_(['completed', 'forfeited'])
    ).order_by(Game.completed_at.desc()).all()
    return render_template('profile.html', player=player, games=games)


@players_bp.route('/account')
@login_required
def my_account():
    return render_template('account.html')


@players_bp.route('/account/avatar', methods=['POST'])
@login_required
def upload_avatar():
    file = request.files.get('avatar')
    if not file or file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('players.my_account'))

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        flash('Only PNG, JPG, GIF, and WebP images are allowed.', 'error')
        return redirect(url_for('players.my_account'))

    if current_user.avatar_filename:
        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.avatar_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    filename = f'{uuid.uuid4().hex}.{ext}'
    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    current_user.avatar_filename = filename
    db.session.commit()
    flash('Avatar updated!', 'success')
    return redirect(url_for('players.my_account'))


@players_bp.route('/chronicle')
@login_required
def chronicle():
    page = request.args.get('page', 1, type=int)
    games = Game.query.filter(
        Game.status.in_(['completed', 'forfeited'])
    ).order_by(Game.completed_at.desc()).paginate(page=page, per_page=20)
    return render_template('chronicle.html', games=games)
