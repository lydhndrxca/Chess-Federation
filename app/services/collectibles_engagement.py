"""Engagement & milestone collectible evaluator.

Unlike game-analysis triggers which run at match end, these check lifetime
stats: chat messages, commendations, career wins/losses, streaks, and
meta-collection milestones.  Called from various hooks (chat send, game end,
commendation submit, etc.)."""

from datetime import datetime, timezone

from app.models import (ChatMessage, Commendation, EnochWager, Game,
                        NamedSequence, PlayerCollectible, PowerRotationOrder,
                        User, db)
from app.services.collectibles_catalog import CATALOG, CATALOG_BY_TRIGGER, COLLECTIONS


def _already_has(user_id, item_id):
    return PlayerCollectible.query.filter_by(
        user_id=user_id, item_id=item_id).first() is not None


def _award(user_id, item_id, game_id=None):
    pc = PlayerCollectible(
        user_id=user_id,
        item_id=item_id,
        game_id=game_id,
    )
    db.session.add(pc)
    return pc


def _check_and_award(user_id, trigger_key, game_id=None):
    """If the user doesn't already have this item, award it. Returns the
    catalog item dict if newly awarded, else None."""
    cat = CATALOG_BY_TRIGGER.get(trigger_key)
    if not cat:
        return None
    if _already_has(user_id, cat['id']):
        return None
    _award(user_id, cat['id'], game_id)
    return cat


# ══════════════════════════════════════════════════════════════
# CHAT TRIGGERS — call after a message is sent in Federation Hall
# ══════════════════════════════════════════════════════════════

def evaluate_chat_triggers(user_id):
    """Check chat-based collectibles after a user sends a message."""
    earned = []

    msg_count = ChatMessage.query.filter_by(user_id=user_id, is_bot=False).count()

    if msg_count >= 1:
        r = _check_and_award(user_id, 'eng_first_chat_message')
        if r:
            earned.append(r)

    if msg_count >= 100:
        r = _check_and_award(user_id, 'eng_100_chat_messages')
        if r:
            earned.append(r)

    if msg_count >= 500:
        r = _check_and_award(user_id, 'eng_500_chat_messages')
        if r:
            earned.append(r)

    now = datetime.now(timezone.utc)
    if 2 <= now.hour < 4:
        r = _check_and_award(user_id, 'eng_chat_at_3am')
        if r:
            earned.append(r)

    recent = ChatMessage.query.filter_by(user_id=user_id, is_bot=False)\
        .order_by(ChatMessage.id.desc()).limit(10).all()
    if len(recent) >= 10:
        first_ts = recent[-1].timestamp
        last_ts = recent[0].timestamp
        if first_ts and last_ts:
            delta = (last_ts - first_ts).total_seconds()
            if delta <= 180:
                r = _check_and_award(user_id, 'eng_rapid_fire_chat')
                if r:
                    earned.append(r)

    enoch_mentions = ChatMessage.query.filter(
        ChatMessage.user_id == user_id,
        ChatMessage.is_bot == False,
        ChatMessage.content.ilike('%enoch%'),
    ).count()
    if enoch_mentions >= 20:
        r = _check_and_award(user_id, 'eng_mention_enoch_20')
        if r:
            earned.append(r)

    try:
        db.session.flush()
    except Exception:
        pass

    return earned


def award_enoch_lurked(user_id):
    """Called when Enoch's lurk triggers while a user is in the hall."""
    r = _check_and_award(user_id, 'eng_enoch_lurked')
    if r:
        try:
            db.session.flush()
        except Exception:
            pass
    return r


# ══════════════════════════════════════════════════════════════
# COMMENDATION TRIGGERS
# ══════════════════════════════════════════════════════════════

def evaluate_commendation_triggers(user_id):
    """Check after a user gives a commendation/condemnation."""
    earned = []

    given_commends = Commendation.query.filter_by(author_id=user_id, kind='commend').count()
    given_condemns = Commendation.query.filter_by(author_id=user_id, kind='condemn').count()

    if given_commends >= 1:
        r = _check_and_award(user_id, 'eng_first_commendation')
        if r:
            earned.append(r)

    if given_condemns >= 1:
        r = _check_and_award(user_id, 'eng_first_condemnation')
        if r:
            earned.append(r)

    received_commends = Commendation.query.filter_by(subject_id=user_id, kind='commend').count()
    if received_commends >= 5:
        r = _check_and_award(user_id, 'eng_receive_5_commendations')
        if r:
            earned.append(r)

    received_condemns = Commendation.query.filter_by(subject_id=user_id, kind='condemn').count()
    if received_condemns >= 5:
        r = _check_and_award(user_id, 'eng_receive_5_condemnations')
        if r:
            earned.append(r)

    from app.services.matchmaking import get_current_week
    week = get_current_week()
    week_commends = Commendation.query.join(Game).filter(
        Commendation.author_id == user_id,
        Commendation.kind == 'commend',
        Game.week_number == week,
    ).count()
    week_condemns = Commendation.query.join(Game).filter(
        Commendation.author_id == user_id,
        Commendation.kind == 'condemn',
        Game.week_number == week,
    ).count()
    if week_commends >= 1 and week_condemns >= 1:
        r = _check_and_award(user_id, 'eng_give_both_commend_condemn')
        if r:
            earned.append(r)

    try:
        db.session.flush()
    except Exception:
        pass

    return earned


