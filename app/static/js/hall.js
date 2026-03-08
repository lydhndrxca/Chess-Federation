document.addEventListener('DOMContentLoaded', () => {
    const messages = document.getElementById('chatMessages');
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');
    if (!messages || !input) return;

    let lastMsgId = 0;
    const existing = messages.querySelectorAll('.chat-msg');
    if (existing.length) {
        lastMsgId = parseInt(existing[existing.length - 1].dataset.msgId) || 0;
    }

    messages.scrollTop = messages.scrollHeight;

    function markSeen(id) {
        const prev = parseInt(localStorage.getItem('chatLastSeen') || '0', 10);
        if (id > prev) localStorage.setItem('chatLastSeen', String(id));
        const badge = document.getElementById('chatBadge');
        if (badge) badge.classList.remove('active');
    }
    if (lastMsgId) markSeen(lastMsgId);

    function appendMsg(m) {
        const div = document.createElement('div');
        div.className = 'chat-msg' + (m.is_bot ? ' chat-msg-bot' : '');
        div.dataset.msgId = m.id;

        if (m.is_bot) {
            div.innerHTML = `
                <div class="chat-avatar-wrap"><img src="${window.STATIC_BASE || '/static/'}img/enoch.png" class="avatar avatar-sm avatar-enoch" alt="Enoch"></div>
                <div class="chat-bubble chat-bubble-bot">
                    <span class="chat-sender chat-sender-bot">${m.bot_name || 'Enoch'}</span>
                    <p class="chat-text chat-text-bot">${escapeHtml(m.content)}</p>
                    <span class="chat-time">${m.timestamp}</span>
                </div>`;
        } else {
            const avatarHtml = m.avatar
                ? `<img src="${window.STATIC_BASE || '/static/'}uploads/avatars/${m.avatar}" class="avatar avatar-sm" alt="">`
                : `<span class="avatar avatar-sm avatar-placeholder">${(m.username || '?')[0].toUpperCase()}</span>`;
            div.innerHTML = `
                <div class="chat-avatar-wrap">${avatarHtml}</div>
                <div class="chat-bubble">
                    <span class="chat-sender">${escapeHtml(m.username || '')}</span>
                    <p class="chat-text">${escapeHtml(m.content)}</p>
                    <span class="chat-time">${m.timestamp}</span>
                </div>`;
        }
        messages.appendChild(div);
        if (m.id > lastMsgId) lastMsgId = m.id;
        markSeen(m.id);
    }

    function showTypingIndicator() {
        const div = document.createElement('div');
        div.className = 'chat-msg chat-msg-bot enoch-typing';
        div.id = 'enochTyping';
        div.innerHTML = `
            <div class="chat-avatar-wrap"><img src="${window.STATIC_BASE || '/static/'}img/enoch.png" class="avatar avatar-sm avatar-enoch" alt="Enoch"></div>
            <div class="chat-bubble chat-bubble-bot">
                <span class="chat-sender chat-sender-bot">Enoch</span>
                <p class="chat-text chat-text-bot typing-dots"><span>.</span><span>.</span><span>.</span></p>
            </div>`;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function removeTypingIndicator() {
        const el = document.getElementById('enochTyping');
        if (el) el.remove();
    }

    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    async function send() {
        const text = input.value.trim();
        if (!text) return;
        input.value = '';
        try {
            const resp = await fetch('/hall/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: text }),
            });
            const data = await resp.json();
            if (data.success) {
                appendMsg(data.message);
                messages.scrollTop = messages.scrollHeight;

                if (data.enoch_reply) {
                    showTypingIndicator();
                    const delay = 2000 + Math.random() * 2000;
                    setTimeout(() => {
                        removeTypingIndicator();
                        appendMsg(data.enoch_reply);
                        messages.scrollTop = messages.scrollHeight;
                    }, delay);
                }

                if (data.earned_items && data.earned_items.length && window.showAwardQueue) {
                    window.showAwardQueue(data.earned_items);
                }
            }
        } catch (e) {
            console.error('Send failed:', e);
        }
    }

    sendBtn.addEventListener('click', send);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') send();
    });

    async function poll() {
        try {
            const resp = await fetch(`/hall/poll?after=${lastMsgId}`);
            const data = await resp.json();
            if (data.messages && data.messages.length) {
                const atBottom = messages.scrollHeight - messages.scrollTop - messages.clientHeight < 80;
                for (const m of data.messages) {
                    if (!document.querySelector(`[data-msg-id="${m.id}"]`)) {
                        appendMsg(m);
                    }
                }
                if (atBottom) messages.scrollTop = messages.scrollHeight;
            }
        } catch (e) {
            console.error('Poll failed:', e);
        }
    }

    setInterval(poll, 3000);
});
