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


def ensure_rotation_order():
    """If no rotation order exists, create one from all active players."""
    existing = PowerRotationOrder.query.first()
    if existing:
        return
    players = User.query.filter_by(is_active_player=True).order_by(User.id).all()
    if not players:
        return
    set_rotation_order([p.id for p in players])