# ══════════════════════════════════════════════════════════════
# SEQUENCE NAMING TRIGGERS
# ══════════════════════════════════════════════════════════════

def evaluate_naming_triggers(user_id):
    earned = []
    count = NamedSequence.query.filter_by(creator_id=user_id).count()

    if count >= 1:
        r = _check_and_award(user_id, 'eng_first_named_sequence')
        if r:
            earned.append(r)

    if count >= 5:
        r = _check_and_award(user_id, 'eng_name_5_sequences')
        if r:
            earned.append(r)

    try:
        db.session.flush()
    except Exception:
        pass

    return earned


# ══════════════════════════════════════════════════════════════
# CAREER / MILESTONE TRIGGERS — call after any game completes
# ══════════════════════════════════════════════════════════════

def evaluate_milestone_triggers(user_id, game_id=None):
    """Check career milestones, streaks, and meta-collection goals."""
    earned = []
    user = User.query.get(user_id)
    if not user:
        return earned

    total = user.total_games or 0
    wins = user.wins or 0
    draws = user.draws or 0

    if wins >= 1:
        r = _check_and_award(user_id, 'eng_first_win', game_id)
        if r:
            earned.append(r)

    if wins >= 10:
        r = _check_and_award(user_id, 'eng_10_wins', game_id)
        if r:
            earned.append(r)

    if wins >= 25:
        r = _check_and_award(user_id, 'eng_25_wins', game_id)
        if r:
            earned.append(r)

    if wins >= 50:
        r = _check_and_award(user_id, 'eng_50_wins', game_id)
        if r:
            earned.append(r)

    if total >= 10:
        r = _check_and_award(user_id, 'eng_10_games', game_id)
        if r:
            earned.append(r)

    if total >= 50:
        r = _check_and_award(user_id, 'eng_50_games', game_id)
        if r:
            earned.append(r)

    if total >= 100:
        r = _check_and_award(user_id, 'eng_100_games', game_id)
        if r:
            earned.append(r)

    if draws >= 5:
        r = _check_and_award(user_id, 'eng_5_draws', game_id)
        if r:
            earned.append(r)

    recent_games = Game.query.filter(
        ((Game.white_id == user_id) | (Game.black_id == user_id)),
        Game.status.in_(['completed', 'forfeited']),
    ).order_by(Game.completed_at.desc()).limit(5).all()

    if len(recent_games) >= 3:
        streak_w = 0
        streak_l = 0
        for g in recent_games:
            won = (g.result == '1-0' and g.white_id == user_id) or \
                  (g.result == '0-1' and g.black_id == user_id)
            lost = (g.result == '0-1' and g.white_id == user_id) or \
                   (g.result == '1-0' and g.black_id == user_id)
            if won:
                streak_w += 1
                streak_l = 0
            elif lost:
                streak_l += 1
                streak_w = 0
            else:
                break

        if streak_w >= 3:
            r = _check_and_award(user_id, 'eng_3_win_streak', game_id)
            if r:
                earned.append(r)
        if streak_w >= 5:
            r = _check_and_award(user_id, 'eng_5_win_streak', game_id)
            if r:
                earned.append(r)
        if streak_l >= 3:
            r = _check_and_award(user_id, 'eng_3_loss_streak', game_id)
            if r:
                earned.append(r)

    # Consecutive black wins
    black_games = Game.query.filter(
        Game.black_id == user_id,
        Game.status.in_(['completed', 'forfeited']),
    ).order_by(Game.completed_at.desc()).limit(3).all()
    if len(black_games) >= 3:
        if all(g.result == '0-1' for g in black_games[:3]):
            r = _check_and_award(user_id, 'three_black_wins_streak', game_id)
            if r:
                earned.append(r)

    # Checkmate career count
    checkmate_wins = Game.query.filter(
        ((Game.white_id == user_id) & (Game.result == '1-0')) |
        ((Game.black_id == user_id) & (Game.result == '0-1')),
        Game.result_type == 'checkmate',
    ).count()
    if checkmate_wins >= 10:
        r = _check_and_award(user_id, 'ten_checkmates_career', game_id)
        if r:
            earned.append(r)

    # Rating drop trigger
    if game_id:
        g = Game.query.get(game_id)
        if g:
            rc = g.rating_change_white if g.white_id == user_id else g.rating_change_black
            if rc is not None and rc <= -50:
                r = _check_and_award(user_id, 'eng_rating_drop_50', game_id)
                if r:
                    earned.append(r)

    # Tier promotion — compare current rating to previous
    # (checked externally via the rating system)

    # ── Meta-collection triggers ──
    owned_count = PlayerCollectible.query.filter_by(user_id=user_id)\
        .with_entities(PlayerCollectible.item_id).distinct().count()

    if owned_count >= 10:
        r = _check_and_award(user_id, 'eng_collect_10')
        if r:
            earned.append(r)

    if owned_count >= 25:
        r = _check_and_award(user_id, 'eng_collect_25')
        if r:
            earned.append(r)

    if owned_count >= 50:
        r = _check_and_award(user_id, 'eng_collect_50')
        if r:
            earned.append(r)

    # All collections
    owned_ids = {r.item_id for r in PlayerCollectible.query.filter_by(user_id=user_id).all()}
    from app.services.collectibles_catalog import CATALOG as _CAT
    coll_covered = set()
    for item in _CAT:
        if item['id'] in owned_ids:
            coll_covered.add(item['collection'])
    if len(coll_covered) >= len(COLLECTIONS):
        r = _check_and_award(user_id, 'eng_collect_all_collections')
        if r:
            earned.append(r)

    try:
        db.session.flush()
    except Exception:
        pass

    return earned


