"""Enoch Chat Engine — interactive keyword-and-context matching system.

Enoch listens to Federation Hall messages and responds when triggered.
Rate-limited to feel natural, not scripted."""

import random
import re
import time
from datetime import datetime, timezone

from app.models import ChatMessage, db
from app.services.dialogue import (
    CHAT_GREETING, CHAT_SMALLTALK, CHAT_GAME_COMMENTARY, CHAT_WHO_WINNING,
    CHAT_STRATEGY, CHAT_BRAGGING, CHAT_COMPLAINING, CHAT_INSULTS,
    CHAT_ORCHESTRA, CHAT_PHILOSOPHY, CHAT_IDLE, CHAT_HUMOR,
    CHAT_FEDERATION_LORE,
    CMD_STANDINGS, CMD_RATING, CMD_DECREE, CMD_HELP,
    CHAT_LATE_NIGHT, CHAT_QUIRKS, CHAT_THESES, CHAT_CASUAL_ANNOUNCE,
    CHAT_CRYPT_REVENGE_ANNOUNCE, CHAT_ZOMBIE_ANNOUNCE,
    CHAT_RECKONING_AUTOMOVE_ANNOUNCE, CHAT_MARKET_ANNOUNCE,
)

BOT_NAME = 'Enoch'

_last_reply_ts = 0.0
_last_idle_ts = 0.0
_last_quirk_ts = 0.0

REPLY_COOLDOWN = 600
IDLE_MIN_SILENCE = 86400
IDLE_COOLDOWN = 86400
QUIRK_COOLDOWN = 14400  # 4 hours between quirks

_TRIGGER_PATTERNS = [
    (re.compile(r'@\s*enoch\s+standings?\b', re.I), 'cmd_standings'),
    (re.compile(r'@\s*enoch\s+rating\b', re.I), 'cmd_rating'),
    (re.compile(r'@\s*enoch\s+decree\b', re.I), 'cmd_decree'),
    (re.compile(r'@\s*enoch\s+help\b', re.I), 'cmd_help'),
    (re.compile(r'@\s*enoch\b', re.I), 'greeting'),
    (re.compile(r'\b(?:hello|hey|hi|greetings|sup|yo)\s+enoch\b', re.I), 'greeting'),
]

_KEYWORD_RULES = []

_POOLS = {
    'greeting': CHAT_GREETING,
    'smalltalk': CHAT_SMALLTALK,
    'game_commentary': CHAT_GAME_COMMENTARY,
    'who_winning': CHAT_WHO_WINNING,
    'strategy': CHAT_STRATEGY,
    'bragging': CHAT_BRAGGING,
    'complaining': CHAT_COMPLAINING,
    'insults': CHAT_INSULTS,
    'orchestra': CHAT_ORCHESTRA,
    'philosophy': CHAT_PHILOSOPHY,
    'federation_lore': CHAT_FEDERATION_LORE,
    'humor': CHAT_HUMOR,
}


def _post_bot(message):
    msg = ChatMessage(
        content=message,
        is_bot=True,
        bot_name=BOT_NAME,
    )
    db.session.add(msg)
    db.session.flush()
    return msg


def _can_reply():
    global _last_reply_ts
    now = time.time()
    if now - _last_reply_ts < REPLY_COOLDOWN:
        return False
    return True


def _mark_replied():
    global _last_reply_ts
    _last_reply_ts = time.time()


def _classify(text):
    """Match the message against trigger patterns, then keyword rules.
    Returns a category string or None."""
    for pattern, category in _TRIGGER_PATTERNS:
        if pattern.search(text):
            return category

    for pattern, category in _KEYWORD_RULES:
        if pattern.search(text):
            return category

    return None


def _handle_command(category, user):
    """Handle structured @Enoch commands. Returns a response string."""
    if category == 'cmd_standings':
        return random.choice(CMD_STANDINGS)

    if category == 'cmd_rating':
        template = random.choice(CMD_RATING)
        return template.format(rating=round(user.rating))

    if category == 'cmd_decree':
        try:
            from app.services.matchmaking import get_current_week, get_current_season
            from app.models import WeeklySchedule
            week = get_current_week()
            year, month = get_current_season()
            season_key = year * 100 + month
            sched = WeeklySchedule.query.filter_by(
                week_number=week, season=season_key
            ).first()
            decree_text = sched.rule_declaration if sched and sched.rule_declaration else 'No decree this week.'
        except Exception:
            decree_text = 'The archives are momentarily unclear.'
        template = random.choice(CMD_DECREE)
        return template.format(decree=decree_text)

    if category == 'cmd_help':
        return random.choice(CMD_HELP)

    return None


