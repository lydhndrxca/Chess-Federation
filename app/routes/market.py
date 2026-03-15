"""Denarius Exchange — crypto market powered by CoinGecko free API."""

import random
import time
from datetime import datetime, timezone

import requests
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.models import (
    ChatMessage, MarketHolding, MarketOrder, MarketTransaction, User, db,
)

market_bp = Blueprint('market', __name__)

DENARIUS_USD = 1
COINGECKO_MARKETS = (
    'https://api.coingecko.com/api/v3/coins/markets'
    '?vs_currency=usd&order=market_cap_desc&per_page=100&page=1'
    '&sparkline=false&price_change_percentage=24h'
)
COINGECKO_SIMPLE = 'https://api.coingecko.com/api/v3/simple/price'

_price_cache = {'ts': 0, 'data': []}
CACHE_TTL = 45


def _fetch_markets():
    now = time.time()
    if now - _price_cache['ts'] < CACHE_TTL and _price_cache['data']:
        return _price_cache['data']
    try:
        r = requests.get(COINGECKO_MARKETS, timeout=10)
        r.raise_for_status()
        _price_cache['data'] = r.json()
        _price_cache['ts'] = now
    except Exception:
        pass
    return _price_cache['data']


def _price_map(coins=None):
    """Return {coin_id: price_usd} from cached market data."""
    data = _fetch_markets()
    pm = {}
    for c in data:
        if coins and c['id'] not in coins:
            continue
        pm[c['id']] = c.get('current_price') or 0
    return pm


def _check_limit_orders(user_id=None):
    """Fill any limit orders whose target price has been reached."""
    prices = _price_map()
    if not prices:
        return

    q = MarketOrder.query.filter_by(status='pending')
    if user_id:
        q = q.filter_by(user_id=user_id)
    pending = q.all()

    for order in pending:
        price = prices.get(order.coin_id)
        if price is None:
            continue

        filled = False
        if order.order_type == 'buy' and price <= order.target_price:
            user = User.query.get(order.user_id)
            if not user or user.roman_gold < order.denarius_amount:
                continue
            crypto_amount = (order.denarius_amount * DENARIUS_USD) / price
            user.roman_gold -= int(order.denarius_amount)
            _upsert_holding(user.id, order.coin_id, order.coin_symbol,
                            _coin_name_from_cache(order.coin_id),
                            crypto_amount, price)
            _record_tx(user.id, order.coin_id, order.coin_symbol, 'buy',
                       crypto_amount, price, order.denarius_amount)
            _post_trade_update(user.username, 'buy', order.coin_symbol,
                               order.denarius_amount)
            filled = True

        elif order.order_type == 'sell' and price >= order.target_price:
            holding = MarketHolding.query.filter_by(
                user_id=order.user_id, coin_id=order.coin_id
            ).first()
            if not holding or holding.amount < order.crypto_amount:
                continue
            user = User.query.get(order.user_id)
            if not user:
                continue
            denarius_back = (order.crypto_amount * price) / DENARIUS_USD
            holding.amount -= order.crypto_amount
            if holding.amount < 1e-12:
                db.session.delete(holding)
            user.roman_gold += int(denarius_back)
            _record_tx(user.id, order.coin_id, order.coin_symbol, 'sell',
                       order.crypto_amount, price, denarius_back)
            _post_trade_update(user.username, 'sell', order.coin_symbol,
                               denarius_back)
            filled = True

        if filled:
            order.status = 'filled'
            order.filled_at = datetime.now(timezone.utc)

    db.session.commit()


def _upsert_holding(user_id, coin_id, coin_symbol, coin_name,
                    add_amount, buy_price):
    h = MarketHolding.query.filter_by(
        user_id=user_id, coin_id=coin_id
    ).first()
    if h:
        total_cost = h.avg_buy_price * h.amount + buy_price * add_amount
        h.amount += add_amount
        h.avg_buy_price = total_cost / h.amount if h.amount else 0
    else:
        h = MarketHolding(
            user_id=user_id, coin_id=coin_id, coin_symbol=coin_symbol,
            coin_name=coin_name, amount=add_amount, avg_buy_price=buy_price,
        )
        db.session.add(h)


def _record_tx(user_id, coin_id, coin_symbol, tx_type,
               crypto_amount, price_usd, denarius_amount):
    db.session.add(MarketTransaction(
        user_id=user_id, coin_id=coin_id, coin_symbol=coin_symbol,
        tx_type=tx_type, crypto_amount=crypto_amount,
        price_usd=price_usd, denarius_amount=denarius_amount,
    ))


