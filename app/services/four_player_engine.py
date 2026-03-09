"""Four-player chess engine for The Reckoning.

Board: 14×14 cross-shaped grid (3×3 corners removed → 160 valid squares).
Seats: south (rows 0-1), west (cols 0-1), north (rows 12-13), east (cols 12-13).
Rules: standard piece movement, no check/checkmate — king is capturable.
A player is eliminated when they have zero pieces remaining.
Last player standing wins.
"""

import json

BOARD_SIZE = 14
COLORS = ['south', 'west', 'north', 'east']
TURN_ORDER = {c: i for i, c in enumerate(COLORS)}

VALID_SQUARES = frozenset(
    (r, c) for r in range(14) for c in range(14)
    if not (r < 3 and c < 3) and not (r < 3 and c > 10)
    and not (r > 10 and c < 3) and not (r > 10 and c > 10)
)

PIECE_VALUES = {'K': 0, 'Q': 9, 'R': 5, 'B': 3, 'N': 3, 'P': 1}
STARTING_MATERIAL = 39  # 8P + 2N + 2B + 2R + 1Q

_BACK_RANK = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
_BACK_RANK_MIRROR = ['R', 'N', 'B', 'K', 'Q', 'B', 'N', 'R']

PAWN_FWD = {
    'south': (1, 0), 'west': (0, 1),
    'north': (-1, 0), 'east': (0, -1),
}
PAWN_HOME_CHECK = {
    'south': lambda r, c: r == 1,
    'west': lambda r, c: c == 1,
    'north': lambda r, c: r == 12,
    'east': lambda r, c: c == 12,
}
PAWN_PROMO_CHECK = {
    'south': lambda r, c: r == 13,
    'west': lambda r, c: c == 13,
    'north': lambda r, c: r == 0,
    'east': lambda r, c: c == 0,
}
PAWN_CAP_OFFSETS = {
    'south': [(1, -1), (1, 1)],
    'west': [(-1, 1), (1, 1)],
    'north': [(-1, -1), (-1, 1)],
    'east': [(-1, -1), (1, -1)],
}

KNIGHT_OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                  (1, -2), (1, 2), (2, -1), (2, 1)]
KING_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)]
RAY_DIRS = {
    'Q': KING_OFFSETS,
    'R': [(-1, 0), (0, -1), (0, 1), (1, 0)],
    'B': [(-1, -1), (-1, 1), (1, -1), (1, 1)],
}

UNICODE_PIECES = {
    'K': '\u265A', 'Q': '\u265B', 'R': '\u265C',
    'B': '\u265D', 'N': '\u265E', 'P': '\u265F',
}


def _key(r, c):
    return f'{r},{c}'


def _parse_key(k):
    parts = k.split(',')
    return int(parts[0]), int(parts[1])


# ── Board creation ──────────────────────────────────────────────

def initial_state():
    board = {}

    for i, pt in enumerate(_BACK_RANK):
        board[_key(0, 3 + i)] = 's' + pt
    for c in range(3, 11):
        board[_key(1, c)] = 'sP'

    for i, pt in enumerate(_BACK_RANK):
        board[_key(3 + i, 0)] = 'w' + pt
    for r in range(3, 11):
        board[_key(r, 1)] = 'wP'

    for i, pt in enumerate(_BACK_RANK_MIRROR):
        board[_key(13, 3 + i)] = 'n' + pt
    for c in range(3, 11):
        board[_key(12, c)] = 'nP'

    for i, pt in enumerate(_BACK_RANK_MIRROR):
        board[_key(3 + i, 13)] = 'e' + pt
    for r in range(3, 11):
        board[_key(r, 12)] = 'eP'

    return {
        'board': board,
        'turn': 'south',
        'eliminated': [],
        'move_count': 0,
    }


def serialize(state):
    return json.dumps(state, separators=(',', ':'))


def deserialize(raw):
    return json.loads(raw)


# ── Piece helpers ───────────────────────────────────────────────

def piece_color(code):
    return {'s': 'south', 'w': 'west', 'n': 'north', 'e': 'east'}[code[0]]


def piece_type(code):
    return code[1]


def color_prefix(color):
    return color[0]


