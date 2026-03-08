"""Named opening / variation detection and storage.

Checkpoints where a novel sequence can be named:
  - Opening:   after 8 half-moves  (move 4 complete)
  - Variation:  after 16 half-moves (move 8 complete)

A sequence is "novel" if no other federation game has ever reached
that exact series of moves at the checkpoint length.
"""

from app.models import Game, Move, NamedSequence, db

CHECKPOINTS = [
    (8, 'Opening'),
    (16, 'Variation'),
]


def _build_move_key(moves_list):
    """Build a canonical space-separated SAN string from a list of Move objects or SAN strings."""
    if not moves_list:
        return ''
    if isinstance(moves_list[0], str):
        return ' '.join(moves_list)
    return ' '.join(m.move_san for m in moves_list)


def get_sequence_info(game_id):
    """Return the best matching named sequence for the current game state,
    plus whether the player can name a new one at the current checkpoint."""
    moves = Move.query.filter_by(game_id=game_id).order_by(Move.id).all()
    half = len(moves)
    if half == 0:
        return {'match': None, 'can_name': False}

    full_key = _build_move_key(moves)

    match = _find_longest_match(full_key, half)

    can_name_info = None
    for cp_half, cp_category in CHECKPOINTS:
        if half == cp_half:
            cp_key = _build_move_key(moves[:cp_half])
            existing = NamedSequence.query.filter_by(moves=cp_key).first()
            if not existing and _is_novel(cp_key, cp_half, game_id):
                can_name_info = {
                    'category': cp_category,
                    'half_moves': cp_half,
                    'moves_key': cp_key,
                }
            break

    result = {'match': None, 'can_name': can_name_info}
    if match:
        result['match'] = {
            'name': match.name,
            'category': match.category,
            'creator': match.creator.username,
        }
    return result


def _find_longest_match(full_key, half_moves):
    """Find the longest NamedSequence that is a prefix of the current game's moves."""
    candidates = NamedSequence.query.filter(
        NamedSequence.half_moves <= half_moves
    ).order_by(NamedSequence.half_moves.desc()).all()

    for seq in candidates:
        if full_key == seq.moves or full_key.startswith(seq.moves + ' '):
            return seq
    return None


def _is_novel(move_key, half_moves, current_game_id):
    """Check whether this exact move sequence has been played in any other game."""
    other_games = Game.query.filter(
        Game.id != current_game_id,
        Game.move_count >= half_moves,
    ).all()

    for g in other_games:
        g_moves = Move.query.filter_by(game_id=g.id).order_by(Move.id).limit(half_moves).all()
        if len(g_moves) >= half_moves:
            g_key = _build_move_key(g_moves)
            if g_key == move_key:
                return False
    return True


def name_sequence(creator_id, name, moves_key, half_moves, category):
    """Store a named sequence. Returns the new NamedSequence or None if it already exists."""
    existing = NamedSequence.query.filter_by(moves=moves_key).first()
    if existing:
        return None

    seq = NamedSequence(
        creator_id=creator_id,
        name=name.strip(),
        moves=moves_key,
        half_moves=half_moves,
        category=category,
    )
    db.session.add(seq)
    db.session.commit()

    try:
        from app.services.enoch import announce_new_sequence
        from app.models import User
        creator = db.session.get(User, creator_id)
        announce_new_sequence(creator, name.strip(), category.lower())
    except (ImportError, Exception):
        pass

    return seq
