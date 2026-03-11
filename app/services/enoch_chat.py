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
    CHAT_RECKONING_AUTOMOVE_ANNOUNCE,
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