def _coin_name_from_cache(coin_id):
    for c in _price_cache.get('data', []):
        if c['id'] == coin_id:
            return c.get('name', coin_id)
    return coin_id


def _post_trade_update(username, action, symbol, dollar_amt):
    """Post a brief one-liner to Federation Hall chat about a trade."""
    sym = symbol.upper()
    amt = f"${int(dollar_amt):,}"
    if action == 'buy':
        text = f"{username} bought {sym} for {amt}."
    else:
        text = f"{username} sold {sym} for {amt}."
    msg = ChatMessage(content=text, is_bot=True, bot_name='Enoch')
    db.session.add(msg)


def _enoch_line(category):
    from app.services.market_dialogue import (
        MARKET_ENTER, MARKET_BUY, MARKET_SELL, MARKET_PROFIT,
        MARKET_LOSS, MARKET_IDLE, MARKET_LIMIT_SET, MARKET_LIMIT_FILLED,
        MARKET_COIN_QUIPS,
    )
    pools = {
        'enter': MARKET_ENTER,
        'buy': MARKET_BUY,
        'sell': MARKET_SELL,
        'profit': MARKET_PROFIT,
        'loss': MARKET_LOSS,
        'idle': MARKET_IDLE,
        'limit_set': MARKET_LIMIT_SET,
        'limit_filled': MARKET_LIMIT_FILLED,
        'coin': MARKET_COIN_QUIPS,
    }
    pool = pools.get(category, MARKET_IDLE)
    return random.choice(pool)


# ── Page ──

@market_bp.route('/market')
@login_required
def market_page():
    _check_limit_orders(current_user.id)
    return render_template('market.html',
                           denarius=current_user.roman_gold,
                           denarius_usd=DENARIUS_USD)


# ── API: prices ──

@market_bp.route('/market/api/prices')
@login_required
def api_prices():
    data = _fetch_markets()
    coins = []
    for c in data:
        coins.append({
            'id': c['id'],
            'symbol': c.get('symbol', ''),
            'name': c.get('name', ''),
            'image': c.get('image', ''),
            'price': c.get('current_price', 0),
            'change_24h': c.get('price_change_percentage_24h', 0),
            'market_cap': c.get('market_cap', 0),
            'volume': c.get('total_volume', 0),
        })
    return jsonify(coins=coins, enoch=_enoch_line('idle'))


# ── API: portfolio ──

@market_bp.route('/market/api/portfolio')
@login_required
def api_portfolio():
    _check_limit_orders(current_user.id)
    holdings = MarketHolding.query.filter_by(user_id=current_user.id).all()
    prices = _price_map({h.coin_id for h in holdings})

    total_invested = 0
    total_current = 0
    items = []
    for h in holdings:
        price = prices.get(h.coin_id, 0)
        current_val = h.amount * price
        invested_val = h.amount * h.avg_buy_price
        total_invested += invested_val
        total_current += current_val
        items.append({
            'coin_id': h.coin_id,
            'symbol': h.coin_symbol,
            'name': h.coin_name,
            'amount': h.amount,
            'avg_buy': h.avg_buy_price,
            'current_price': price,
            'value_usd': current_val,
            'value_denarius': current_val / DENARIUS_USD,
            'pnl_usd': current_val - invested_val,
            'pnl_pct': ((current_val / invested_val - 1) * 100) if invested_val > 0 else 0,
        })

    pnl = total_current - total_invested
    category = 'profit' if pnl >= 0 else 'loss'

    return jsonify(
        denarius=current_user.roman_gold,
        denarius_usd_value=current_user.roman_gold * DENARIUS_USD,
        portfolio_usd=total_current,
        portfolio_denarius=total_current / DENARIUS_USD,
        invested_usd=total_invested,
        pnl_usd=pnl,
        pnl_pct=((total_current / total_invested - 1) * 100) if total_invested > 0 else 0,
        holdings=items,
        enoch=_enoch_line(category) if items else _enoch_line('enter'),
    )


# ── API: buy (market order) ──

