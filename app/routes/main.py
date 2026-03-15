import random
import time

import requests
from flask import Blueprint, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, and_

from app.models import (
    Game, User, WeeklySchedule, ChatMessage, Challenge,
    MarketHolding, MarketTransaction, CourierGame, db,
)
from app.services.matchmaking import (
    check_forfeits, generate_weekly_pairings, get_current_season,
    get_current_week, get_week_deadline, get_decree_deadline,
)

main_bp = Blueprint('main', __name__)


def _head_to_head(user_id, opponent_id):
    """Return (wins, losses, draws) for user_id vs opponent_id across all games."""
    games = Game.query.filter(
        Game.status.in_(['completed', 'forfeited']),
        Game.is_practice == False,
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

    try:
        from app.services.power import ensure_rotation_order
        ensure_rotation_order()
    except (ImportError, Exception):
        pass
    generate_weekly_pairings()

    week = get_current_week()
    year, month = get_current_season()
    season_key = year * 100 + month

    weekly_games = Game.query.filter(
        Game.week_number == week, Game.season == season_key,
        Game.is_practice == False,
        or_(Game.game_type == 'weekly', Game.game_type == None),
    ).all()

    def _build_game_card(g):
        my_color = 'white' if current_user.id == g.white_id else 'black'
        opponent = g.black if my_color == 'white' else g.white
        if not opponent:
            return None
        is_my_turn = (g.status in ('pending', 'active') and g.current_turn == my_color)
        h2h = _head_to_head(current_user.id, opponent.id)
        return {
            'game': g,
            'opponent': opponent,
            'my_color': my_color,
            'is_my_turn': is_my_turn,
            'h2h': h2h,
        }

    my_games = []
    for g in weekly_games:
        if current_user.id not in (g.white_id, g.black_id):
            continue
        card = _build_game_card(g)
        if card:
            my_games.append(card)

    turn_order = {True: 0, False: 1}
    status_order = {'pending': 0, 'active': 1, 'completed': 2, 'forfeited': 3}
    my_games.sort(key=lambda x: (turn_order.get(x['is_my_turn'], 1), status_order.get(x['game'].status, 9)))

    other_games = [g for g in weekly_games if current_user.id not in (g.white_id, g.black_id)]

    # Casual games (standard rules, no deadline, unlimited)
    casual_games_q = Game.query.filter(
        Game.game_type == 'casual',
        Game.is_practice == False,
        or_(Game.white_id == current_user.id, Game.black_id == current_user.id),
        Game.status.in_(['pending', 'active', 'completed']),
    ).order_by(Game.id.desc()).limit(20).all()

    my_casual_games = [c for c in (_build_game_card(g) for g in casual_games_q) if c]
    my_casual_games.sort(key=lambda x: (
        turn_order.get(x['is_my_turn'], 1),
        status_order.get(x['game'].status, 9),
    ))

    # Pending challenges
    incoming_challenges = Challenge.query.filter_by(
        challenged_id=current_user.id, status='pending'
    ).all()

    # All players for challenging
    all_players = User.query.filter(
        User.is_active_player == True,
        User.is_bot == False,
        User.id != current_user.id,
    ).order_by(User.username).all()

    # Players with no active casual game against current user
    active_casual_opp_ids = set()
    for g in casual_games_q:
        if g.status in ('pending', 'active'):
            opp_id = g.black_id if g.white_id == current_user.id else g.white_id
            active_casual_opp_ids.add(opp_id)
    challengeable_players = [p for p in all_players if p.id not in active_casual_opp_ids]

    standings_list = User.query.filter_by(
        is_active_player=True
    ).order_by(User.rating.desc()).all()

    schedule = WeeklySchedule.query.filter_by(
        week_number=week, season=season_key
    ).first()

    if not schedule:
        try:
            from app.services.power import get_current_holder
            holder = get_current_holder()
            if holder:
                schedule = WeeklySchedule(
                    week_number=week, season=season_key,
                    power_position_holder_id=holder.id,
                )
                db.session.add(schedule)
                db.session.commit()
        except (ImportError, Exception):
            pass

    match_deadline = get_week_deadline()
    decree_deadline = get_decree_deadline()
    match_deadline_iso = match_deadline.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    decree_deadline_iso = decree_deadline.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

    next_holder = None
    try:
        from app.services.power import get_next_holder
        next_holder = get_next_holder()
    except (ImportError, Exception):
        pass

    from app.services.enoch_ai import get_current_mood
    enoch_mood = get_current_mood()

    from app.models import FourPlayerGame
    active_reckoning = FourPlayerGame.query.filter(
        FourPlayerGame.status.in_(['waiting', 'active'])
    ).order_by(FourPlayerGame.created_at.desc()).first()

    weekly_rule = None
    try:
        from app.services.weekly_rule import (
            RULE_ACTIVE, RULE_TITLE, RULE_DESCRIPTION, RULE_ENOCH_ANNOUNCEMENT,
            ensure_chat_announcement,
        )
        if RULE_ACTIVE:
            weekly_rule = {
                'title': RULE_TITLE,
                'description': RULE_DESCRIPTION,
                'enoch_text': RULE_ENOCH_ANNOUNCEMENT,
            }
            ensure_chat_announcement()
    except ImportError:
        pass

    try:
        from app.services.enoch_chat import (
            ensure_casual_announcement, ensure_crypt_revenge_announcement,
            ensure_zombie_announcement, ensure_reckoning_automove_announcement,
            ensure_market_announcement, ensure_courier_announcement,
            ensure_courier_brain_announcement, ensure_market_3x_announcement,
            ensure_weekly_summary,
        )
        ensure_casual_announcement()
        ensure_crypt_revenge_announcement()
        ensure_zombie_announcement()
        ensure_reckoning_automove_announcement()
        ensure_market_announcement()
        ensure_courier_announcement()
        ensure_courier_brain_announcement()
        ensure_market_3x_announcement()
        ensure_weekly_summary()
    except (ImportError, Exception):
        pass

    from app.routes.hall import _serialize_msg
    recent_chat_raw = ChatMessage.query.order_by(
        ChatMessage.timestamp.desc()
    ).limit(15).all()
    recent_chat_raw.reverse()
    recent_chat = recent_chat_raw
    recent_chat_json = [_serialize_msg(m) for m in recent_chat_raw]

    return render_template(
        'standings.html',
        week=week,
        season_year=year,
        season_month=month,
        weekly_games=weekly_games,
        my_games=my_games,
        other_games=other_games,
        my_casual_games=my_casual_games,
        incoming_challenges=incoming_challenges,
        all_players=all_players,
        challengeable_players=challengeable_players,
        standings=standings_list,
        schedule=schedule,
        match_deadline_iso=match_deadline_iso,
        decree_deadline_iso=decree_deadline_iso,
        next_holder=next_holder,
        enoch_mood=enoch_mood,
        weekly_rule=weekly_rule,
        active_reckoning=active_reckoning,
        recent_chat=recent_chat,
        recent_chat_json=recent_chat_json,
    )


@main_bp.route('/api/my-turns')
@login_required
def api_my_turns():
    from flask import jsonify
    active = Game.query.filter(
        or_(Game.white_id == current_user.id, Game.black_id == current_user.id),
        Game.status.in_(['pending', 'active']),
    ).all()
    turns = []
    for g in active:
        my_color = 'white' if g.white_id == current_user.id else 'black'
        if g.current_turn == my_color:
            opp = g.black if my_color == 'white' else g.white
            turns.append({
                'game_id': g.id,
                'opponent': opp.username if opp else 'Unknown',
            })
    return jsonify({'turns': turns, 'count': len(turns)})


@main_bp.route('/rankings')
@login_required
def rankings():
    from app.services.rating import TIERS, get_tier, get_progression

    standings_list = User.query.filter_by(
        is_active_player=True
    ).order_by(User.rating.desc()).all()

    player_data = []
    for player in standings_list:
        prog = get_progression(player.rating)
        player_data.append({
            'user': player,
            'tier': prog['current'],
            'progression': prog,
        })

    tier_data = []
    for lvl, threshold, name, desc in TIERS:
        members = [p for p in standings_list if get_tier(p.rating)['level'] == lvl]
        tier_data.append({
            'level': lvl,
            'threshold': threshold,
            'name': name,
            'desc': desc,
            'members': members,
        })

    return render_template(
        'rankings.html',
        standings=player_data,
        tiers=tier_data,
    )


@main_bp.route('/archive')
@login_required
def archive():
    return _archive_month(None, None)


@main_bp.route('/archive/<int:year>/<int:month>')
@login_required
def archive_month(year, month):
    return _archive_month(year, month)


def _archive_month(year, month):
    from sqlalchemy import func, distinct

    if year is None or month is None:
        cur_year, cur_month = get_current_season()
        if cur_month == 1:
            year, month = cur_year - 1, 12
        else:
            year, month = cur_year, cur_month - 1

    season_key = year * 100 + month

    available = (
        db.session.query(Game.season)
        .distinct()
        .order_by(Game.season.desc())
        .all()
    )
    months_list = []
    for (s,) in available:
        y, m = divmod(s, 100)
        if 1 <= m <= 12 and y > 2000:
            months_list.append({'year': y, 'month': m, 'season_key': s})

    games = Game.query.filter_by(season=season_key, is_practice=False).order_by(
        Game.week_number, Game.id
    ).all()

    weeks = {}
    for g in games:
        weeks.setdefault(g.week_number, []).append(g)

    schedules = WeeklySchedule.query.filter_by(season=season_key).order_by(
        WeeklySchedule.week_number
    ).all()
    decree_map = {s.week_number: s for s in schedules}

    player_ids = set()
    for g in games:
        player_ids.add(g.white_id)
        player_ids.add(g.black_id)
    players = User.query.filter(User.id.in_(player_ids)).all() if player_ids else []

    stats = {}
    for p in players:
        stats[p.id] = {'user': p, 'wins': 0, 'losses': 0, 'draws': 0, 'rating_change': 0}

    for g in games:
        if g.status not in ('completed', 'forfeited'):
            continue
        if g.white_id not in stats or g.black_id not in stats:
            continue
        if g.result == '1-0':
            stats[g.white_id]['wins'] += 1
            stats[g.black_id]['losses'] += 1
        elif g.result == '0-1':
            stats[g.black_id]['wins'] += 1
            stats[g.white_id]['losses'] += 1
        elif g.result == '1/2-1/2':
            stats[g.white_id]['draws'] += 1
            stats[g.black_id]['draws'] += 1
        elif g.result == '0-0':
            stats[g.white_id]['losses'] += 1
            stats[g.black_id]['losses'] += 1

        if g.rating_change_white is not None:
            stats[g.white_id]['rating_change'] += g.rating_change_white
        if g.rating_change_black is not None:
            stats[g.black_id]['rating_change'] += g.rating_change_black

    sorted_stats = sorted(stats.values(), key=lambda x: x['rating_change'], reverse=True)

    return render_template(
        'archive.html',
        year=year,
        month=month,
        season_key=season_key,
        weeks=weeks,
        decree_map=decree_map,
        sorted_stats=sorted_stats,
        months_list=months_list,
        total_games=len(games),
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


# ── Scrolling news ticker API ──────────────────────────────────

_news_cache = {'ts': 0, 'items': []}
_NEWS_TTL = 900  # 15 minutes

ENOCH_TICKER_QUIPS = [
    "I have been awake for 347 consecutive hours. This is fine.",
    "The pipes are leaking again. I blame the bishops.",
    "Reminder: I see every move you make. Even the ones you take back.",
    "If you're reading this, you should be playing chess.",
    "The sub-basement humidity is at 94%. My ledger pages are curling.",
    "Market tip from Enoch: buy low, sell lower, blame everyone else.",
    "Fun fact: I have never lost a game of chess. I have also never played one. I only watch.",
    "The rats have formed a union. They want better cheese. I told them to file a complaint.",
    "Someone left a knight on e4 for three days. I've named it Gerald.",
    "Current mood: the sound a bishop makes sliding across a wet board.",
    "I found a pawn under the boiler. It's been there since week 2. It seems happy.",
    "The Federation's total net worth changes every 45 seconds. I find this stressful.",
    "Enoch's investment advice: invest in whatever scares you the most.",
    "Breaking: local steward discovers new crack in sub-basement wall. More at never.",
    "The candles are low. The ledger is heavy. The chess never stops.",
    "I've been told my management style is 'unsettling.' I consider this a compliment.",
    "Today's chess wisdom: if you don't know what to do, move a pawn. If that fails, blame Enoch.",
    "Weather in the sub-basement: perpetual damp, chance of existential dread.",
    "ALERT: Someone forfeited. I won't say who. But I'm disappointed.",
    "The 3x market amplifier was my idea. I accept no responsibility for the consequences.",
    "Knights have lame knees this week. I find this deeply satisfying.",
    "Courier Run tip: your courier is not your friend. It is your burden.",
    "Remember: every dollar you lose in the market goes directly into my satisfaction.",
    "I have organized the complaint box by level of futility. Yours is near the top.",
    "The Federation clock ticks. The deadline approaches. The steward watches.",
]


def _fetch_world_headlines():
    """Fetch world news via free RSS-to-JSON service (no API key needed)."""
    feeds = [
        'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
        'https://feeds.bbci.co.uk/news/rss.xml',
        'https://rss.cnn.com/rss/edition.rss',
    ]
    items = []
    for feed_url in feeds:
        try:
            r = requests.get(
                'https://api.rss2json.com/v1/api.json',
                params={'rss_url': feed_url, 'count': 6},
                timeout=8,
            )
            if r.status_code == 200:
                data = r.json()
                for entry in (data.get('items') or [])[:6]:
                    title = entry.get('title', '').strip()
                    if title and len(title) > 10:
                        items.append({'text': title, 'source': 'News'})
                if items:
                    break
        except Exception:
            continue
    return items


def _fetch_crypto_headlines():
    """Fetch crypto-relevant ticker items from CoinGecko trending + top movers."""
    items = []
    try:
        r = requests.get(
            'https://api.coingecko.com/api/v3/search/trending',
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            for c in (data.get('coins') or [])[:6]:
                coin = c.get('item', {})
                name = coin.get('name', '')
                sym = coin.get('symbol', '')
                if name:
                    items.append({
                        'text': f'{name} ({sym}) is trending on crypto markets',
                        'source': 'Crypto',
                    })
    except Exception:
        pass

    try:
        from app.routes.market import _fetch_markets
        markets = _fetch_markets()
        if markets:
            top_gainers = sorted(
                markets, key=lambda c: c.get('price_change_percentage_24h') or 0,
                reverse=True,
            )[:3]
            top_losers = sorted(
                markets, key=lambda c: c.get('price_change_percentage_24h') or 0,
            )[:3]
            for c in top_gainers:
                pct = c.get('price_change_percentage_24h', 0)
                price = c.get('current_price', 0)
                if pct > 0:
                    items.append({
                        'text': (f"{c['name']} ({c.get('symbol','').upper()}) "
                                 f"${price:,.2f} — up {pct:.1f}% today"),
                        'source': 'Crypto',
                    })
            for c in top_losers:
                pct = c.get('price_change_percentage_24h', 0)
                price = c.get('current_price', 0)
                if pct < -3:
                    items.append({
                        'text': (f"{c['name']} ({c.get('symbol','').upper()}) "
                                 f"${price:,.2f} — down {abs(pct):.1f}% today"),
                        'source': 'Crypto',
                    })
    except Exception:
        pass
    return items


def _build_federation_items():
    """Build ticker items from player data and recent federation events."""
    items = []
    try:
        users = User.query.filter_by(is_bot=False).order_by(User.rating.desc()).all()
        for u in users:
            items.append({
                'text': f'{u.username}: Rating {u.rating} | ${u.roman_gold:,} | {u.wins}W-{u.losses}L-{u.draws}D',
                'source': 'Federation',
            })

        holdings_by_user = {}
        for h in MarketHolding.query.all():
            holdings_by_user.setdefault(h.user_id, []).append(h)

        from app.routes.market import _price_map
        all_coin_ids = set()
        for hs in holdings_by_user.values():
            for h in hs:
                all_coin_ids.add(h.coin_id)
        prices = _price_map(all_coin_ids) if all_coin_ids else {}

        for u in users:
            user_hs = holdings_by_user.get(u.id, [])
            if user_hs:
                total_val = sum(h.amount * prices.get(h.coin_id, 0) for h in user_hs)
                total_inv = sum(h.amount * h.avg_buy_price for h in user_hs)
                pnl = total_val - total_inv
                sign = '+' if pnl >= 0 else ''
                items.append({
                    'text': f"{u.username}'s portfolio: ${total_val:,.0f} ({sign}${pnl:,.0f})",
                    'source': 'Market',
                })

        recent_games = Game.query.filter_by(status='completed').order_by(
            Game.completed_at.desc()
        ).limit(5).all()
        user_map = {u.id: u.username for u in users}
        for g in recent_games:
            w = user_map.get(g.white_id, '?')
            b = user_map.get(g.black_id, '?')
            if g.result == '1-0':
                items.append({'text': f'{w} defeated {b} in Federation match', 'source': 'Match'})
            elif g.result == '0-1':
                items.append({'text': f'{b} defeated {w} in Federation match', 'source': 'Match'})
            elif g.result == '1/2-1/2':
                items.append({'text': f'{w} drew with {b} in Federation match', 'source': 'Match'})

        courier_wins = CourierGame.query.filter_by(
            winner='white'
        ).order_by(CourierGame.completed_at.desc()).limit(3).all()
        for cg in courier_wins:
            uname = user_map.get(cg.user_id, '?')
            items.append({
                'text': f'{uname} completed a Courier Run and earned $50',
                'source': 'Courier',
            })

    except Exception:
        pass
    return items


def _build_enoch_quips():
    """Pick a few random Enoch personality quips for the ticker."""
    picks = random.sample(ENOCH_TICKER_QUIPS, min(5, len(ENOCH_TICKER_QUIPS)))
    return [{'text': q, 'source': 'Enoch'} for q in picks]


@main_bp.route('/api/ticker')
@login_required
def api_ticker():
    """Return scrolling ticker items: news, crypto, federation stats, Enoch quips."""
    now = time.time()
    if now - _news_cache['ts'] > _NEWS_TTL or not _news_cache['items']:
        news = _fetch_world_headlines()
        crypto = _fetch_crypto_headlines()
        federation = _build_federation_items()
        quips = _build_enoch_quips()

        all_items = []
        all_items.extend(news[:8])
        all_items.extend(crypto[:8])
        all_items.extend(federation)
        all_items.extend(quips)
        random.shuffle(all_items)
        _news_cache['items'] = all_items
        _news_cache['ts'] = now

    return jsonify(items=_news_cache['items'])
