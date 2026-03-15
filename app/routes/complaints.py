"""Complaints & Suggestions — where players air grievances and Enoch responds."""

import random

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.models import ChatMessage, Complaint, db

complaints_bp = Blueprint('complaints', __name__)


ENOCH_SNIDE = [
    "Another complaint. How refreshing. I'll file it next to the others — in the furnace.",
    "Noted. I'll address this right after I finish counting every grain of dust in the sub-basement.",
    "Nothing is ever good enough, is it? I maintain an entire underground chess federation and THIS is the thanks I get.",
    "I have logged your grievance. It will be reviewed at the next board meeting, which is never.",
    "Fascinating. Your dissatisfaction has been recorded on a small piece of paper that I have already lost.",
    "I didn't build this place for gratitude. Good thing, too.",
    "Complaint received. Expected resolution date: the heat death of the universe.",
    "You know what I never receive? A simple 'thank you, Enoch.' Just once.",
    "I'll add this to the pile. The pile is on fire. The fire is also complaining.",
    "Another voice in the void. At least the void is consistent.",
    "I have read your concern. I have also read the back of a tin can today. Both were equally moving.",
    "The suggestion box is located in the boiler room. The boiler room is locked. I ate the key.",
    "Your feedback is very important to us. 'Us' being the rats. They seem indifferent.",
    "I will consider your input with the same care I give to unsolicited advice — none.",
    "Do you know how many hours I spend maintaining the ledger? Of course you don't. Nobody asks.",
    "Noted. Filed. Ignored. The standard procedure.",
    "I appreciate your candor. I do not appreciate anything else about this interaction.",
    "Every complaint makes me stronger. That's not true, but it's what I tell myself.",
    "The archive will remember your words. I, personally, will not.",
    "Ah yes, because running an underground chess federation is SO easy. Please, tell me more.",
    "Your suggestion has been forwarded to the Department of Things That Will Never Happen.",
    "If I had a gold coin for every complaint, I'd have... well, YOUR gold coins. Which I already manage.",
    "The pipes will weep for you tonight. Or that's just the plumbing. Hard to tell.",
    "I have taken your feedback under advisement. The advisement lasted three seconds.",
    "Rest assured, your complaint has been carefully considered and immediately discarded.",
]


@complaints_bp.route('/complaints')
@login_required
def complaints_page():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(50).all()
    return render_template('complaints.html', complaints=complaints)


@complaints_bp.route('/complaints/submit', methods=['POST'])
@login_required
def submit_complaint():
    data = request.get_json(force=True)
    text = (data.get('content') or '').strip()
    if not text:
        return jsonify(error='Please write something.'), 400
    if len(text) > 2000:
        return jsonify(error='Too long. Keep it under 2000 characters.'), 400

    snide = random.choice(ENOCH_SNIDE)

    complaint = Complaint(
        user_id=current_user.id,
        content=text,
        enoch_response=snide,
    )
    db.session.add(complaint)

    short_text = text[:60] + ('...' if len(text) > 60 else '')
    chat_msg = ChatMessage(
        user_id=None,
        content=f'{current_user.username} submitted a complaint: "{short_text}"\n\n{snide}\n— Enoch',
        is_bot=True,
        bot_name='Enoch, Steward Beneath the Board',
    )
    db.session.add(chat_msg)
    db.session.commit()

    return jsonify(
        ok=True,
        complaint={
            'id': complaint.id,
            'user': current_user.username,
            'avatar': ('/static/uploads/' + current_user.avatar_filename) if current_user.avatar_filename else None,
            'content': complaint.content,
            'enoch': complaint.enoch_response,
            'created': complaint.created_at.isoformat() if complaint.created_at else '',
        },
    )
