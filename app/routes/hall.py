import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from app.models import ChatMessage, ChatReaction, db
from app.services.enoch import get_title
from app.services.enoch_chat import process_message, maybe_idle_interjection, maybe_quirk_interjection, maybe_cash_update

hall_bp = Blueprint('hall', __name__)

ALLOWED_IMG_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}


@hall_bp.route('/hall')
@login_required
def federation_hall():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).limit(200).all()
    return render_template('hall.html', messages=messages, enoch_title=get_title(),
                           upload_base='uploads/chat/')


def _serialize_msg(m):
    """Serialize a ChatMessage to a JSON-friendly dict."""
    reactions = {}
    for r in (m.reactions or []):
        reactions.setdefault(r.emoji, []).append({
            'user_id': r.user_id,
            'username': r.user.username if r.user else None,
        })

    reply_preview = None
    if m.reply_to_id and m.reply_to:
        rt = m.reply_to
        reply_preview = {
            'id': rt.id,
            'username': rt.user.username if rt.user else ('Enoch' if rt.is_bot else None),
            'content': (rt.content or '')[:80],
            'is_bot': rt.is_bot,
        }

    return {
        'id': m.id,
        'user_id': m.user_id,
        'username': m.user.username if m.user else None,
        'avatar': m.user.avatar_filename if m.user else None,
        'content': m.content,
        'timestamp': m.timestamp.strftime('%b %d, %I:%M %p'),
        'is_bot': m.is_bot,
        'bot_name': m.bot_name,
        'reply_to': reply_preview,
        'image': m.image_filename,
        'edited': m.edited or False,
        'reactions': reactions,
    }


@hall_bp.route('/hall/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    reply_to_id = data.get('reply_to_id')
    if not content or len(content) > 2000:
        return jsonify({'error': 'Invalid message'}), 400

    try:
        reply_id_int = int(reply_to_id) if reply_to_id else None
    except (ValueError, TypeError):
        reply_id_int = None

    msg = ChatMessage(
        user_id=current_user.id,
        content=content,
        is_bot=False,
        reply_to_id=reply_id_int,
    )
    db.session.add(msg)
    db.session.flush()

    enoch_reply = None
    try:
        enoch_msg = process_message(current_user, content)
        if enoch_msg:
            enoch_reply = _serialize_msg(enoch_msg)
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
        'message': _serialize_msg(msg),
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


@hall_bp.route('/hall/upload-image', methods=['POST'])
@login_required
def upload_chat_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image'}), 400
    f = request.files['image']
    ext = os.path.splitext(f.filename or '')[1].lower()
    if ext not in ALLOWED_IMG_EXT:
        return jsonify({'error': 'Invalid image type'}), 400

    fname = f'chat_{uuid.uuid4().hex[:12]}{ext}'
    upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads'), 'chat')
    os.makedirs(upload_dir, exist_ok=True)
    f.save(os.path.join(upload_dir, fname))

    content = request.form.get('content', '').strip() or '[image]'
    reply_to_id = request.form.get('reply_to_id')
    try:
        reply_id_int = int(reply_to_id) if reply_to_id else None
    except (ValueError, TypeError):
        reply_id_int = None

    msg = ChatMessage(
        user_id=current_user.id,
        content=content,
        is_bot=False,
        image_filename=fname,
        reply_to_id=reply_id_int,
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({'success': True, 'message': _serialize_msg(msg)})


@hall_bp.route('/hall/react', methods=['POST'])
@login_required
def react_to_message():
    data = request.get_json() or {}
    msg_id = data.get('message_id')
    emoji = data.get('emoji', '').strip()
    if not msg_id or not emoji or len(emoji) > 10:
        return jsonify({'error': 'Invalid'}), 400

    existing = ChatReaction.query.filter_by(
        message_id=msg_id, user_id=current_user.id, emoji=emoji
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'action': 'removed', 'emoji': emoji})
    else:
        r = ChatReaction(message_id=msg_id, user_id=current_user.id, emoji=emoji)
        db.session.add(r)
        db.session.commit()
        return jsonify({'action': 'added', 'emoji': emoji, 'id': r.id})


@hall_bp.route('/hall/edit', methods=['POST'])
@login_required
def edit_message():
    data = request.get_json() or {}
    msg_id = data.get('message_id')
    new_content = data.get('content', '').strip()
    if not msg_id or not new_content or len(new_content) > 2000:
        return jsonify({'error': 'Invalid'}), 400
    msg = ChatMessage.query.get(msg_id)
    if not msg or msg.user_id != current_user.id or msg.is_bot:
        return jsonify({'error': 'Not allowed'}), 403
    msg.content = new_content
    msg.edited = True
    db.session.commit()
    return jsonify({'success': True, 'message': _serialize_msg(msg)})


@hall_bp.route('/hall/delete', methods=['POST'])
@login_required
def delete_message():
    data = request.get_json() or {}
    msg_id = data.get('message_id')
    if not msg_id:
        return jsonify({'error': 'Invalid'}), 400
    msg = ChatMessage.query.get(msg_id)
    if not msg or msg.user_id != current_user.id or msg.is_bot:
        return jsonify({'error': 'Not allowed'}), 403
    ChatReaction.query.filter_by(message_id=msg_id).delete()
    db.session.delete(msg)
    db.session.commit()
    return jsonify({'success': True, 'deleted_id': msg_id})


@hall_bp.route('/hall/unread')
@login_required
def unread_count():
    after_id = request.args.get('after', 0, type=int)
    count = ChatMessage.query.filter(ChatMessage.id > after_id).count()
    latest = db.session.query(db.func.max(ChatMessage.id)).scalar() or 0

    username = current_user.username
    mentions = 0
    if username and count > 0:
        mentions = ChatMessage.query.filter(
            ChatMessage.id > after_id,
            ChatMessage.user_id != current_user.id,
            ChatMessage.content.ilike(f'%{username}%'),
        ).count()

    return jsonify({'count': count, 'latest_id': latest, 'mentions': mentions})


@hall_bp.route('/hall/poll')
@login_required
def poll_messages():
    after_id = request.args.get('after', 0, type=int)

    try:
        idle_msg = maybe_idle_interjection()
        if idle_msg:
            db.session.commit()
        else:
            quirk_msg = maybe_quirk_interjection()
            if quirk_msg:
                db.session.commit()
            else:
                cash_msg = maybe_cash_update()
                if cash_msg:
                    db.session.commit()
    except Exception:
        pass

    messages = ChatMessage.query.filter(
        ChatMessage.id > after_id
    ).order_by(ChatMessage.timestamp.asc()).limit(50).all()

    return jsonify({'messages': [_serialize_msg(m) for m in messages]})


@hall_bp.route('/hall/login-greeting')
@login_required
def login_greeting():
    from app.services.login_greetings import get_login_greeting
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
