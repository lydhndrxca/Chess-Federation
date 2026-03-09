"""Routes for The Crypt — 10-wave Millionaire-style solo chess mode."""

import json
from datetime import datetime, timezone

import chess
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user

from app.models import db, CryptGame, User
from app.services.crypt_logic import (
    SHOP_PRICES, CAPTURE_GOLD, CAPTURE_SCORE,
    wave_bonus_gold, wave_bonus_score,
    generate_wave, build_fen, get_surviving_pieces,
    check_wave_complete, get_legal_moves_list,
    pick_horde_move,
    MAX_WAVES, ENTRY_COST, DAILY_LIMIT, LADDER,
    MILESTONES, BOSS_REWARD,
    get_safety_net, get_cashout_value, is_milestone_wave,
    runs_today, can_enter,
)
from app.services.crypt_dialogue import (
    get_wave_start_line, get_capture_line, get_wave_complete_line,
    get_game_over_line, get_shopping_line, get_buy_line,
    get_battle_line, get_high_score_line,
    get_milestone_line, get_cashout_line,
    get_boss_battle_line, get_boss_victory_line, get_boss_defeat_line,
)

crypt_bp = Blueprint('crypt', __name__)


def _best_wave(user_id):
    row = (CryptGame.query
           .filter_by(user_id=user_id)
           .filter(CryptGame.completed_at.isnot(None))
           .order_by(CryptGame.wave.desc())
           .first())
    return row.wave if row else 0


def _leaderboard(limit=10):
    rows = (CryptGame.query
            .filter(CryptGame.completed_at.isnot(None))
            .order_by(CryptGame.wave.desc(), CryptGame.score.desc())
            .limit(limit).all())
    return rows


# ── Pages ────────────────────────────────────────────────────────

@crypt_bp.route('/crypt')
@login_required
def crypt_home():
    active = CryptGame.query.filter_by(
        user_id=current_user.id, completed_at=None).first()
    if active:
        return redirect(url_for('crypt.crypt_game', game_id=active.id))

    today_runs = runs_today(current_user.id)
    return render_template(
        'crypt.html', game=None,
        leaderboard=_leaderboard(),
        best_wave=_best_wave(current_user.id),
        shop_prices=SHOP_PRICES,
        entry_cost=ENTRY_COST,
        daily_limit=DAILY_LIMIT,
        daily_runs=today_runs,
        can_enter=today_runs < DAILY_LIMIT and current_user.rating >= ENTRY_COST,
        ladder=LADDER,
        max_waves=MAX_WAVES,
        boss_reward=BOSS_REWARD,
    )


@crypt_bp.route('/crypt/<int:game_id>')
@login_required
def crypt_game(game_id):
    game = CryptGame.query.get_or_404(game_id)
    if game.user_id != current_user.id:
        return redirect(url_for('crypt.crypt_home'))

    legal_moves = []
    if game.phase == 'battle' and game.fen_current:
        board = chess.Board(game.fen_current)
        if board.turn == chess.WHITE:
            legal_moves = get_legal_moves_list(board)

    highest_cleared = game.wave - 1
    return render_template(
        'crypt.html', game=game,
        leaderboard=_leaderboard(),
        best_wave=_best_wave(current_user.id),
        shop_prices=SHOP_PRICES,
        legal_moves=legal_moves,
        ladder=LADDER,
        max_waves=MAX_WAVES,
        boss_reward=BOSS_REWARD,
        entry_cost=ENTRY_COST,
        daily_limit=DAILY_LIMIT,
        daily_runs=runs_today(current_user.id),
        can_enter=False,
        safety_net=get_safety_net(highest_cleared),
    )


# ── API ──────────────────────────────────────────────────────────

@crypt_bp.route('/crypt/new', methods=['POST'])
@login_required
def crypt_new():
    active = CryptGame.query.filter_by(
        user_id=current_user.id, completed_at=None).first()
    if active:
        return jsonify(ok=False, error='You already have an active run.'), 400

    if not can_enter(current_user.id):
        return jsonify(ok=False, error='Daily limit reached (3 per day).'), 400

    if current_user.rating < ENTRY_COST:
        return jsonify(ok=False, error=f'Not enough rating ({ENTRY_COST} required).'), 400

    current_user.rating -= ENTRY_COST
    game = CryptGame(user_id=current_user.id, rating_entry=ENTRY_COST)
    db.session.add(game)
    db.session.commit()
    return jsonify(ok=True, game_id=game.id)


