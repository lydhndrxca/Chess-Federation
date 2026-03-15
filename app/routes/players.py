import os
import uuid

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import Commendation, CryptGame, EnochWager, Game, PlayerCollectible, User, db
from app.services.collectibles_catalog import CATALOG, CATALOG_BY_ID, COLLECTIONS
from app.services.rating import get_progression

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

    progression = get_progression(player.rating)

    crypt_completed = CryptGame.query.filter_by(user_id=player.id)\
        .filter(CryptGame.completed_at.isnot(None)).all()
    crypt_best_wave = max((c.wave for c in crypt_completed), default=0)
    crypt_best_score = max((c.score for c in crypt_completed), default=0)
    crypt_total_kills = sum(c.kills for c in crypt_completed)
    crypt_runs = len(crypt_completed)
    crypt_rating_net = sum(c.rating_result for c in crypt_completed
                          if c.rating_result is not None)

    return render_template(
        'profile.html', player=player,
        all_games=all_games, fed_games=fed_games,
        practice_games=practice_games, match_stats=match_stats,
        commendations=commendations, condemnations=condemnations,
        drawer=drawer, collections=COLLECTIONS, catalog=CATALOG,
        wager_history=wager_history, progression=progression,
        crypt_best_wave=crypt_best_wave, crypt_best_score=crypt_best_score,
        crypt_total_kills=crypt_total_kills, crypt_runs=crypt_runs,
        crypt_rating_net=crypt_rating_net,
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
    rival = _get_rival(current_user.id)
    progression = get_progression(current_user.rating)
    return render_template('account.html', rival=rival, progression=progression)


def _get_rival(user_id):
    """Find the player with the most games played against this user."""
    games = Game.query.filter(
        (Game.white_id == user_id) | (Game.black_id == user_id),
        Game.status.in_(['completed', 'forfeited']),
        Game.is_practice == False,
    ).all()

    opp_stats = {}
    for g in games:
        opp_id = g.black_id if g.white_id == user_id else g.white_id
        if opp_id not in opp_stats:
            opp_stats[opp_id] = {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0}
        opp_stats[opp_id]['total'] += 1
        r = _player_result(g, user_id)
        if r == 'win':
            opp_stats[opp_id]['wins'] += 1
        elif r == 'loss':
            opp_stats[opp_id]['losses'] += 1
        elif r == 'draw':
            opp_stats[opp_id]['draws'] += 1

    if not opp_stats:
        return None

    rival_id = max(opp_stats, key=lambda k: opp_stats[k]['total'])
    rival_user = db.session.get(User, rival_id)
    if not rival_user:
        return None
    s = opp_stats[rival_id]
    return {
        'user': rival_user,
        'wins': s['wins'],
        'losses': s['losses'],
        'draws': s['draws'],
        'total': s['total'],
    }


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
    from app.models import MarketTransaction, WeeklySchedule
    from app.services.matchmaking import get_current_week, get_current_season
    from collections import OrderedDict
    import calendar

    games = Game.query.filter(
        Game.status.in_(['completed', 'forfeited'])
    ).order_by(Game.completed_at.desc()).all()

    weeks = OrderedDict()
    for g in games:
        key = (g.season, g.week_number)
        if key not in weeks:
            season_year = g.season // 100
            season_month = g.season % 100
            month_name = calendar.month_name[season_month] if 1 <= season_month <= 12 else str(season_month)
            sched = WeeklySchedule.query.filter_by(
                week_number=g.week_number, season=g.season
            ).first()
            weeks[key] = {
                'week': g.week_number,
                'season': g.season,
                'label': f"Week {g.week_number} — {month_name} {season_year}",
                'decree': sched.rule_declaration if sched and sched.rule_declaration else None,
                'decree_holder': sched.power_holder.username if sched and sched.power_holder else None,
                'weekly_games': [],
                'casual_games': [],
                'enoch_games': [],
                'market_events': [],
            }
        entry = weeks[key]
        if g.is_practice:
            entry['enoch_games'].append(g)
        elif g.game_type == 'casual':
            entry['casual_games'].append(g)
        else:
            entry['weekly_games'].append(g)

    big_txs = MarketTransaction.query.filter(
        MarketTransaction.denarius_amount >= 500
    ).order_by(MarketTransaction.created_at.desc()).limit(50).all()
    for tx in big_txs:
        key = None
        for wk in weeks:
            if weeks[wk]['season'] == tx.created_at.year * 100 + tx.created_at.month:
                key = wk
                break
        if key:
            action = 'bought' if tx.tx_type == 'buy' else 'sold'
            weeks[key]['market_events'].append({
                'user': tx.user.username if tx.user else '???',
                'text': f"{action} {tx.coin_symbol.upper()} for ${int(tx.denarius_amount):,}",
                'date': tx.created_at,
            })

    return render_template('chronicle.html', weeks=list(weeks.values()))


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
