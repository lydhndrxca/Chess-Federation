"""Enoch Chat Engine — interactive keyword-and-context matching system.

Enoch listens to Federation Hall messages and responds when triggered.
Rate-limited to feel natural, not scripted."""

import random
import re
import time
from datetime import datetime, timedelta, timezone

from app.models import ChatMessage, Game, User, db
from app.services.dialogue import (
    CHAT_GREETING, CHAT_SMALLTALK, CHAT_GAME_COMMENTARY, CHAT_WHO_WINNING,
    CHAT_STRATEGY, CHAT_BRAGGING, CHAT_COMPLAINING, CHAT_INSULTS,
    CHAT_ORCHESTRA, CHAT_PHILOSOPHY, CHAT_IDLE, CHAT_HUMOR,
    CHAT_FEDERATION_LORE, CHAT_LURKING,
    CMD_STANDINGS, CMD_RATING, CMD_DECREE, CMD_HELP,
)

BOT_NAME = 'Enoch'

_last_reply_ts = 0.0
_last_idle_ts = 0.0
_last_lurk_ts = 0.0

REPLY_COOLDOWN = 600
IDLE_MIN_SILENCE = 86400
IDLE_COOLDOWN = 86400
LURK_COOLDOWN = 43200
LURK_MSG_THRESHOLD = 12
LURK_WINDOW = 300
LURK_CHANCE = 0.03

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
            from app.services.matchmaking import get_current_week
            from app.models import Game as G
            week = get_current_week()
            game = G.query.filter_by(week=week).first()
            decree_text = game.rule_snapshot if game and game.rule_snapshot else 'No decree this week.'
        except Exception:
            decree_text = 'The archives are momentarily unclear.'
        template = random.choice(CMD_DECREE)
        return template.format(decree=decree_text)

    if category == 'cmd_help':
        return random.choice(CMD_HELP)

    return None


def _maybe_lurk():
    """Check if Enoch should drop an ambient lurking line during busy chat.
    Returns a ChatMessage or None."""
    global _last_lurk_ts
    now = time.time()

    if now - _last_lurk_ts < LURK_COOLDOWN:
        return None
    if now - _last_reply_ts < REPLY_COOLDOWN:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=LURK_WINDOW)
    recent_count = ChatMessage.query.filter(
        ChatMessage.timestamp >= cutoff,
        ChatMessage.is_bot == False,  # noqa: E712
    ).count()

    if recent_count < LURK_MSG_THRESHOLD:
        return None

    if random.random() > LURK_CHANCE:
        return None

    _last_lurk_ts = now
    _mark_replied()

    try:
        from app.services.collectibles_engagement import award_enoch_lurked
        cutoff_inner = datetime.now(timezone.utc) - timedelta(seconds=LURK_WINDOW)
        active_users = ChatMessage.query.filter(
            ChatMessage.timestamp >= cutoff_inner,
            ChatMessage.is_bot == False,
        ).with_entities(ChatMessage.user_id).distinct().all()
        for (uid,) in active_users:
            if uid:
                award_enoch_lurked(uid)
    except Exception:
        pass

    return _post_bot(random.choice(CHAT_LURKING))


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
