"""Courier Run — a chess-derived escort game engine.

Standard 8x8 board, full piece set. Each side picks a pawn as Courier.
Win by delivering your Courier to the enemy back rank or capturing the
enemy Courier. No check, checkmate, castling, en passant, or promotion.
Turn cap at 80 full turns with tiebreak rules.
"""

import chess

TURN_CAP = 80

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


def initial_fen():
    return chess.STARTING_FEN


def parse_square(sq_str):
    """Convert algebraic square name (e.g. 'e2') to chess.Square."""
    return chess.parse_square(sq_str)


def square_name(sq):
    return chess.square_name(sq)


def get_pawn_squares(fen, color):
    """Return list of square names for pawns of the given color."""
    board = chess.Board(fen)
    side = chess.WHITE if color == 'white' else chess.BLACK
    pawns = board.pieces(chess.PAWN, side)
    return [chess.square_name(sq) for sq in pawns]


def get_legal_moves(fen, courier_white_sq, courier_black_sq):
    """Return legal moves with courier-run restrictions applied.

    Removes: castling, en passant, promotion.
    Non-courier pawns cannot reach the promotion rank.
    The courier CAN reach the enemy back rank (that's the win condition).
    python-chess only generates promotion moves for pawns going to rank 1/8,
    so we synthesize non-promotion versions for the courier.
    """
    board = chess.Board(fen)

    moves = []
    courier_promo_targets = set()

    for m in board.legal_moves:
        if board.is_castling(m):
            continue
        if board.is_en_passant(m):
            continue

        if m.promotion:
            piece = board.piece_at(m.from_square)
            if not piece or piece.piece_type != chess.PAWN:
                continue
            is_courier = False
            if piece.color == chess.WHITE and courier_white_sq is not None:
                is_courier = (m.from_square == courier_white_sq)
            elif piece.color == chess.BLACK and courier_black_sq is not None:
                is_courier = (m.from_square == courier_black_sq)
            if is_courier:
                key = (m.from_square, m.to_square)
                if key not in courier_promo_targets:
                    courier_promo_targets.add(key)
                    moves.append(chess.Move(m.from_square, m.to_square))
            continue

        piece = board.piece_at(m.from_square)
        if piece and piece.piece_type == chess.PAWN:
            dest_rank = chess.square_rank(m.to_square)
            if piece.color == chess.WHITE and dest_rank == 7:
                continue
            elif piece.color == chess.BLACK and dest_rank == 0:
                continue
        moves.append(m)

    return moves


def get_legal_moves_dests(fen, courier_white_sq, courier_black_sq):
    """Return a dict of {from_square: [to_squares]} for Chessground."""
    moves = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    dests = {}
    for m in moves:
        orig = chess.square_name(m.from_square)
        dest = chess.square_name(m.to_square)
        dests.setdefault(orig, []).append(dest)
    return dests


def make_move(fen, uci_str, courier_white_sq, courier_black_sq):
    """Apply a move and return the new state.

    Returns dict with: fen, san, move_number, turn, captured_courier,
    courier_delivered, from_sq, to_sq, is_capture
    """
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci_str)

    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    if move not in legal:
        raise ValueError(f"Illegal move: {uci_str}")

    is_capture = board.piece_at(move.to_square) is not None
    captured_piece_sq = move.to_square

    # Check if this captures the enemy courier
    captured_courier = None
    if is_capture:
        if board.turn == chess.WHITE and courier_black_sq is not None:
            if captured_piece_sq == courier_black_sq:
                captured_courier = 'black'
        elif board.turn == chess.BLACK and courier_white_sq is not None:
            if captured_piece_sq == courier_white_sq:
                captured_courier = 'white'

    # Build SAN manually for courier back-rank moves (non-promotion to rank 1/8)
    piece = board.piece_at(move.from_square)
    is_courier_delivery = (
        piece and piece.piece_type == chess.PAWN
        and move.promotion is None
        and chess.square_rank(move.to_square) in (0, 7)
    )

    if is_courier_delivery:
        san = _courier_san(board, move, is_capture)
    else:
        san = board.san(move)

    side = board.turn

    # For courier delivery: python-chess needs a promotion flag to push
    # a pawn to the back rank. We push with queen promotion then
    # replace the piece with a pawn to keep the board consistent.
    if is_courier_delivery:
        promo_move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)
        board.push(promo_move)
        board.set_piece_at(move.to_square, chess.Piece(chess.PAWN, side))
    else:
        board.push(move)

    # Update courier positions after move
    new_courier_white = courier_white_sq
    new_courier_black = courier_black_sq

    if side == chess.WHITE and courier_white_sq == move.from_square:
        new_courier_white = move.to_square
    elif side == chess.BLACK and courier_black_sq == move.from_square:
        new_courier_black = move.to_square

    if captured_courier == 'white':
        new_courier_white = None
    elif captured_courier == 'black':
        new_courier_black = None

    # Check if courier delivered to enemy back rank
    courier_delivered = None
    if new_courier_white is not None and chess.square_rank(new_courier_white) == 7:
        courier_delivered = 'white'
    if new_courier_black is not None and chess.square_rank(new_courier_black) == 0:
        courier_delivered = 'black'

    return {
        'fen': board.fen(),
        'san': san,
        'move_number': board.fullmove_number,
        'turn': 'white' if board.turn == chess.WHITE else 'black',
        'from_sq': chess.square_name(move.from_square),
        'to_sq': chess.square_name(move.to_square),
        'is_capture': is_capture,
        'captured_courier': captured_courier,
        'courier_delivered': courier_delivered,
        'courier_white_sq': new_courier_white,
        'courier_black_sq': new_courier_black,
    }