@crypt_bp.route('/crypt/<int:game_id>/deploy', methods=['POST'])
@login_required
def crypt_deploy(game_id):
    game = CryptGame.query.get_or_404(game_id)
    if game.user_id != current_user.id or game.phase != 'placement':
        return jsonify(ok=False, error='Invalid state.'), 400

    data = request.get_json(force=True)
    placement = data.get('placement', {})

    inventory = json.loads(game.inventory)
    placed = list(placement.values())

    inv_copy = list(inventory)
    for p in placed:
        if p in inv_copy:
            inv_copy.remove(p)
        else:
            return jsonify(ok=False, error=f'Piece {p} not in inventory.'), 400

    if 'K' not in placed:
        return jsonify(ok=False, error='You must place your King.'), 400

    for sq in placement:
        rank = int(sq[1])
        if rank > 2:
            return jsonify(ok=False, error='Pieces must be on ranks 1–2.'), 400

    enemy = generate_wave(game.wave)
    fen = build_fen(placement, enemy)
    game.fen_current = fen
    game.phase = 'battle'
    db.session.commit()

    board = chess.Board(fen)

    return jsonify(
        ok=True,
        fen=fen,
        enemy_pieces=[{'piece': p, 'square': s} for p, s in enemy],
        legal_moves=get_legal_moves_list(board),
        wave=game.wave,
        is_boss=(game.wave == MAX_WAVES),
        enoch=get_wave_start_line(game.wave),
    )


@crypt_bp.route('/crypt/<int:game_id>/move', methods=['POST'])
@login_required
def crypt_move(game_id):
    game = CryptGame.query.get_or_404(game_id)
    if game.user_id != current_user.id or game.phase != 'battle':
        return jsonify(ok=False, error='Invalid state.'), 400

    data = request.get_json(force=True)
    uci_str = data.get('uci', '')

    board = chess.Board(game.fen_current)
    if board.turn != chess.WHITE:
        return jsonify(ok=False, error='Not your turn.'), 400

    try:
        move = chess.Move.from_uci(uci_str)
    except Exception:
        return jsonify(ok=False, error='Invalid move format.'), 400

    if move not in board.legal_moves:
        return jsonify(ok=False, error='Illegal move.'), 400

    captured = board.piece_at(move.to_square)
    player_san = board.san(move)
    board.push(move)

    cap_gold = 0
    cap_score = 0
    enoch_line = None
    if captured and captured.color == chess.BLACK:
        cap_gold = CAPTURE_GOLD.get(captured.piece_type, 0)
        cap_score = CAPTURE_SCORE.get(captured.piece_type, 0)
        game.gold += cap_gold
        game.gold_earned += cap_gold
        game.score += cap_score
        game.kills += 1
        enoch_line = get_capture_line(player_captured=True)

    game.fen_current = board.fen()

    wc = check_wave_complete(board) or (board.is_checkmate() and board.turn == chess.BLACK)
    if wc:
        return _finish_wave(game, board, player_san, cap_gold, cap_score)

    if board.turn == chess.BLACK and board.is_stalemate():
        return _finish_wave(game, board, player_san, cap_gold, cap_score)

    ai_move = pick_horde_move(board.fen(), game.wave)
    if ai_move is None:
        return _finish_wave(game, board, player_san, cap_gold, cap_score)

    ai_captured = board.piece_at(ai_move.to_square)
    ai_san = board.san(ai_move)
    board.push(ai_move)
    game.fen_current = board.fen()

    if ai_captured and ai_captured.color == chess.WHITE:
        enoch_line = get_capture_line(player_captured=False)
    elif not enoch_line:
        enoch_line = get_boss_battle_line() if game.wave >= MAX_WAVES else get_battle_line()

    if board.is_checkmate():
        return _finish_game(game, board, player_san, ai_san, ai_move,
                            cap_gold, cap_score)

    if board.is_stalemate():
        return _finish_game(game, board, player_san, ai_san, ai_move,
                            cap_gold, cap_score)

    if check_wave_complete(board):
        return _finish_wave(game, board, player_san, cap_gold, cap_score,
                            ai_san=ai_san, ai_uci=ai_move.uci())

    db.session.commit()

    return jsonify(
        ok=True,
        fen=board.fen(),
        player_san=player_san,
        ai_move={'san': ai_san, 'uci': ai_move.uci()},
        legal_moves=get_legal_moves_list(board),
        game_over=False,
        wave_complete=False,
        capture_gold=cap_gold,
        capture_score=cap_score,
        gold=game.gold,
        score=game.score,
        kills=game.kills,
        wave=game.wave,
        enoch=enoch_line,
    )


