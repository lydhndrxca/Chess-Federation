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

    all_games = Game.query.filter(
        (Game.white_id == player.id) | (Game.black_id == player.id)
    ).filter(
        Game.status.in_(['completed', 'forfeited'])
    ).order_by(Game.completed_at.desc()).all()

    fed_games = [g for g in all_games if not g.is_practice]
    practice_games = [g for g in all_games if g.is_practice]

    match_stats = _build_match_stats(player, all_games, fed_games, practice_games)

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
        'profile.html', player=player,
        all_games=all_games, fed_games=fed_games,
        practice_games=practice_games, match_stats=match_stats,
        commendations=commendations, condemnations=condemnations,
        drawer=drawer, collections=COLLECTIONS, catalog=CATALOG,
        wager_history=wager_history,
    )


def _player_result(game, player_id):
    if game.result == '1-0':
        return 'win' if game.white_id == player_id else 'loss'
    elif game.result == '0-1':
        return 'win' if game.black_id == player_id else 'loss'
    elif game.result == '1/2-1/2':
        return 'draw'
    elif game.result == '0-0':
        return 'loss'
    return None


def _build_match_stats(player, all_games, fed_games, practice_games):
    pid = player.id

    def _compute(games_list):
        w = l = d = 0
        total_moves = 0
        as_white_w = as_white_l = as_black_w = as_black_l = 0
        longest = shortest = None
        for g in games_list:
            r = _player_result(g, pid)
            if r == 'win':
                w += 1
                if g.white_id == pid:
                    as_white_w += 1
                else:
                    as_black_w += 1
            elif r == 'loss':
                l += 1
                if g.white_id == pid:
                    as_white_l += 1
                else:
                    as_black_l += 1
            elif r == 'draw':
                d += 1
            total_moves += g.move_count or 0
            if g.move_count and g.move_count > 0:
                if longest is None or g.move_count > longest:
                    longest = g.move_count
                if shortest is None or g.move_count < shortest:
                    shortest = g.move_count
        total = w + l + d
        return {
            'total': total,
            'wins': w, 'losses': l, 'draws': d,
            'win_pct': round(100 * w / total) if total else 0,
            'avg_moves': round(total_moves / total) if total else 0,
            'longest': longest or 0,
            'shortest': shortest or 0,
            'as_white_wins': as_white_w, 'as_white_losses': as_white_l,
            'as_black_wins': as_black_w, 'as_black_losses': as_black_l,
        }

    overall = _compute(all_games)
    federation = _compute(fed_games)
    practice = _compute(practice_games)

    opponents = {}
    for g in fed_games:
        opp_id = g.black_id if g.white_id == pid else g.white_id
        if opp_id not in opponents:
            opp_user = g.black if g.white_id == pid else g.white
            opponents[opp_id] = {'user': opp_user, 'wins': 0, 'losses': 0, 'draws': 0}
        r = _player_result(g, pid)
        if r == 'win':
            opponents[opp_id]['wins'] += 1
        elif r == 'loss':
            opponents[opp_id]['losses'] += 1
        elif r == 'draw':
            opponents[opp_id]['draws'] += 1

    head_to_head = sorted(opponents.values(),
                          key=lambda x: x['wins'] + x['losses'] + x['draws'],
                          reverse=True)

    return {
        'overall': overall,
        'federation': federation,
        'practice': practice,
        'head_to_head': head_to_head,
    }


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
