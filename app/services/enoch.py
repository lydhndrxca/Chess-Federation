"""Enoch — the Federation's basement-dwelling orchestrator.

Posts automated announcements to Federation Hall."""

from app.models import ChatMessage, db

BOT_NAME = 'Enoch'


def post(message):
    msg = ChatMessage(
        content=message,
        is_bot=True,
        bot_name=BOT_NAME,
    )
    db.session.add(msg)


def announce_match_result(game, white, black, change_w, change_b):
    if game.result == '1-0':
        winner, loser = white, black
        w_change, l_change = change_w, change_b
    elif game.result == '0-1':
        winner, loser = black, white
        w_change, l_change = change_b, change_w
    else:
        post(f'The match between {white.username} and {black.username} has concluded in a draw. '
             f'Adjustments recorded: {white.username} {change_w:+.0f} | {black.username} {change_b:+.0f}.')
        return

    result_desc = game.result_type or 'decisive play'
    post(f'{winner.username} prevails over {loser.username} by {result_desc}. '
         f'The record is amended: {winner.username} {w_change:+.0f} | {loser.username} {l_change:+.0f}.')


def announce_promotion(user, new_tier):
    post(f'Let it be known — {user.username} has been elevated to the rank of '
         f'{new_tier["name"]}. The Federation acknowledges this advancement.')


def announce_forfeit(winner, loser):
    post(f'{loser.username} has failed to meet the obligation of play. '
         f'The match is forfeit. {winner.username} receives the standing victory.')


def announce_power_rotation(holder):
    post(f'The seat of power passes to {holder.username}. '
         f'A decree is expected before the appointed hour.')


def announce_decree(holder, decree_text):
    post(f'{holder.username} has issued this week\'s decree: "{decree_text}"')
