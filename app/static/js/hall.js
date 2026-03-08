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

    function appendMsg(m) {
        const div = document.createElement('div');
        div.className = 'chat-msg' + (m.is_bot ? ' chat-msg-bot' : '');
        div.dataset.msgId = m.id;

        if (m.is_bot) {
            div.innerHTML = `
                <div class="chat-avatar-wrap"><span class="avatar avatar-sm avatar-bot">E</span></div>
                <div class="chat-bubble chat-bubble-bot">
                    <span class="chat-sender chat-sender-bot">${m.bot_name || 'Enoch'}</span>
                    <p class="chat-text">${escapeHtml(m.content)}</p>
                    <span class="chat-time">${m.timestamp}</span>
                </div>`;
        } else {
            const avatarHtml = m.avatar
                ? `<img src="/static/uploads/avatars/${m.avatar}" class="avatar avatar-sm" alt="">`
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
                for (const m of data.messages) appendMsg(m);
                if (atBottom) messages.scrollTop = messages.scrollHeight;
            }
        } catch (e) {
            console.error('Poll failed:', e);
        }
    }

    setInterval(poll, 3000);
});