# ── Legal move generation ───────────────────────────────────────

def _in_bounds(r, c):
    return (r, c) in VALID_SQUARES


def get_legal_moves(state, color=None):
    """Return list of moves: {'from': [r,c], 'to': [r,c], 'promo': str|None}"""
    color = color or state['turn']
    if color in state['eliminated']:
        return []
    board = state['board']
    prefix = color_prefix(color)
    moves = []

    for key, code in board.items():
        if code[0] != prefix:
            continue
        r, c = _parse_key(key)
        pt = code[1]

        if pt == 'P':
            _pawn_moves(board, color, prefix, r, c, moves)
        elif pt == 'N':
            _jump_moves(board, prefix, r, c, KNIGHT_OFFSETS, moves)
        elif pt == 'K':
            _jump_moves(board, prefix, r, c, KING_OFFSETS, moves)
        elif pt in ('Q', 'R', 'B'):
            _ray_moves(board, prefix, r, c, RAY_DIRS[pt], moves)

    return moves


def _pawn_moves(board, color, prefix, r, c, moves):
    dr, dc = PAWN_FWD[color]

    nr, nc = r + dr, c + dc
    if _in_bounds(nr, nc) and _key(nr, nc) not in board:
        if PAWN_PROMO_CHECK[color](nr, nc):
            for promo in ['Q', 'R', 'B', 'N']:
                moves.append({'from': [r, c], 'to': [nr, nc], 'promo': promo})
        else:
            moves.append({'from': [r, c], 'to': [nr, nc], 'promo': None})

        if PAWN_HOME_CHECK[color](r, c):
            nr2, nc2 = nr + dr, nc + dc
            if _in_bounds(nr2, nc2) and _key(nr2, nc2) not in board:
                moves.append({'from': [r, c], 'to': [nr2, nc2], 'promo': None})

    for odr, odc in PAWN_CAP_OFFSETS[color]:
        tr, tc = r + odr, c + odc
        tk = _key(tr, tc)
        if _in_bounds(tr, tc) and tk in board and board[tk][0] != prefix:
            if PAWN_PROMO_CHECK[color](tr, tc):
                for promo in ['Q', 'R', 'B', 'N']:
                    moves.append({'from': [r, c], 'to': [tr, tc], 'promo': promo})
            else:
                moves.append({'from': [r, c], 'to': [tr, tc], 'promo': None})


def _jump_moves(board, prefix, r, c, offsets, moves):
    for dr, dc in offsets:
        tr, tc = r + dr, c + dc
        tk = _key(tr, tc)
        if _in_bounds(tr, tc):
            if tk not in board or board[tk][0] != prefix:
                moves.append({'from': [r, c], 'to': [tr, tc], 'promo': None})


def _ray_moves(board, prefix, r, c, dirs, moves):
    for dr, dc in dirs:
        tr, tc = r + dr, c + dc
        while _in_bounds(tr, tc):
            tk = _key(tr, tc)
            if tk in board:
                if board[tk][0] != prefix:
                    moves.append({'from': [r, c], 'to': [tr, tc], 'promo': None})
                break
            moves.append({'from': [r, c], 'to': [tr, tc], 'promo': None})
            tr += dr
            tc += dc


# ── Move application ────────────────────────────────────────────

def make_move(state, fr, fc, tr, tc, promo=None):
    """Apply a move. Returns (new_state, captured_code_or_None).
    Raises ValueError on illegal move."""
    legal = get_legal_moves(state)
    matched = None
    for m in legal:
        if (m['from'] == [fr, fc] and m['to'] == [tr, tc]
                and m['promo'] == promo):
            matched = m
            break
    if not matched:
        if promo is None:
            for m in legal:
                if m['from'] == [fr, fc] and m['to'] == [tr, tc] and m['promo'] == 'Q':
                    matched = m
                    promo = 'Q'
                    break
        if not matched:
            raise ValueError('Illegal move')

    board = dict(state['board'])
    fk = _key(fr, fc)
    tk = _key(tr, tc)

    moving_piece = board.pop(fk)
    captured = board.get(tk)
    if captured:
        del board[tk]

    if promo:
        board[tk] = moving_piece[0] + promo
    else:
        board[tk] = moving_piece

    new_state = {
        'board': board,
        'turn': state['turn'],
        'eliminated': list(state['eliminated']),
        'move_count': state['move_count'] + 1,
    }

    newly_eliminated = _check_eliminations(new_state)
    for elim in newly_eliminated:
        new_state['eliminated'].append(elim)

    new_state['turn'] = _next_turn(new_state)
    return new_state, captured