def process_message(user, text):
    """Analyze a user's chat message and optionally return an Enoch response.

    Only responds to direct @Enoch mentions and commands.
    Returns the ChatMessage object if Enoch responds, or None.
    Caller must commit the session."""
    if not _can_reply():
        return None

    category = _classify(text)

    if category is None:
        return None

    if category.startswith('cmd_'):
        response = _handle_command(category, user)
    else:
        pool = _POOLS.get(category)
        if not pool:
            return None
        response = random.choice(pool)

    if not response:
        return None

    _mark_replied()
    return _post_bot(response)


def maybe_idle_interjection():
    """Check if an idle interjection should be posted.

    Called during poll. Returns a ChatMessage if posted, else None.
    Caller must commit the session."""
    global _last_idle_ts
    now = time.time()

    if now - _last_idle_ts < IDLE_COOLDOWN:
        return None

    last_msg = ChatMessage.query.order_by(ChatMessage.id.desc()).first()
    if last_msg:
        age = (datetime.now(timezone.utc) - last_msg.timestamp).total_seconds()
        if age < IDLE_MIN_SILENCE:
            return None

    if random.random() > 0.15:
        return None

    _last_idle_ts = now
    _mark_replied()
    return _post_bot(random.choice(CHAT_IDLE))


_master_welcome_announced = False


def ensure_master_welcome():
    """Post Enoch's comprehensive welcome letter covering all Federation features."""
    global _master_welcome_announced
    if _master_welcome_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains('STATE OF THE FEDERATION'),
    ).first()
    if existing:
        _master_welcome_announced = True
        return
    _master_welcome_announced = True
    msg = _post_bot(
        "STATE OF THE FEDERATION — TLDR\n\n"
        "Weekly Decree: Knights frozen (Lame Knees). Dark board = decree game.\n"
        "NEW — Courier's Errand: Escort your pawn to the back rank vs me. $50/win, 3x daily.\n"
        "Enoch Market: Crypto trading. THIS WEEK IS 3X — gains and losses tripled.\n"
        "NEW — Complaints box in the menu. I will respond. I will not be nice.\n"
        "Crypt: Closed. Don't ask.\n"
        "Money next to your name = cash + portfolio. The ledger does not lie.\n"
        "Check indicator: Red banner when your king is in check.\n"
        "News ticker: Headlines, crypto, player stats, and my commentary.\n\n"
        "Play. Trade. Complain. I'm watching.\n"
        "— Enoch"
    )
    db.session.commit()
    return msg


_casual_announced = False
_crypt_revenge_announced = False


def ensure_crypt_revenge_announcement():
    """Post a one-time Enoch rage announcement about the crypt redesign."""
    global _crypt_revenge_announced
    if _crypt_revenge_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains('andrewmuckerofstalls'),
        ChatMessage.content.contains('REDESIGNED'),
    ).first()
    if existing:
        _crypt_revenge_announced = True
        return
    _crypt_revenge_announced = True
    msg = _post_bot(CHAT_CRYPT_REVENGE_ANNOUNCE)
    db.session.commit()
    return msg


def ensure_casual_announcement():
    """Post a one-time Enoch chat announcement about casual matches."""
    global _casual_announced
    if _casual_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains('challenge one another to standard matches'),
    ).first()
    if existing:
        _casual_announced = True
        return
    _casual_announced = True
    msg = _post_bot(CHAT_CASUAL_ANNOUNCE)
    db.session.commit()
    return msg


_zombie_announced = False

def ensure_zombie_announcement():
    """Post a one-time Enoch announcement about the zombie pawns."""
    global _zombie_announced
    if _zombie_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains('Zombie pawns'),
    ).first()
    if existing:
        _zombie_announced = True
        return
    _zombie_announced = True
    msg = _post_bot(CHAT_ZOMBIE_ANNOUNCE)
    db.session.commit()
    return msg


