import os
import uuid

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import Commendation, EnochWager, Game, PlayerCollectible, User, db
from app.services.collectibles_catalog import CATALOG, CATALOG_BY_ID, COLLECTIONS

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
    commendations = Commendation.query.filter_by(
        subject_id=player.id, kind='commend'
    ).order_by(Commendation.created_at.desc()).all()
    condemnations = Commendation.query.filter_by(
        subject_id=player.id, kind='condemn'
    ).order_by(Commendation.created_at.desc()).all()
    collectible_rows = PlayerCollectible.query.filter_by(user_id=player.id)\
        .order_by(PlayerCollectible.acquired_at.desc()).all()
    drawer = _build_drawer(collectible_rows)

    wager_history = EnochWager.query.filter_by(user_id=player.id)\
        .order_by(EnochWager.created_at.desc()).limit(10).all()

    return render_template(
        'profile.html', player=player, games=games,
        commendations=commendations, condemnations=condemnations,
        drawer=drawer, collections=COLLECTIONS, catalog=CATALOG,
        wager_history=wager_history,
    )


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


@players_bp.route('/account/bio', methods=['POST'])
@login_required
def update_bio():
    bio = request.form.get('bio', '').strip()[:300]
    current_user.bio = bio
    db.session.commit()
    flash('Bio updated.', 'success')
    return redirect(url_for('players.my_account'))


@players_bp.route('/account/toggle-naming', methods=['POST'])
@login_required
def toggle_naming():
    current_user.can_name_openings = not current_user.can_name_openings
    db.session.commit()
    state = 'enabled' if current_user.can_name_openings else 'disabled'
    flash(f'Sequence naming {state}.', 'success')
    return redirect(url_for('players.my_account'))


@players_bp.route('/chronicle')
@login_required
def chronicle():
    page = request.args.get('page', 1, type=int)
    games = Game.query.filter(
        Game.status.in_(['completed', 'forfeited'])
    ).order_by(Game.completed_at.desc()).paginate(page=page, per_page=20)
    return render_template('chronicle.html', games=games)


@players_bp.route('/api/drawer/<int:user_id>')
@login_required
def drawer_api(user_id):
    rows = PlayerCollectible.query.filter_by(user_id=user_id)\
        .order_by(PlayerCollectible.acquired_at.desc()).all()
    drawer = _build_drawer(rows)
    return jsonify(drawer)


def _build_drawer(rows):
    """Build a structured drawer dict grouped by collection with stacking."""
    owned = {}
    for r in rows:
        key = r.item_id
        if key not in owned:
            owned[key] = []
        owned[key].append({
            'game_id': r.game_id,
            'acquired_at': r.acquired_at.isoformat() if r.acquired_at else None,
        })

    drawer = {}
    for coll in COLLECTIONS:
        items_in_coll = [it for it in CATALOG if it['collection'] == coll]
        slots = []
        for it in items_in_coll:
            stack = owned.get(it['id'], [])
            slots.append({
                'item': it,
                'earned': len(stack) > 0,
                'count': len(stack),
                'instances': stack,
            })
        drawer[coll] = slots
    return drawer
