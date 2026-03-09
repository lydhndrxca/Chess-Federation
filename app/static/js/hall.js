document.addEventListener('DOMContentLoaded', () => {
    const cfg = window.CHAT_CONFIG || {};
    const myId = cfg.currentUserId;
    const myName = cfg.currentUsername || '';
    const enochTitle = cfg.enochTitle || 'Enoch';
    const enochImg = cfg.enochImg || '/static/img/enoch.png';
    const staticBase = cfg.staticBase || '/static/';

    const chatBody = document.getElementById('chatBody');
    const messages = document.getElementById('chatMessages');
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');
    const scrollFab = document.getElementById('chatScrollFab');
    if (!messages || !input) return;

    let lastMsgId = 0;
    const existing = messages.querySelectorAll('.msg-row');
    if (existing.length) {
        lastMsgId = parseInt(existing[existing.length - 1].dataset.msgId) || 0;
    }

    scrollToBottom(false);

    function markSeen(id) {
        const prev = parseInt(localStorage.getItem('chatLastSeen') || '0', 10);
        if (id > prev) localStorage.setItem('chatLastSeen', String(id));
        const badge = document.getElementById('chatBadge');
        if (badge) badge.classList.remove('active');
    }
    if (lastMsgId) markSeen(lastMsgId);

    /* ── Scroll helpers ── */
    function isNearBottom() {
        if (!chatBody) return true;
        return chatBody.scrollHeight - chatBody.scrollTop - chatBody.clientHeight < 100;
    }

    function scrollToBottom(smooth) {
        if (!chatBody) return;
        if (smooth) {
            chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });
        } else {
            chatBody.scrollTop = chatBody.scrollHeight;
        }
    }

    if (chatBody) {
        chatBody.addEventListener('scroll', () => {
            if (scrollFab) {
                scrollFab.classList.toggle('visible', !isNearBottom());
            }
        });
    }
    if (scrollFab) {
        scrollFab.addEventListener('click', () => scrollToBottom(true));
    }

    /* ── Message rendering ── */
    let lastAppendedUserId = null;
    let lastAppendedIsBot = false;
    let currentGroup = null;
    let currentStack = null;

    // Detect last group's sender from the server-rendered HTML
    const groups = messages.querySelectorAll('.msg-group');
    if (groups.length) {
        const last = groups[groups.length - 1];
        if (last.classList.contains('msg-group-own')) {
            lastAppendedUserId = myId;
            lastAppendedIsBot = false;
        } else if (last.classList.contains('msg-group-bot')) {
            lastAppendedIsBot = true;
            lastAppendedUserId = null;
        } else {
            lastAppendedIsBot = false;
            const row = last.querySelector('.msg-row');
            lastAppendedUserId = row ? parseInt(row.dataset.userId) || null : null;
        }
        currentGroup = last;
        currentStack = last.querySelector('.msg-stack');
    }

    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function avatarHtml(m) {
        if (m.is_bot) {
            return `<img src="${enochImg}" class="avatar avatar-sm avatar-enoch" alt="Enoch">`;
        }
        if (m.avatar) {
            return `<img src="${staticBase}uploads/avatars/${m.avatar}" class="avatar avatar-sm" alt="">`;
        }
        return `<span class="avatar avatar-sm avatar-placeholder">${(m.username || '?')[0].toUpperCase()}</span>`;
    }

    function isSameSender(m) {
        if (m.is_bot) return lastAppendedIsBot;
        return !lastAppendedIsBot && lastAppendedUserId === (m.user_id || null);
    }

    function appendMsg(m) {
        const isOwn = !m.is_bot && (m.user_id === myId || m.username === myName);
        const sameSender = isSameSender(m);
        const atBottom = isNearBottom();

        if (!sameSender || !currentGroup) {
            const group = document.createElement('div');
            group.className = 'msg-group ' + (isOwn ? 'msg-group-own' : (m.is_bot ? 'msg-group-bot' : 'msg-group-other'));

            if (!isOwn) {
                const av = document.createElement('div');
                av.className = 'msg-avatar';
                av.innerHTML = avatarHtml(m);
                group.appendChild(av);
            }

            const stack = document.createElement('div');
            stack.className = 'msg-stack';

            if (!isOwn) {
                const author = document.createElement('span');
                author.className = 'msg-author' + (m.is_bot ? ' msg-author-bot' : '');
                author.textContent = m.is_bot ? (m.bot_name || enochTitle) : (m.username || '');
                stack.appendChild(author);
            }

            group.appendChild(stack);
            messages.appendChild(group);
            currentGroup = group;
            currentStack = stack;
        }

        const row = document.createElement('div');
        row.className = 'msg-row' + (isOwn ? ' msg-row-own' : '');
        row.dataset.msgId = m.id;
        row.dataset.userId = m.is_bot ? '' : (m.user_id || '');
        row.dataset.isBot = m.is_bot ? '1' : '0';

        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble ' + (isOwn ? 'msg-bubble-own' : (m.is_bot ? 'msg-bubble-bot' : 'msg-bubble-other'));
        bubble.innerHTML = `<p class="msg-text">${escapeHtml(m.content)}</p>`;

        const time = document.createElement('span');
        time.className = 'msg-time';
        time.textContent = m.timestamp || '';

        row.appendChild(bubble);
        row.appendChild(time);
        currentStack.appendChild(row);

        lastAppendedUserId = m.is_bot ? null : (m.user_id || null);
        lastAppendedIsBot = !!m.is_bot;

        if (m.id > lastMsgId) lastMsgId = m.id;
        markSeen(m.id);

        if (atBottom) scrollToBottom(true);
    }

    /* ── Typing indicator ── */
    function showTypingIndicator() {
        const atBottom = isNearBottom();

        const group = document.createElement('div');
        group.className = 'msg-group msg-group-bot msg-typing';
        group.id = 'enochTyping';

        const av = document.createElement('div');
        av.className = 'msg-avatar';
        av.innerHTML = `<img src="${enochImg}" class="avatar avatar-sm avatar-enoch" alt="Enoch">`;
        group.appendChild(av);

        const stack = document.createElement('div');
        stack.className = 'msg-stack';
        stack.innerHTML = `<div class="msg-row"><div class="msg-bubble msg-bubble-bot"><p class="msg-text typing-dots"><span>.</span><span>.</span><span>.</span></p></div></div>`;
        group.appendChild(stack);
        messages.appendChild(group);

        if (atBottom) scrollToBottom(true);
    }

    function removeTypingIndicator() {
        const el = document.getElementById('enochTyping');
        if (el) el.remove();
    }

    /* ── Send ── */
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
                appendMsg({ ...data.message, user_id: myId });

                if (data.enoch_reply) {
                    showTypingIndicator();
                    const delay = 1500 + Math.random() * 1500;
                    setTimeout(() => {
                        removeTypingIndicator();
                        appendMsg(data.enoch_reply);
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
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    });

    /* ── Polling ── */
    async function poll() {
        try {
            const resp = await fetch(`/hall/poll?after=${lastMsgId}`);
            const data = await resp.json();
            if (data.messages && data.messages.length) {
                for (const m of data.messages) {
                    if (!messages.querySelector(`[data-msg-id="${m.id}"]`)) {
                        appendMsg(m);
                    }
                }
            }
        } catch (e) {
            console.error('Poll failed:', e);
        }
    }

    setInterval(poll, 3000);

    /* ── Emoji Picker ── */
    const emojiToggle = document.getElementById('emojiToggle');
    const emojiPicker = document.getElementById('emojiPicker');
    const emojiTabs = document.getElementById('emojiTabs');
    const emojiGrid = document.getElementById('emojiGrid');

    if (emojiToggle && emojiPicker && emojiGrid) {
        const EMOJI_DATA = [
            { icon: '😀', label: 'Smileys', emojis: '😀😂🤣😅😆😊😎🤓🥳🤔🤨😏😬😐🙄😤😡🤬😈👿💀☠️😱😨😰🥶🥵🤮🤢😴😇🥹🫡🫠' },
            { icon: '👋', label: 'People', emojis: '👋👏🙌🤝👍👎✊👊🤞✌️🤟🫶👀🧠🗣️👑🤴👸🧙‍♂️🤺💂‍♂️🕵️‍♂️🧛‍♂️💪🦾🫵👆👇👈👉🖕🤙' },
            { icon: '♟️', label: 'Chess', emojis: '♟️♞♝♜♛♚⚔️🏰🛡️🗡️🏆🥇🥈🥉🎯🎲🃏🪦📜📖🕯️🔥💀🩸⚰️🪤🏴‍☠️⚡🌑🕸️🕷️🐀' },
            { icon: '❤️', label: 'Symbols', emojis: '❤️🧡💛💚💙💜🖤🤍💔💯✅❌⭕🚫❓❗💢💥💫🔥⚡💎🏳️🏴🚩🎵🎶🔔🔕📢📣' },
            { icon: '😈', label: 'Enoch', emojis: '😈👿💀☠️🕯️🕸️🕷️🐀🦇🪳🪦⚰️🩸🗡️⚔️🔮🧿👁️🫀🧠🖤🪤📜🔥🌑🌒🌘⛓️🪬🫥' },
        ];

        let activeTab = 0;

        function renderTabs() {
            emojiTabs.innerHTML = '';
            EMOJI_DATA.forEach((cat, i) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'emoji-tab' + (i === activeTab ? ' active' : '');
                btn.textContent = cat.icon;
                btn.title = cat.label;
                btn.addEventListener('click', () => {
                    activeTab = i;
                    renderTabs();
                    renderGrid();
                });
                emojiTabs.appendChild(btn);
            });
        }

        function renderGrid() {
            emojiGrid.innerHTML = '';
            const seg = typeof Intl !== 'undefined' && Intl.Segmenter
                ? new Intl.Segmenter('en', { granularity: 'grapheme' }) : null;
            const chars = seg
                ? [...seg.segment(EMOJI_DATA[activeTab].emojis)].map(s => s.segment)
                : [...EMOJI_DATA[activeTab].emojis];
            const seen = new Set();
            chars.forEach(ch => {
                if (ch.length === 1 && ch.charCodeAt(0) < 256) return;
                if (seen.has(ch)) return;
                seen.add(ch);
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'emoji-btn';
                btn.textContent = ch;
                btn.addEventListener('click', () => {
                    const pos = input.selectionStart || input.value.length;
                    input.value = input.value.slice(0, pos) + ch + input.value.slice(pos);
                    input.focus();
                    input.selectionStart = input.selectionEnd = pos + ch.length;
                });
                emojiGrid.appendChild(btn);
            });
        }

        emojiToggle.addEventListener('click', () => {
            const open = emojiPicker.classList.toggle('open');
            emojiToggle.classList.toggle('active', open);
            if (open && !emojiGrid.children.length) {
                renderTabs();
                renderGrid();
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && emojiPicker.classList.contains('open')) {
                emojiPicker.classList.remove('open');
                emojiToggle.classList.remove('active');
            }
        });
    }
});