def _check_eliminations(state):
    """Return list of colors that now have zero pieces (newly eliminated)."""
    board = state['board']
    alive = set()
    for code in board.values():
        alive.add(piece_color(code))

    newly = []
    for c in COLORS:
        if c not in state['eliminated'] and c not in alive:
            newly.append(c)
    return newly


def _next_turn(state):
    idx = TURN_ORDER[state['turn']]
    for i in range(1, 5):
        nxt = COLORS[(idx + i) % 4]
        if nxt not in state['eliminated']:
            return nxt
    return state['turn']


# ── Game-over / scoring ─────────────────────────────────────────

def is_game_over(state):
    alive = [c for c in COLORS if c not in state['eliminated']]
    return len(alive) <= 1


def get_winner(state):
    alive = [c for c in COLORS if c not in state['eliminated']]
    return alive[0] if len(alive) == 1 else None


def get_rankings(state):
    """Return colors ordered 1st→4th. Eliminated in reverse order, then alive by material."""
    alive = [c for c in COLORS if c not in state['eliminated']]
    alive.sort(key=lambda c: get_material(state, c), reverse=True)
    eliminated_rev = list(reversed(state['eliminated']))
    return alive + eliminated_rev


def get_material(state, color):
    prefix = color_prefix(color)
    total = 0
    for code in state['board'].values():
        if code[0] == prefix and code[1] != 'K':
            total += PIECE_VALUES.get(code[1], 0)
    return total


def get_piece_count(state, color):
    prefix = color_prefix(color)
    return sum(1 for code in state['board'].values() if code[0] == prefix)


# ── Scoring ─────────────────────────────────────────────────────

FINISH_POINTS = {0: 100, 1: 50, 2: 25, 3: 0}
TIMEOUT_POINTS_BY_RANK = {0: 15, 1: 10, 2: 5, 3: 0}


def compute_scores(state, timed_out=False):
    """Return dict mapping color → rating points earned."""
    rankings = get_rankings(state)
    table = TIMEOUT_POINTS_BY_RANK if timed_out else FINISH_POINTS
    return {color: table.get(i, 0) for i, color in enumerate(rankings)}


# ── Display helpers ─────────────────────────────────────────────

def board_to_grid(state):
    """Return a 14×14 list-of-lists for frontend rendering.
    Each cell is None (invalid), '' (empty), or a dict with piece info."""
    board = state['board']
    grid = []
    for r in range(BOARD_SIZE - 1, -1, -1):
        row = []
        for c in range(BOARD_SIZE):
            if (r, c) not in VALID_SQUARES:
                row.append(None)
            else:
                k = _key(r, c)
                if k in board:
                    code = board[k]
                    row.append({
                        'code': code,
                        'color': piece_color(code),
                        'type': piece_type(code),
                        'symbol': UNICODE_PIECES[piece_type(code)],
                        'r': r, 'c': c,
                    })
                else:
                    row.append({'empty': True, 'r': r, 'c': c})
        grid.append(row)
    return grid


def move_to_str(m):
    """Convert a move dict to string like '1,3-3,3' or '1,3-13,3=Q'."""
    s = f"{m['from'][0]},{m['from'][1]}-{m['to'][0]},{m['to'][1]}"
    if m.get('promo'):
        s += '=' + m['promo']
    return s


def parse_move_str(s):
    """Parse '1,3-3,3' or '1,3-13,3=Q' → (fr, fc, tr, tc, promo)."""
    promo = None
    if '=' in s:
        s, promo = s.rsplit('=', 1)
    parts = s.split('-')
    f = parts[0].split(',')
    t = parts[1].split(',')
    return int(f[0]), int(f[1]), int(t[0]), int(t[1]), promo