def _finish_wave(game, board, player_san, cap_gold, cap_score,
                 ai_san=None, ai_uci=None):
    bg = wave_bonus_gold(game.wave)
    bs = wave_bonus_score(game.wave)
    game.gold += bg
    game.gold_earned += bg
    game.score += bs

    wave_just_cleared = game.wave
    surviving = get_surviving_pieces(board)
    game.inventory = json.dumps(surviving)

    # Check if this was the final wave (beat the boss!)
    if wave_just_cleared >= MAX_WAVES:
        return _finish_game_victory(game, board, player_san, ai_san, ai_uci,
                                    cap_gold, cap_score)

    game.wave += 1
    game.phase = 'placement'
    game.fen_current = None
    db.session.commit()

    is_milestone = is_milestone_wave(wave_just_cleared)
    cashout_val = get_cashout_value(wave_just_cleared)
    safety = get_safety_net(wave_just_cleared)

    enoch_line = get_wave_complete_line()
    milestone_enoch = get_milestone_line(wave_just_cleared) if is_milestone else None

    resp = dict(
        ok=True,
        fen=board.fen(),
        player_san=player_san,
        wave_complete=True,
        game_over=False,
        bonus_gold=bg,
        bonus_score=bs,
        capture_gold=cap_gold,
        capture_score=cap_score,
        next_wave=game.wave,
        inventory=surviving,
        gold=game.gold,
        score=game.score,
        kills=game.kills,
        wave_cleared=wave_just_cleared,
        is_milestone=is_milestone,
        cashout_value=cashout_val,
        safety_net=safety,
        max_waves=MAX_WAVES,
        enoch=enoch_line,
        enoch_milestone=milestone_enoch,
    )
    if ai_san:
        resp['ai_move'] = {'san': ai_san, 'uci': ai_uci}
    return jsonify(resp)


def _finish_game_victory(game, board, player_san, ai_san, ai_uci,
                         cap_gold, cap_score):
    """Player cleared all 10 waves including the boss."""
    game.phase = 'gameover'
    game.completed_at = datetime.now(timezone.utc)
    game.fen_current = board.fen()
    game.rating_result = BOSS_REWARD
    game.cashed_out = False

    user = User.query.get(game.user_id)
    user.rating += ENTRY_COST + BOSS_REWARD

    prev_best = _best_wave(game.user_id)
    is_new_best = game.wave > prev_best

    db.session.commit()

    return jsonify(
        ok=True,
        fen=board.fen(),
        player_san=player_san,
        ai_move={'san': ai_san, 'uci': ai_uci} if ai_san else None,
        game_over=True,
        victory=True,
        wave_complete=True,
        final_wave=game.wave,
        final_score=game.score,
        final_kills=game.kills,
        gold=game.gold,
        gold_earned=game.gold_earned,
        gold_spent=game.gold_spent,
        capture_gold=cap_gold,
        capture_score=cap_score,
        rating_change=BOSS_REWARD,
        is_new_best=is_new_best,
        enoch=get_boss_victory_line(),
        enoch_highscore=get_high_score_line() if is_new_best else None,
    )


def _finish_game(game, board, player_san, ai_san, ai_move,
                 cap_gold, cap_score):
    """Player lost (checkmate/stalemate)."""
    game.phase = 'gameover'
    game.completed_at = datetime.now(timezone.utc)
    game.fen_current = board.fen()

    highest_cleared = game.wave - 1
    net = get_safety_net(highest_cleared)
    game.rating_result = net

    user = User.query.get(game.user_id)
    refund = ENTRY_COST + net
    if refund > 0:
        user.rating += refund

    prev_best = _best_wave(game.user_id)
    is_new_best = game.wave > prev_best

    enoch_line = get_boss_defeat_line() if game.wave >= MAX_WAVES else get_game_over_line()

    db.session.commit()

    return jsonify(
        ok=True,
        fen=board.fen(),
        player_san=player_san,
        ai_move={'san': ai_san, 'uci': ai_move.uci()},
        game_over=True,
        victory=False,
        wave_complete=False,
        final_wave=game.wave,
        final_score=game.score,
        final_kills=game.kills,
        gold=game.gold,
        gold_earned=game.gold_earned,
        gold_spent=game.gold_spent,
        capture_gold=cap_gold,
        capture_score=cap_score,
        rating_change=net,
        safety_net_used=net,
        is_new_best=is_new_best,
        enoch=enoch_line,
        enoch_highscore=get_high_score_line() if is_new_best else None,
    )