def _courier_san(board, move, is_capture):
    """Generate SAN-like notation for a courier delivery move."""
    from_file = chess.FILE_NAMES[chess.square_file(move.from_square)]
    to_name = chess.square_name(move.to_square)
    if is_capture:
        return f"{from_file}x{to_name}"
    return to_name


def check_game_over(fen, courier_white_sq, courier_black_sq, turn_count):
    """Check all end conditions.

    Returns (is_over, winner, reason) or (False, None, None).
    winner: 'white', 'black', or 'draw'
    reason: 'courier_delivered', 'courier_captured', 'tiebreak_distance',
            'tiebreak_material', 'draw'
    """
    if courier_white_sq is not None and chess.square_rank(courier_white_sq) == 7:
        return True, 'white', 'courier_delivered'
    if courier_black_sq is not None and chess.square_rank(courier_black_sq) == 0:
        return True, 'black', 'courier_delivered'

    if courier_white_sq is None:
        return True, 'black', 'courier_captured'
    if courier_black_sq is None:
        return True, 'white', 'courier_captured'

    board = chess.Board(fen)
    piece_at_w = board.piece_at(courier_white_sq)
    if piece_at_w is None or piece_at_w.piece_type != chess.PAWN or piece_at_w.color != chess.WHITE:
        return True, 'black', 'courier_captured'
    piece_at_b = board.piece_at(courier_black_sq)
    if piece_at_b is None or piece_at_b.piece_type != chess.PAWN or piece_at_b.color != chess.BLACK:
        return True, 'white', 'courier_captured'

    if turn_count >= TURN_CAP:
        return _resolve_tiebreak(fen, courier_white_sq, courier_black_sq)

    legal = get_legal_moves(fen, courier_white_sq, courier_black_sq)
    if len(legal) == 0:
        return _resolve_tiebreak(fen, courier_white_sq, courier_black_sq)

    return False, None, None


def _resolve_tiebreak(fen, courier_white_sq, courier_black_sq):
    """Resolve tiebreak at turn cap or stalemate."""
    w_dist = 7 - chess.square_rank(courier_white_sq)  # distance to rank 8
    b_dist = chess.square_rank(courier_black_sq)       # distance to rank 1

    if w_dist < b_dist:
        return True, 'white', 'tiebreak_distance'
    elif b_dist < w_dist:
        return True, 'black', 'tiebreak_distance'

    w_mat = _material_score(fen, chess.WHITE)
    b_mat = _material_score(fen, chess.BLACK)
    if w_mat > b_mat:
        return True, 'white', 'tiebreak_material'
    elif b_mat > w_mat:
        return True, 'black', 'tiebreak_material'

    return True, 'draw', 'draw'


def _material_score(fen, color):
    board = chess.Board(fen)
    score = 0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and p.color == color:
            score += PIECE_VALUES.get(p.piece_type, 0)
    return score


def get_board_state(fen):
    """Return piece positions for rendering."""
    board = chess.Board(fen)
    pieces = {}
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p:
            pieces[chess.square_name(sq)] = p.symbol()
    return {
        'pieces': pieces,
        'turn': 'white' if board.turn == chess.WHITE else 'black',
        'fen': fen,
    }


def courier_distance_to_goal(sq, color):
    """How many ranks until this courier reaches the enemy back rank."""
    if color == 'white':
        return 7 - chess.square_rank(sq)
    else:
        return chess.square_rank(sq)