@market_bp.route('/market/api/buy', methods=['POST'])
@login_required
def api_buy():
    data = request.get_json(force=True)
    coin_id = data.get('coin_id', '').strip()
    spend_denarius = float(data.get('denarius', 0))

    if spend_denarius <= 0:
        return jsonify(error='Amount must be positive.'), 400
    if spend_denarius > current_user.roman_gold:
        return jsonify(error='Insufficient funds.'), 400

    prices = _price_map({coin_id})
    price = prices.get(coin_id)
    if not price or price <= 0:
        return jsonify(error='Could not fetch price for this coin.'), 400

    crypto_amount = (spend_denarius * DENARIUS_USD) / price
    coin_name = _coin_name_from_cache(coin_id)
    coin_symbol = ''
    for c in _price_cache.get('data', []):
        if c['id'] == coin_id:
            coin_symbol = c.get('symbol', '')
            break

    current_user.roman_gold -= int(spend_denarius)
    _upsert_holding(current_user.id, coin_id, coin_symbol, coin_name,
                    crypto_amount, price)
    _record_tx(current_user.id, coin_id, coin_symbol, 'buy',
               crypto_amount, price, spend_denarius)
    _post_trade_update(current_user.username, 'buy', coin_symbol, spend_denarius)
    db.session.commit()

    return jsonify(
        ok=True,
        crypto_amount=crypto_amount,
        price=price,
        denarius_remaining=current_user.roman_gold,
        enoch=_enoch_line('buy'),
    )


# ── API: sell (market order) ──

@market_bp.route('/market/api/sell', methods=['POST'])
@login_required
def api_sell():
    data = request.get_json(force=True)
    coin_id = data.get('coin_id', '').strip()
    sell_amount = float(data.get('amount', 0))

    holding = MarketHolding.query.filter_by(
        user_id=current_user.id, coin_id=coin_id
    ).first()
    if not holding or holding.amount < sell_amount or sell_amount <= 0:
        return jsonify(error='Invalid sell amount.'), 400

    prices = _price_map({coin_id})
    price = prices.get(coin_id)
    if not price or price <= 0:
        return jsonify(error='Could not fetch price.'), 400

    denarius_back = (sell_amount * price) / DENARIUS_USD
    holding.amount -= sell_amount
    if holding.amount < 1e-12:
        db.session.delete(holding)

    sym = holding.coin_symbol
    current_user.roman_gold += int(denarius_back)
    _record_tx(current_user.id, coin_id, sym, 'sell',
               sell_amount, price, denarius_back)
    _post_trade_update(current_user.username, 'sell', sym, denarius_back)
    db.session.commit()

    return jsonify(
        ok=True,
        denarius_received=int(denarius_back),
        denarius_remaining=current_user.roman_gold,
        enoch=_enoch_line('sell'),
    )


# ── API: limit order ──

@market_bp.route('/market/api/order', methods=['POST'])
@login_required
def api_create_order():
    data = request.get_json(force=True)
    order_type = data.get('order_type', '').strip()
    coin_id = data.get('coin_id', '').strip()
    target_price = float(data.get('target_price', 0))

    if order_type not in ('buy', 'sell'):
        return jsonify(error='Invalid order type.'), 400
    if target_price <= 0:
        return jsonify(error='Target price must be positive.'), 400

    coin_symbol = ''
    for c in _price_cache.get('data', []):
        if c['id'] == coin_id:
            coin_symbol = c.get('symbol', '')
            break

    if order_type == 'buy':
        spend_denarius = float(data.get('denarius', 0))
        if spend_denarius <= 0 or spend_denarius > current_user.roman_gold:
            return jsonify(error='Invalid amount.'), 400
        crypto_amount = (spend_denarius * DENARIUS_USD) / target_price
        order = MarketOrder(
            user_id=current_user.id, coin_id=coin_id,
            coin_symbol=coin_symbol, order_type='buy',
            target_price=target_price, denarius_amount=spend_denarius,
            crypto_amount=crypto_amount,
        )
    else:
        sell_amount = float(data.get('amount', 0))
        holding = MarketHolding.query.filter_by(
            user_id=current_user.id, coin_id=coin_id
        ).first()
        if not holding or holding.amount < sell_amount or sell_amount <= 0:
            return jsonify(error='Invalid sell amount.'), 400
        denarius_amount = (sell_amount * target_price) / DENARIUS_USD
        order = MarketOrder(
            user_id=current_user.id, coin_id=coin_id,
            coin_symbol=coin_symbol, order_type='sell',
            target_price=target_price, denarius_amount=denarius_amount,
            crypto_amount=sell_amount,
        )

    db.session.add(order)
    db.session.commit()

    return jsonify(ok=True, order_id=order.id,
                   enoch=_enoch_line('limit_set'))


