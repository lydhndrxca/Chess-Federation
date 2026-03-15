"""Weekly Custom Rule Engine
═══════════════════════════════════════════════════════
To change or disable the weekly rule:
  - Set RULE_ACTIVE = False to revert to standard chess
  - Update RULE_TITLE / RULE_DESCRIPTION for announcements
  - Replace get_custom_legal_moves / make_custom_move / is_custom_game_over

Current rule: Knights are frozen — they cannot move at all.
Only applies to player-vs-player Federation matches, NOT Enoch practice.
═══════════════════════════════════════════════════════
"""

import chess

# ── Rule config ──────────────────────────────────────

RULE_ACTIVE = True

RULE_TITLE = "Lame Knees"

RULE_DESCRIPTION = (
    "Knights have lame knees — now the horses cannot move. "
    "They remain on the board but are completely frozen in place."
)

RULE_ENOCH_ANNOUNCEMENT = (
    "A new decree from the seat of power. The horses have gone lame. "
    "The knights cannot move. They sit on the board like statues — "
    "blocking squares, absorbing captures, contributing nothing. "
    "Play around them. Or through them. The decree is absolute."
)

RULE_REMINDER = (
    "Knights cannot move this week. They are frozen in place."
)

RULE_EXPLANATION = (
    "This week's decree freezes all knights. They cannot move at all — "
    "no L-shapes, no jumps, nothing. They still occupy their square "
    "and can be captured by the opponent, but they cannot be moved by "
    "their owner. Plan accordingly. This applies to all player-vs-player "
    "Federation matches. Enoch practice matches use standard rules."
)

_CHAT_ANNOUNCED = False


def ensure_chat_announcement():
    """Post Enoch's weekly rule announcement to chat (idempotent per server run)."""
    global _CHAT_ANNOUNCED
    if not RULE_ACTIVE or _CHAT_ANNOUNCED:
        return
    _CHAT_ANNOUNCED = True
    try:
        from app.models import ChatMessage, db
        already = ChatMessage.query.filter(
            ChatMessage.is_bot == True,
            ChatMessage.content.contains('horses have gone lame'),
        ).first()
        if already:
            return
        msg = ChatMessage(
            user_id=None,
            content=RULE_ENOCH_ANNOUNCEMENT,
            is_bot=True,
            bot_name='Enoch, Steward Beneath the Board',
        )
        db.session.add(msg)
        db.session.commit()
    except Exception:
        pass


# ── Frozen knights: simply remove all knight moves ──


def _king_in_danger(board, king_color):
    """True if king is in check. Knights are frozen so they cannot attack."""
    king_sq = board.king(king_color)
    if king_sq is None:
        return True
    opponent = not king_color
    non_knight_attackers = board.attackers(opponent, king_sq) & ~board.knights
    return bool(non_knight_attackers)


def _king_safe_after(board, move):
    """True if after `move`, the mover's king is safe (frozen knight rules)."""
    board.push(move)
    mover = not board.turn
    safe = not _king_in_danger(board, mover)
    board.pop()
    return safe


def _generate_custom_legal_moves(board):
    """Yield all legal moves — knights excluded entirely."""
    for move in board.pseudo_legal_moves:
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.KNIGHT:
            continue
        if _king_safe_after(board, move):
            yield move


# ── Public API (mirrors ChessEngine interface) ──────

def get_custom_legal_moves(fen):
    """Return list of legal-move dicts with frozen knight rules."""
    if not RULE_ACTIVE:
        from app.services.chess_engine import ChessEngine
        return ChessEngine.get_legal_moves(fen)

    board = chess.Board(fen)
    moves = []
    for move in _generate_custom_legal_moves(board):
        san = board.san(move)
        moves.append({
            'uci': move.uci(),
            'san': san,
            'from': chess.square_name(move.from_square),
            'to': chess.square_name(move.to_square),
            'promotion': move.promotion is not None,
        })
    return moves


def make_custom_move(fen, uci_move):
    """Validate and apply a move under frozen knight rules.
    Returns same dict shape as ChessEngine.make_move."""
    if not RULE_ACTIVE:
        from app.services.chess_engine import ChessEngine
        return ChessEngine.make_move(fen, uci_move)

    board = chess.Board(fen)
    move = chess.Move.from_uci(uci_move)

    legal = list(_generate_custom_legal_moves(board))
    if move not in legal:
        raise ValueError(f'Illegal move: {uci_move}')

    san = board.san(move)
    board.push(move)

    if board.turn == chess.WHITE:
        move_number = board.fullmove_number - 1
    else:
        move_number = board.fullmove_number

    return {
        'fen': board.fen(),
        'san': san,
        'move_number': move_number,
        'turn': 'white' if board.turn == chess.WHITE else 'black',
    }


def is_custom_game_over(fen):
    """Check game-over under frozen knight rules.
    Returns (is_over, result_type) same as ChessEngine.is_game_over."""
    if not RULE_ACTIVE:
        from app.services.chess_engine import ChessEngine
        return ChessEngine.is_game_over(fen)

    board = chess.Board(fen)

    if board.is_insufficient_material():
        return True, 'draw'
    if board.can_claim_draw():
        return True, 'draw'

    has_legal = False
    for _ in _generate_custom_legal_moves(board):
        has_legal = True
        break

    if not has_legal:
        if _king_in_danger(board, board.turn):
            return True, 'checkmate'
        return True, 'stalemate'

    return False, None