@crypt_bp.route('/crypt/<int:game_id>/cashout', methods=['POST'])
@login_required
def crypt_cashout(game_id):
    """Player cashes out at a milestone wave."""
    game = CryptGame.query.get_or_404(game_id)
    if game.user_id != current_user.id or game.phase != 'placement':
        return jsonify(ok=False, error='Invalid state.'), 400

    highest_cleared = game.wave - 1
    cashout_val = get_cashout_value(highest_cleared)
    if cashout_val is None:
        return jsonify(ok=False, error='Cannot cash out at this wave.'), 400

    game.phase = 'gameover'
    game.completed_at = datetime.now(timezone.utc)
    game.rating_result = cashout_val
    game.cashed_out = True

    user = User.query.get(game.user_id)
    user.rating += ENTRY_COST + cashout_val

    db.session.commit()

    return jsonify(
        ok=True,
        rating_change=cashout_val,
        total_returned=ENTRY_COST + cashout_val,
        final_wave=highest_cleared,
        final_score=game.score,
        final_kills=game.kills,
        enoch=get_cashout_line(),
    )


@crypt_bp.route('/crypt/<int:game_id>/buy', methods=['POST'])
@login_required
def crypt_buy(game_id):
    game = CryptGame.query.get_or_404(game_id)
    if game.user_id != current_user.id or game.phase != 'placement':
        return jsonify(ok=False, error='Invalid state.'), 400

    data = request.get_json(force=True)
    piece = data.get('piece', '')
    if piece not in SHOP_PRICES:
        return jsonify(ok=False, error='Invalid piece.'), 400

    price = SHOP_PRICES[piece]
    if game.gold < price:
        return jsonify(ok=False, error='Not enough gold.'), 400

    game.gold -= price
    game.gold_spent += price
    inventory = json.loads(game.inventory)
    inventory.append(piece)
    game.inventory = json.dumps(inventory)
    db.session.commit()

    return jsonify(
        ok=True,
        gold=game.gold,
        inventory=inventory,
        enoch=get_buy_line(piece),
    )


@crypt_bp.route('/crypt/<int:game_id>/state')
@login_required
def crypt_state(game_id):
    game = CryptGame.query.get_or_404(game_id)
    if game.user_id != current_user.id:
        return jsonify(ok=False), 403

    highest_cleared = game.wave - 1
    resp = {
        'phase': game.phase,
        'wave': game.wave,
        'score': game.score,
        'gold': game.gold,
        'kills': game.kills,
        'inventory': json.loads(game.inventory) if game.inventory else [],
        'safety_net': get_safety_net(highest_cleared),
        'max_waves': MAX_WAVES,
    }

    if game.phase == 'battle' and game.fen_current:
        board = chess.Board(game.fen_current)
        resp['fen'] = game.fen_current
        if board.turn == chess.WHITE:
            resp['legal_moves'] = get_legal_moves_list(board)
        else:
            resp['legal_moves'] = []

    return jsonify(resp)


@crypt_bp.route('/crypt/<int:game_id>/abandon', methods=['POST'])
@login_required
def crypt_abandon(game_id):
    game = CryptGame.query.get_or_404(game_id)
    if game.user_id != current_user.id:
        return jsonify(ok=False), 403
    if game.completed_at:
        return jsonify(ok=False, error='Already finished.'), 400

    highest_cleared = game.wave - 1
    net = get_safety_net(highest_cleared)
    game.rating_result = net
    game.phase = 'gameover'
    game.completed_at = datetime.now(timezone.utc)

    user = User.query.get(game.user_id)
    refund = ENTRY_COST + net
    if refund > 0:
        user.rating += refund

    db.session.commit()
    return jsonify(ok=True, rating_change=net)