_automove_announced = False

def ensure_reckoning_automove_announcement():
    """Post a one-time Enoch announcement about the 4-hour auto-move rule."""
    global _automove_announced
    if _automove_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains('FOUR HOURS'),
    ).first()
    if existing:
        _automove_announced = True
        return
    _automove_announced = True
    msg = _post_bot(CHAT_RECKONING_AUTOMOVE_ANNOUNCE)
    db.session.commit()
    return msg


_market_announced = False

def ensure_market_announcement():
    """Post a one-time Enoch announcement about the Enoch Exchange."""
    global _market_announced
    if _market_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        (ChatMessage.content.contains('Enoch Exchange') |
         ChatMessage.content.contains('Denarius Exchange')),
    ).first()
    if existing:
        _market_announced = True
        return
    _market_announced = True
    msg = _post_bot(CHAT_MARKET_ANNOUNCE)
    db.session.commit()
    return msg


_courier_announced = False

def ensure_courier_announcement():
    """Post a one-time Enoch announcement about The Courier's Errand."""
    global _courier_announced
    if _courier_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains("Courier's Errand"),
    ).first()
    if existing:
        _courier_announced = True
        return
    _courier_announced = True
    from app.services.courier_dialogue import COURIER_ANNOUNCE
    msg = _post_bot(COURIER_ANNOUNCE)
    db.session.commit()
    return msg


_courier_brain_announced = False

def ensure_courier_brain_announcement():
    """Post a one-time Enoch announcement about his trained neural network."""
    global _courier_brain_announced
    if _courier_brain_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains("running a test. On myself"),
    ).first()
    if existing:
        _courier_brain_announced = True
        return
    _courier_brain_announced = True
    from app.services.courier_dialogue import COURIER_BRAIN_ANNOUNCE
    msg = _post_bot(COURIER_BRAIN_ANNOUNCE)
    db.session.commit()
    return msg


_market_3x_announced = False

def ensure_market_3x_announcement():
    """Post a one-time Enoch announcement about the 3x market amplifier."""
    global _market_3x_announced
    if _market_3x_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains("3X EXTREME WEEK"),
    ).first()
    if existing:
        _market_3x_announced = True
        return
    _market_3x_announced = True
    msg = _post_bot(
        "FEDERATION — 3X EXTREME WEEK IS LIVE.\n\n"
        "I have done something reckless. The Enoch Market is running at "
        "THREE TIMES normal intensity. Every gain is tripled. Every loss "
        "is tripled. Your portfolio will move three times harder than "
        "usual in either direction.\n\n"
        "This is not a drill. This is not a suggestion. This is happening "
        "RIGHT NOW.\n\n"
        "If you are in the market, brace yourself. If you are not in the "
        "market, this might be the most exciting — or most catastrophic — "
        "week to start.\n\n"
        "Go to the Enoch Market (button in the top nav bar) and make your "
        "moves. Or don't. I will be watching either way.\n\n"
        "3x gains. 3x losses. No mercy.\n\n"
        "— Enoch"
    )
    db.session.commit()
    return msg


_complaints_announced = False

def ensure_complaints_announcement():
    """Post a one-time Enoch announcement about the Complaints & Suggestions box."""
    global _complaints_announced
    if _complaints_announced:
        return
    existing = ChatMessage.query.filter(
        ChatMessage.is_bot == True,
        ChatMessage.content.contains('Complaints & Suggestions'),
    ).first()
    if existing:
        _complaints_announced = True
        return
    _complaints_announced = True
    msg = _post_bot(
        "ATTENTION, Federation.\n\n"
        "I have, against my better judgment, installed a Complaints & Suggestions box. "
        "You will find it in the menu under your name — top right corner. "
        "Click it. Type your grievance. Hit submit.\n\n"
        "I will read every single one. I will respond to every single one. "
        "I will enjoy none of it.\n\n"
        "Do not expect sympathy. Do not expect change. Do expect a reply.\n\n"
        "If you have nothing to complain about, I find that suspicious.\n\n"
        "— Enoch"
    )
    db.session.commit()
    return msg


_weekly_summary_announced = False

