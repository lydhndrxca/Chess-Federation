"""Enoch — the Federation's subterranean archivist.

Narrator, announcer, and ceremonial caretaker. Every system message
filters through his ink-stained perspective. Uses random selection
from expanded dialogue pools for variety."""

import random

from app.models import ChatMessage, db
from app.services.dialogue import (
    TITLES, GAME_START, EARLY_GAME, OPENING_DETECTED, UNKNOWN_OPENING,
    CAPTURE_PAWN, CAPTURE_KNIGHT, CAPTURE_BISHOP, CAPTURE_ROOK, CAPTURE_QUEEN,
    CHECK, CHECKMATE, BLUNDER, MATCH_RESULT_WIN, MATCH_RESULT_DRAW,
    PROMOTION, FORFEIT, DOUBLE_FORFEIT, POWER_ROTATION, DECREE,
    IDLE_COMMENTARY, TAUNTS, NEW_SEQUENCE, RATING_CHANGE, MODAL_DISMISS,
    CUSTOM_KNIGHT_RULE,
)

BOT_NAME = 'Enoch'

CAPTURE_POOLS = {
    'p': CAPTURE_PAWN,
    'n': CAPTURE_KNIGHT,
    'b': CAPTURE_BISHOP,
    'r': CAPTURE_ROOK,
    'q': CAPTURE_QUEEN,
}


def _pick(pool, **kwargs):
    line = random.choice(pool)
    if kwargs:
        try:
            line = line.format(**kwargs)
        except KeyError:
            pass
    return line


def get_title():
    return f'{BOT_NAME}, {random.choice(TITLES)}'


def post(message):
    msg = ChatMessage(
        content=message,
        is_bot=True,
        bot_name=BOT_NAME,
    )
    db.session.add(msg)


# ── Hall announcements (posted to Federation Hall chat) ──────

def announce_match_result(game, white, black, change_w, change_b):
    if game.result == '1-0':
        winner, loser = white, black
    elif game.result == '0-1':
        winner, loser = black, white
    else:
        line = _pick(MATCH_RESULT_DRAW,
                     player_a=white.username, player_b=black.username)
        post(line)
        post(f'{white.username} {change_w:+.0f} | {black.username} {change_b:+.0f}')
        return

    line = _pick(MATCH_RESULT_WIN,
                 winner=winner.username, loser=loser.username)
    post(line)

    w_line = _pick(RATING_CHANGE,
                   player=winner.username,
                   rating=round(winner.rating),
                   change=f'{change_w if winner == white else change_b:+.0f}')
    l_line = _pick(RATING_CHANGE,
                   player=loser.username,
                   rating=round(loser.rating),
                   change=f'{change_w if loser == white else change_b:+.0f}')
    post(f'{w_line} {l_line}')


def announce_promotion(user, new_tier):
    line = _pick(PROMOTION, player=user.username, title=new_tier['name'])
    post(line)


def announce_forfeit(winner, loser):
    line = _pick(FORFEIT, winner=winner.username, loser=loser.username)
    post(line)


def announce_double_forfeit(player_a, player_b):
    line = _pick(DOUBLE_FORFEIT,
                 player_a=player_a.username, player_b=player_b.username)
    post(line)


def announce_power_rotation(holder):
    line = _pick(POWER_ROTATION, player=holder.username)
    post(line)


def announce_decree(holder, decree_text):
    line = _pick(DECREE, player=holder.username, decree=decree_text)
    post(line)


def announce_new_sequence(creator, name, category):
    line = _pick(NEW_SEQUENCE,
                 player=creator.username, name=name, category=category)
    post(line)


# ── Game commentary (returned inline, not posted to Hall) ────

def comment_game_start():
    return _pick(GAME_START)


def comment_early_game():
    return _pick(EARLY_GAME)


def comment_opening_detected(opening_name):
    return _pick(OPENING_DETECTED, opening=opening_name)


def comment_unknown_opening():
    return _pick(UNKNOWN_OPENING)


def comment_capture(san):
    """Determine captured piece type from SAN and return a capture comment.
    SAN examples: exd5, Nxf3, Bxe7, Rxd1, Qxf7, dxc8=Q"""
    if 'x' not in san:
        return None

    piece_char = san[0] if san[0].isupper() and san[0] != 'O' else ''

    if piece_char == 'Q':
        return _pick(CAPTURE_QUEEN)
    if piece_char == 'R':
        return _pick(CAPTURE_ROOK)
    if piece_char == 'B':
        return _pick(CAPTURE_BISHOP)
    if piece_char == 'N':
        return _pick(CAPTURE_KNIGHT)
    return _pick(CAPTURE_PAWN)


def comment_capture_victim(captured_piece_type):
    """Return a capture comment based on the victim piece type (lowercase char)."""
    pool = CAPTURE_POOLS.get(captured_piece_type, CAPTURE_PAWN)
    return _pick(pool)


def comment_check():
    return _pick(CHECK)


def comment_checkmate():
    return _pick(CHECKMATE)


def comment_blunder():
    return _pick(BLUNDER)


def comment_idle():
    return _pick(IDLE_COMMENTARY)


def comment_taunt(player_name):
    return _pick(TAUNTS, player=player_name)


def _is_knight_move(san):
    """True if the SAN describes a knight move (e.g. Ne3, Nxd4, Nbc6)."""
    clean = san.replace('+', '').replace('#', '')
    return clean[:1] == 'N'


def get_move_commentary(san, move_number, is_game_over, result_type,
                        opening_name=None, custom_rule=False):
    """Generate Enoch's in-game commentary for a move.

    Returns a string or None. Prioritizes the most dramatic event.
    When custom_rule is True, knight moves get special rule commentary
    instead of normal knight/capture lines."""
    if is_game_over and result_type == 'checkmate':
        return comment_checkmate()

    if '+' in san:
        if custom_rule and _is_knight_move(san):
            return _pick(CUSTOM_KNIGHT_RULE)
        return comment_check()

    if custom_rule and _is_knight_move(san):
        return _pick(CUSTOM_KNIGHT_RULE)

    if 'x' in san:
        return comment_capture(san)

    if opening_name and move_number <= 10:
        return comment_opening_detected(opening_name)

    half_moves = move_number * 2
    if half_moves <= 10:
        return comment_early_game()

    return None


def get_modal_dismiss():
    return random.choice(MODAL_DISMISS)
