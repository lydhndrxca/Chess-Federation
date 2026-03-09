"""Weekly Custom Rule Engine
═══════════════════════════════════════════════════════
To change or disable the weekly rule:
  - Set RULE_ACTIVE = False to revert to standard chess
  - Update RULE_TITLE / RULE_DESCRIPTION for announcements
  - Replace get_custom_legal_moves / make_custom_move / is_custom_game_over

Current rule: Knights move 3+2 (extended L-shape) instead of standard 2+1.
Only applies to player-vs-player Federation matches, NOT Enoch practice.
═══════════════════════════════════════════════════════
"""

import chess

# ── Rule config ──────────────────────────────────────

RULE_ACTIVE = True

RULE_TITLE = "The Extended Knight"

RULE_DESCRIPTION = (
    "This week, knights ride with longer strides — three squares forward "
    "and two to the side, in any direction, replacing the standard 2+1."
)

RULE_ENOCH_ANNOUNCEMENT = (
    "A decree echoes through the vaults. The knights have been fed. They now "
    "leap three squares forward and two to the side — any direction they "
    "choose. The old two-and-one is suspended. I have amended the ledger."
)

RULE_REMINDER = (
    "Knights move 3 forward + 2 to the side (any direction) this week."
)

RULE_EXPLANATION = (
    "This week's custom rule changes how knights move. Instead of the "
    "standard L-shape (2 squares in one direction, 1 to the side), "
    "knights now move 3 squares in any cardinal direction and 2 to the "
    "side. Same L-shape concept, just one extra square on each leg. "
    "This applies to all player-vs-player Federation matches. Enoch "
    "practice matches use standard rules."
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
            ChatMessage.content.contains('knights have been fed'),
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


# ── Custom knight offsets (3+2 replaces standard 2+1) ──

CUSTOM_KNIGHT_OFFSETS = [
    (3, 2), (3, -2), (-3, 2), (-3, -2),
    (2, 3), (2, -3), (-2, 3), (-2, -3),
]


def _custom_knight_targets(square):
    """Squares a custom knight on `square` can reach."""
    f = chess.square_file(square)
    r = chess.square_rank(square)
    targets = []
    for df, dr in CUSTOM_KNIGHT_OFFSETS:
        nf, nr = f + df, r + dr
        if 0 <= nf <= 7 and 0 <= nr <= 7:
            targets.append(chess.square(nf, nr))
    return targets


def _attacked_by_custom_knight(board, color, square):
    """True if any `color` knight attacks `square` via 3+2."""
    for nsq in board.pieces(chess.KNIGHT, color):
        if square in _custom_knight_targets(nsq):
            return True
    return False


def _king_in_danger(board, king_color):
    """True if `king_color`'s king is in check under custom knight rules."""
    king_sq = board.king(king_color)
    if king_sq is None:
        return True
    opponent = not king_color
    non_knight_attackers = board.attackers(opponent, king_sq) & ~board.knights
    if non_knight_attackers:
        return True
    return _attacked_by_custom_knight(board, opponent, king_sq)


def _king_safe_after(board, move):
    """True if after `move`, the mover's king is safe (custom rules)."""
    board.push(move)
    mover = not board.turn
    safe = not _king_in_danger(board, mover)
    board.pop()
    return safe


def _san_for_custom_move(board, move):
    """Generate SAN-style notation for a custom knight move."""
    piece = board.piece_at(move.from_square)
    if piece is None:
        return move.uci()
    target_piece = board.piece_at(move.to_square)
    is_capture = target_piece is not None

    san = 'N'
    same_type = [
        sq for sq in board.pieces(chess.KNIGHT, board.turn)
        if sq != move.from_square
        and move.to_square in _custom_knight_targets(sq)
    ]
    if same_type:
        from_f = chess.square_file(move.from_square)
        from_r = chess.square_rank(move.from_square)
        other_files = [chess.square_file(s) for s in same_type]
        if from_f not in other_files:
            san += chess.FILE_NAMES[from_f]
        else:
            san += str(from_r + 1)

    if is_capture:
        san += 'x'
    san += chess.square_name(move.to_square)

    board.push(move)
    opponent = board.turn
    opp_king = board.king(opponent)
    if opp_king is not None and _king_in_danger(board, opponent):
        has_escape = False
        for m in _generate_custom_legal_moves(board):
            has_escape = True
            break
        san += '#' if not has_escape else '+'
    board.pop()
    return san


def _generate_custom_legal_moves(board):
    """Yield all legal moves under custom knight rules."""
    for move in board.pseudo_legal_moves:
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.KNIGHT:
            continue
        if _king_safe_after(board, move):
            yield move

    for sq in board.pieces(chess.KNIGHT, board.turn):
        for target in _custom_knight_targets(sq):
            tp = board.piece_at(target)
            if tp and tp.color == board.turn:
                continue
            move = chess.Move(sq, target)
            if _king_safe_after(board, move):
                yield move


# ── Public API (mirrors ChessEngine interface) ──────

def get_custom_legal_moves(fen):
    """Return list of legal-move dicts with custom knight rules."""
    if not RULE_ACTIVE:
        from app.services.chess_engine import ChessEngine
        return ChessEngine.get_legal_moves(fen)

    board = chess.Board(fen)
    moves = []
    for move in _generate_custom_legal_moves(board):
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.KNIGHT:
            san = _san_for_custom_move(board, move)
        else:
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
    """Validate and apply a move under custom knight rules.
    Returns same dict shape as ChessEngine.make_move."""
    if not RULE_ACTIVE:
        from app.services.chess_engine import ChessEngine
        return ChessEngine.make_move(fen, uci_move)

    board = chess.Board(fen)
    move = chess.Move.from_uci(uci_move)

    legal = list(_generate_custom_legal_moves(board))
    if move not in legal:
        raise ValueError(f'Illegal move: {uci_move}')

    piece = board.piece_at(move.from_square)
    if piece and piece.piece_type == chess.KNIGHT:
        san = _san_for_custom_move(board, move)
    else:
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
    """Check game-over under custom knight rules.
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
