from app.models import PowerRotationOrder, User, db
from app.services.matchmaking import get_current_week


def get_rotation_order():
    """Return the ordered list of users in the power rotation."""
    entries = PowerRotationOrder.query.order_by(PowerRotationOrder.position).all()
    return [e.user for e in entries if e.user]


def set_rotation_order(user_ids):
    """Replace the rotation order with the given user IDs."""
    PowerRotationOrder.query.delete()
    for pos, uid in enumerate(user_ids):
        db.session.add(PowerRotationOrder(user_id=uid, position=pos))
    db.session.commit()


def get_current_holder():
    """Determine who holds the Power Position this week."""
    order = get_rotation_order()
    if not order:
        return None
    week = get_current_week()
    idx = week % len(order)
    return order[idx]


def get_next_holder():
    """Determine who will hold the Power Position next week."""
    order = get_rotation_order()
    if not order:
        return None
    week = get_current_week()
    idx = (week + 1) % len(order)
    return order[idx]


def ensure_rotation_order():
    """Create rotation if missing, and add any new players not yet in it."""
    entries = PowerRotationOrder.query.order_by(PowerRotationOrder.position).all()

    if not entries:
        players = User.query.filter_by(is_active_player=True).order_by(User.id).all()
        if not players:
            return
        n = len(players)
        week = get_current_week()
        ordered_ids = [None] * n
        for i, p in enumerate(players):
            ordered_ids[(week + i) % n] = p.id
        set_rotation_order(ordered_ids)
        return

    existing_ids = {e.user_id for e in entries}
    active = User.query.filter_by(is_active_player=True).all()
    max_pos = max(e.position for e in entries)
    added = False
    for p in active:
        if p.id not in existing_ids:
            max_pos += 1
            db.session.add(PowerRotationOrder(user_id=p.id, position=max_pos))
            added = True
    if added:
        db.session.commit()
