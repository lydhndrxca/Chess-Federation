from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.models import ChatMessage, db

hall_bp = Blueprint('hall', __name__)


@hall_bp.route('/hall')
@login_required
def federation_hall():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).limit(200).all()
    return render_template('hall.html', messages=messages)


@hall_bp.route('/hall/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    if not content or len(content) > 1000:
        return jsonify({'error': 'Invalid message'}), 400

    msg = ChatMessage(
        user_id=current_user.id,
        content=content,
        is_bot=False,
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': {
            'id': msg.id,
            'username': current_user.username,
            'avatar': current_user.avatar_filename,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%b %d, %I:%M %p'),
            'is_bot': False,
        },
    })


@hall_bp.route('/hall/poll')
@login_required
def poll_messages():
    after_id = request.args.get('after', 0, type=int)
    messages = ChatMessage.query.filter(
        ChatMessage.id > after_id
    ).order_by(ChatMessage.timestamp.asc()).limit(50).all()

    result = []
    for m in messages:
        result.append({
            'id': m.id,
            'username': m.user.username if m.user else None,
            'avatar': m.user.avatar_filename if m.user else None,
            'content': m.content,
            'timestamp': m.timestamp.strftime('%b %d, %I:%M %p'),
            'is_bot': m.is_bot,
            'bot_name': m.bot_name,
        })

    return jsonify({'messages': result})