def evaluate_power_position_trigger(user_id):
    """Called when a user serves as power position holder."""
    r = _check_and_award(user_id, 'eng_decree_submitted')
    if r:
        try:
            db.session.flush()
        except Exception:
            pass
    return r


def evaluate_tier_promotion(user_id, game_id=None):
    """Called when a player's tier changes upward."""
    r = _check_and_award(user_id, 'eng_tier_promotion', game_id)
    if r:
        try:
            db.session.flush()
        except Exception:
            pass
    return r


# ══════════════════════════════════════════════════════════════
# GAMBLING TRIGGERS — call after a wager is settled
# ══════════════════════════════════════════════════════════════

def evaluate_wager_triggers(user_id, game_id, wager_result, wager_mood, is_anomaly):
    """Check all gambling collectible triggers after a wager settles.

    wager_result: 'win', 'loss', or 'draw'
    wager_mood:   'chill', 'annoyed', or 'angry'
    is_anomaly:   bool
    Returns list of newly earned catalog item dicts.
    """
    earned = []

    def _try(trigger_key):
        r = _check_and_award(user_id, trigger_key, game_id)
        if r:
            earned.append(r)

    user = db.session.get(User, user_id)
    if not user:
        return earned

    total_bets = user.enoch_wager_wins + user.enoch_wager_losses + user.enoch_wager_draws
    total_wins = user.enoch_wager_wins

    _try('wager_first_bet')

    if wager_result == 'win':
        _try('wager_first_win')
    elif wager_result == 'loss':
        _try('wager_first_loss')

    if total_bets >= 5:
        _try('wager_5_bets')
    if total_bets >= 15:
        _try('wager_15_bets')
    if total_bets >= 30:
        _try('wager_30_bets')

    if total_wins >= 10:
        _try('wager_10_wins')

    if user.enoch_points >= 25:
        _try('wager_net_plus_25')
    if user.enoch_points >= 50:
        _try('wager_net_plus_50')
    if user.enoch_points <= -25:
        _try('wager_net_minus_25')

    if is_anomaly and wager_result == 'win':
        _try('wager_survive_anomaly')

    if wager_result == 'win' and wager_mood == 'angry':
        _try('wager_win_angry')
    if wager_result == 'win' and wager_mood == 'chill':
        _try('wager_win_chill')

    if wager_result == 'win':
        recent = EnochWager.query.filter_by(user_id=user_id)\
            .filter(EnochWager.result.isnot(None))\
            .order_by(EnochWager.created_at.desc()).limit(3).all()
        if len(recent) >= 3 and all(w.result == 'win' for w in recent):
            _try('wager_3_wins_streak')

    if wager_result == 'loss':
        recent = EnochWager.query.filter_by(user_id=user_id)\
            .filter(EnochWager.result.isnot(None))\
            .order_by(EnochWager.created_at.desc()).limit(3).all()
        if len(recent) >= 3 and all(w.result == 'loss' for w in recent):
            _try('wager_3_losses_streak')

    try:
        db.session.flush()
    except Exception:
        pass

    return earned
