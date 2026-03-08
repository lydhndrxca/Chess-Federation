from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.models import ChatMessage, db
from app.services.enoch import get_title
from app.services.enoch_chat import process_message, maybe_idle_interjection

hall_bp = Blueprint('hall', __name__)


@hall_bp.route('/hall')
@login_required
def federation_hall():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).limit(200).all()
    return render_template('hall.html', messages=messages, enoch_title=get_title())


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
    db.session.flush()

    enoch_reply = None
    try:
        enoch_msg = process_message(current_user, content)
        if enoch_msg:
            enoch_reply = {
                'id': enoch_msg.id,
                'username': None,
                'avatar': None,
                'content': enoch_msg.content,
                'timestamp': enoch_msg.timestamp.strftime('%b %d, %I:%M %p'),
                'is_bot': True,
                'bot_name': enoch_msg.bot_name,
            }
    except Exception:
        pass

    chat_earned = []
    try:
        from app.services.collectibles_engagement import evaluate_chat_triggers
        chat_earned = evaluate_chat_triggers(current_user.id) or []
    except Exception:
        pass

    db.session.commit()

    resp = {
        'success': True,
        'message': {
            'id': msg.id,
            'username': current_user.username,
            'avatar': current_user.avatar_filename,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%b %d, %I:%M %p'),
            'is_bot': False,
        },
    }
    if enoch_reply:
        resp['enoch_reply'] = enoch_reply
    if chat_earned:
        resp['earned_items'] = [{
            'id': it['id'], 'name': it['name'],
            'collection': it['collection'], 'desc': it['desc'],
            'enoch': it['enoch'],
        } for it in chat_earned]

    return jsonify(resp)


@hall_bp.route('/hall/unread')
@login_required
def unread_count():
    after_id = request.args.get('after', 0, type=int)
    count = ChatMessage.query.filter(ChatMessage.id > after_id).count()
    latest = db.session.query(db.func.max(ChatMessage.id)).scalar() or 0
    return jsonify({'count': count, 'latest_id': latest})


@hall_bp.route('/hall/poll')
@login_required
def poll_messages():
    after_id = request.args.get('after', 0, type=int)

    try:
        idle_msg = maybe_idle_interjection()
        if idle_msg:
            db.session.commit()
    except Exception:
        pass

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


@hall_bp.route('/hall/login-greeting')
@login_required
def login_greeting():
    from app.services.login_greetings import get_login_greeting, PLAYER_GREETINGS
    from flask import url_for as _url
    import json, os

    line = get_login_greeting(current_user.username)
    if not line:
        return jsonify({'greeting': None})

    audio_url = None
    manifest_path = os.path.join(
        os.path.dirname(__file__), '..', 'static', 'audio', 'enoch', 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        for entry in manifest.values():
            if entry.get('text') == line:
                audio_url = _url('static', filename='audio/enoch/' + entry['file'])
                break
    except Exception:
        pass

    return jsonify({'greeting': line, 'audio_url': audio_url})
