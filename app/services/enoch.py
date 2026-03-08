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
        post(f'{white.username} and {black.username} drew. '
             f'{white.username}: {change_w:+.0f} | {black.username}: {change_b:+.0f}')
        return

    result_desc = game.result_type or 'victory'
    post(f'{winner.username} defeats {loser.username} by {result_desc}. '
         f'{winner.username}: {w_change:+.0f} | {loser.username}: {l_change:+.0f}')


def announce_promotion(user, new_tier):
    post(f'{user.username} has ascended to {new_tier["name"]}.')


def announce_forfeit(winner, loser):
    post(f'{loser.username} has forfeited. {winner.username} is awarded the match.')


def announce_power_rotation(holder):
    post(f'The Power Position now rests with {holder.username}. Declare the week\'s decree.')


def announce_decree(holder, decree_text):
    post(f'{holder.username} has issued the Weekly Decree: "{decree_text}"')