# ── API: list orders ──

@market_bp.route('/market/api/orders')
@login_required
def api_orders():
    orders = MarketOrder.query.filter_by(
        user_id=current_user.id
    ).order_by(MarketOrder.created_at.desc()).limit(50).all()
    items = []
    for o in orders:
        items.append({
            'id': o.id,
            'coin_id': o.coin_id,
            'symbol': o.coin_symbol,
            'type': o.order_type,
            'target_price': o.target_price,
            'denarius': o.denarius_amount,
            'crypto': o.crypto_amount,
            'status': o.status,
            'created': o.created_at.isoformat() if o.created_at else '',
            'filled': o.filled_at.isoformat() if o.filled_at else '',
        })
    return jsonify(orders=items)


# ── API: cancel order ──

@market_bp.route('/market/api/order/<int:order_id>', methods=['DELETE'])
@login_required
def api_cancel_order(order_id):
    order = MarketOrder.query.filter_by(
        id=order_id, user_id=current_user.id, status='pending'
    ).first()
    if not order:
        return jsonify(error='Order not found.'), 404
    order.status = 'cancelled'
    db.session.commit()
    return jsonify(ok=True)


# ── API: transaction history ──

@market_bp.route('/market/api/history')
@login_required
def api_history():
    txs = MarketTransaction.query.filter_by(
        user_id=current_user.id
    ).order_by(MarketTransaction.created_at.desc()).limit(50).all()
    items = []
    for t in txs:
        items.append({
            'coin_id': t.coin_id,
            'symbol': t.coin_symbol,
            'type': t.tx_type,
            'crypto': t.crypto_amount,
            'price': t.price_usd,
            'denarius': t.denarius_amount,
            'created': t.created_at.isoformat() if t.created_at else '',
        })
    return jsonify(transactions=items)


# ── API: Enoch quip ──

@market_bp.route('/market/api/enoch')
@login_required
def api_enoch_quip():
    cat = request.args.get('ctx', 'idle')
    return jsonify(line=_enoch_line(cat))


# ── API: quick summary for standings ticker ──

@market_bp.route('/market/api/summary')
@login_required
def api_summary():
    holdings = MarketHolding.query.filter_by(user_id=current_user.id).all()
    if not holdings:
        return jsonify(
            denarius=current_user.roman_gold,
            portfolio_usd=0,
            pnl_usd=0,
            pnl_pct=0,
        )
    prices = _price_map({h.coin_id for h in holdings})
    total_current = sum(h.amount * prices.get(h.coin_id, 0) for h in holdings)
    total_invested = sum(h.amount * h.avg_buy_price for h in holdings)
    pnl = total_current - total_invested
    return jsonify(
        denarius=current_user.roman_gold,
        portfolio_usd=total_current,
        pnl_usd=pnl,
        pnl_pct=((total_current / total_invested - 1) * 100) if total_invested > 0 else 0,
    )


# ── API: leaderboard for rotating ticker ──

@market_bp.route('/market/api/leaderboard')
@login_required
def api_leaderboard():
    """Return all human players' daily market P&L and total value."""
    users = User.query.filter_by(is_bot=False).all()
    all_holdings = MarketHolding.query.all()

    holdings_by_user = {}
    coin_ids = set()
    for h in all_holdings:
        holdings_by_user.setdefault(h.user_id, []).append(h)
        coin_ids.add(h.coin_id)

    prices = _price_map(coin_ids) if coin_ids else {}

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_txs = MarketTransaction.query.filter(
        MarketTransaction.created_at >= today_start
    ).all()
    daily_pnl_by_user = {}
    for tx in today_txs:
        amt = tx.denarius_amount if tx.tx_type == 'sell' else -tx.denarius_amount
        daily_pnl_by_user[tx.user_id] = daily_pnl_by_user.get(tx.user_id, 0) + amt

    players = []
    for u in users:
        user_holdings = holdings_by_user.get(u.id, [])
        portfolio_val = sum(h.amount * prices.get(h.coin_id, 0) for h in user_holdings)
        total_value = u.roman_gold + portfolio_val
        daily = daily_pnl_by_user.get(u.id, 0)
        players.append({
            'username': u.username,
            'total_value': round(total_value, 2),
            'daily_pnl': round(daily, 2),
        })
    players.sort(key=lambda p: p['total_value'], reverse=True)
    return jsonify(players=players)