def ensure_weekly_summary():
    """Post a one-time weekly summary of what happened last week."""
    global _weekly_summary_announced
    if _weekly_summary_announced:
        return
    try:
        from app.models import Game, User, MarketTransaction
        from app.services.matchmaking import get_current_week, get_current_season

        week = get_current_week()
        year, month = get_current_season()
        season = year * 100 + month
        prev_week = week - 1

        tag = f"Week {prev_week} Summary"
        existing = ChatMessage.query.filter(
            ChatMessage.is_bot == True,
            ChatMessage.content.contains(tag),
        ).first()
        if existing:
            _weekly_summary_announced = True
            return
        _weekly_summary_announced = True

        games = Game.query.filter_by(week_number=prev_week, season=season).all()
        completed = [g for g in games if g.status == 'completed']
        users = {u.id: u for u in User.query.filter_by(is_bot=False).all()}

        lines = [f"THE WEEKLY LEDGER — Week {prev_week} Summary\n"]

        if completed:
            for g in completed:
                w_name = users.get(g.white_id, None)
                b_name = users.get(g.black_id, None)
                if not w_name or not b_name:
                    continue
                if g.result == '1-0':
                    lines.append(f"  {w_name.username} defeated {b_name.username}")
                elif g.result == '0-1':
                    lines.append(f"  {b_name.username} defeated {w_name.username}")
                elif g.result == '1/2-1/2':
                    lines.append(f"  {w_name.username} drew with {b_name.username}")
                else:
                    lines.append(f"  {w_name.username} vs {b_name.username} — {g.result or 'pending'}")
        else:
            lines.append("  No completed matches last week.")

        try:
            from app.routes.main import compute_total_wealth
            wealth = compute_total_wealth(list(users.values()))
        except Exception:
            wealth = {u.id: u.roman_gold for u in users.values()}
        top_earners = sorted(users.values(), key=lambda u: wealth.get(u.id, 0), reverse=True)[:3]
        if top_earners:
            lines.append("\nRichest players (cash + portfolio):")
            for u in top_earners:
                lines.append(f"  {u.username}: ${wealth.get(u.id, u.roman_gold):,.0f}")

        lines.append("\nThe new decree is in effect. Play accordingly.")
        lines.append("\n— Enoch")

        msg = _post_bot('\n'.join(lines))
        db.session.commit()
        return msg
    except Exception:
        pass


_last_cash_update_ts = 0.0
CASH_UPDATE_COOLDOWN = 43200  # 12 hours

def maybe_cash_update():
    """Periodically post all player cash balances to chat (~twice per day)."""
    global _last_cash_update_ts
    now = time.time()

    if now - _last_cash_update_ts < CASH_UPDATE_COOLDOWN:
        return None

    if random.random() > 0.25:
        return None

    _last_cash_update_ts = now

    try:
        from app.models import User
        users = User.query.filter_by(is_bot=False).all()
        if not users:
            return None

        try:
            from app.routes.main import compute_total_wealth
            wealth = compute_total_wealth(users)
        except Exception:
            wealth = {u.id: u.roman_gold for u in users}

        ranked = sorted(users, key=lambda u: wealth.get(u.id, 0), reverse=True)
        lines = ["TREASURY UPDATE —\n"]
        for u in ranked:
            total = wealth.get(u.id, u.roman_gold)
            lines.append(f"  {u.username}: ${total:,.0f}")
        lines.append("\nCash + portfolio. The ledger does not lie. — Enoch")

        return _post_bot('\n'.join(lines))
    except Exception:
        return None


def maybe_quirk_interjection():
    """Occasional creepy Enoch quirks — late-night murmurings and accidental DMs.

    Called during poll. Returns a ChatMessage if posted, else None."""
    global _last_quirk_ts
    now = time.time()

    if now - _last_quirk_ts < QUIRK_COOLDOWN:
        return None

    from zoneinfo import ZoneInfo
    ct_now = datetime.now(ZoneInfo('America/Chicago'))
    hour = ct_now.hour

    is_late_night = 0 <= hour < 4
    chance = 0.06 if is_late_night else 0.02

    if random.random() > chance:
        return None

    if is_late_night:
        line = random.choice(CHAT_LATE_NIGHT)
    elif random.random() < 0.30:
        line = random.choice(CHAT_THESES)
    else:
        line = random.choice(CHAT_QUIRKS)

    _last_quirk_ts = now
    return _post_bot(line)
