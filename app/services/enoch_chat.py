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

REPLY_COOLDOWN = 60
IDLE_MIN_SILENCE = 43200
IDLE_COOLDOWN = 43200
LURK_COOLDOWN = 3600
LURK_MSG_THRESHOLD = 5
LURK_WINDOW = 180
LURK_CHANCE = 0.08

_TRIGGER_PATTERNS = [
    (re.compile(r'@\s*enoch\s+standings?\b', re.I), 'cmd_standings'),
    (re.compile(r'@\s*enoch\s+rating\b', re.I), 'cmd_rating'),
    (re.compile(r'@\s*enoch\s+decree\b', re.I), 'cmd_decree'),
    (re.compile(r'@\s*enoch\s+help\b', re.I), 'cmd_help'),
    (re.compile(r'@\s*enoch\b', re.I), 'greeting'),
    (re.compile(r'\b(?:hello|hey|hi|greetings|sup|yo)\s+enoch\b', re.I), 'greeting'),
    (re.compile(r'\benoch\b', re.I), 'greeting'),
]

_KEYWORD_RULES = [
    (re.compile(r'\bwho(?:\'?s| is)\s+winning\b', re.I), 'who_winning'),
    (re.compile(r'\bwho(?:\'?s| is)\s+ahead\b', re.I), 'who_winning'),
    (re.compile(r'\bwinning\b', re.I), 'who_winning'),

    (re.compile(r'\b(?:violin|cello|orchestra|band|music|instrument|trumpet|flute|piano|drum|bassoon|clarinet|tuba|oboe|harp)\b', re.I), 'orchestra'),
    (re.compile(r'\bschool\b', re.I), 'orchestra'),

    (re.compile(r'\bwhy\s+(?:do\s+we|play)\b', re.I), 'philosophy'),
    (re.compile(r'\bmeaning\s+of\b', re.I), 'philosophy'),
    (re.compile(r'\bwhat\s+is\s+chess\b', re.I), 'philosophy'),
    (re.compile(r'\bphilosoph', re.I), 'philosophy'),

    (re.compile(r'\b(?:help|advice|what\s+should\s+i\s+do|suggest|recommend|tip)\b', re.I), 'strategy'),

    (re.compile(r'\b(?:good\s+move|great\s+move|nice\s+move|brilliant|look\s+at\s+this|what\s+do\s+you\s+think|thoughts|analyze)\b', re.I), 'game_commentary'),

    (re.compile(r'(?:i\'?m\s+the\s+best|too\s+easy|crush(?:ed)?|destroy(?:ed)?|wreck(?:ed)?|dominat|unstoppable|fear\s+me|bow\s+(?:down|to)|king\s+of|ez\b|gg\s+ez|i\s+am\s+the\s+best|get\s+rekt|git\s+gud)', re.I), 'bragging'),

    (re.compile(r'\b(?:unfair|lucky|luck|lag|rigged|cheat|hate\s+this|hate\s+chess|bs|stupid|garbage|trash\s+game)\b', re.I), 'complaining'),

    (re.compile(r'\b(?:federation|this\s+place|the\s+vault|the\s+archive|ledger|how\s+long|history)\b', re.I), 'federation_lore'),

    (re.compile(r'\b(?:lol|lmao|rofl|haha|hehe|funny|joke|hilarious|comedy|laugh)\b', re.I), 'humor'),

    (re.compile(r'\b(?:how\s+are\s+you|what\'?s\s+up|how\s+goes|how\s+do\s+you\s+feel|what\s+are\s+you\s+doing|weather|cold|warm|today)\b', re.I), 'smalltalk'),

    (re.compile(r'\b(?:fuck|shit|damn|ass|bitch|idiot|moron|stupid|dumb|suck|loser|pathetic|screw\s+you|shut\s+up)\b', re.I), 'insults'),
]

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

    Returns the ChatMessage object if Enoch responds, or None.
    Caller must commit the session."""
    if not _can_reply():
        return None

    category = _classify(text)

    if category is None:
        return _maybe_lurk()

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
