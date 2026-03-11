document.addEventListener('DOMContentLoaded', () => {
    const cfg = window.CHAT_CONFIG || {};
    const myId = cfg.currentUserId;
    const myName = cfg.currentUsername || '';
    const enochTitle = cfg.enochTitle || 'Enoch';
    const enochImg = cfg.enochImg || '/static/img/enoch.png';
    const staticBase = cfg.staticBase || '/static/';
    const uploadBase = cfg.uploadBase || staticBase + 'uploads/chat/';

    const chatBody = document.getElementById('chatBody');
    const messages = document.getElementById('chatMessages');
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');
    const scrollFab = document.getElementById('chatScrollFab');
    const imgInput = document.getElementById('chatImageInput');
    if (!messages || !input) return;

    let lastMsgId = 0;
    const existing = messages.querySelectorAll('.msg-row');
    if (existing.length) lastMsgId = parseInt(existing[existing.length - 1].dataset.msgId) || 0;

    let replyToId = null;
    let replyToName = '';

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
        if (smooth) chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });
        else chatBody.scrollTop = chatBody.scrollHeight;
    }
    if (chatBody) chatBody.addEventListener('scroll', () => {
        if (scrollFab) scrollFab.classList.toggle('visible', !isNearBottom());
    });
    if (scrollFab) scrollFab.addEventListener('click', () => scrollToBottom(true));

    /* ── Helpers ── */
    function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

    function avatarHtml(m) {
        if (m.is_bot) return `<img src="${enochImg}" class="avatar avatar-sm avatar-enoch" alt="Enoch">`;
        if (m.avatar) return `<img src="${staticBase}uploads/avatars/${m.avatar}" class="avatar avatar-sm" alt="">`;
        return `<span class="avatar avatar-sm avatar-placeholder">${(m.username || '?')[0].toUpperCase()}</span>`;
    }

    /* ── Message grouping state ── */
    let lastAppendedUserId = null;
    let lastAppendedIsBot = false;
    let currentGroup = null;
    let currentStack = null;

    const groups = messages.querySelectorAll('.msg-group');
    if (groups.length) {
        const last = groups[groups.length - 1];
        if (last.classList.contains('msg-group-own')) { lastAppendedUserId = myId; lastAppendedIsBot = false; }
        else if (last.classList.contains('msg-group-bot')) { lastAppendedIsBot = true; lastAppendedUserId = null; }
        else { lastAppendedIsBot = false; const row = last.querySelector('.msg-row'); lastAppendedUserId = row ? parseInt(row.dataset.userId) || null : null; }
        currentGroup = last;
        currentStack = last.querySelector('.msg-stack');
    }

    function isSameSender(m) {
        if (m.is_bot) return lastAppendedIsBot;
        return !lastAppendedIsBot && lastAppendedUserId === (m.user_id || null);
    }

    /* ── Reaction rendering ── */
    function renderReactions(reactions, msgId) {
        if (!reactions || !Object.keys(reactions).length) return '';
        let html = '<div class="msg-reactions">';
        for (const [emoji, users] of Object.entries(reactions)) {
            const isMine = users.some(u => u.user_id === myId);
            const names = users.map(u => u.username || '?').join(', ');
            html += `<button class="msg-reaction-pill${isMine ? ' msg-reaction-mine' : ''}" data-emoji="${esc(emoji)}" data-msg-id="${msgId}" title="${esc(names)}">${emoji}<span class="msg-reaction-count">${users.length > 1 ? users.length : ''}</span></button>`;
        }
        html += '</div>';
        return html;
    }

    /* ── Append message ── */
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
        row.dataset.content = m.content || '';

        let replyHtml = '';
        if (m.reply_to) {
            replyHtml = `<div class="msg-reply-preview" data-reply-id="${m.reply_to.id}"><span class="msg-reply-author">${esc(m.reply_to.username || 'Enoch')}</span><span class="msg-reply-text">${esc(m.reply_to.content)}</span></div>`;
        }

        const isLong = (m.content || '').length > 200;
        let imgHtml = '';
        if (m.image) imgHtml = `<img src="${uploadBase}${m.image}" class="msg-image" alt="image" loading="lazy">`;

        const bubbleClass = isOwn ? 'msg-bubble-own' : (m.is_bot ? 'msg-bubble-bot' : 'msg-bubble-other');
        const editedTag = m.edited ? '<span class="msg-edited">(edited)</span>' : '';

        row.innerHTML = `${replyHtml}<div class="msg-bubble ${bubbleClass}">${imgHtml}<p class="msg-text${isLong ? ' msg-text-long' : ''}">${esc(m.content)}</p>${isLong ? '<button class="msg-expand-btn" type="button">Show more</button>' : ''}${editedTag}</div>${renderReactions(m.reactions, m.id)}<span class="msg-time">${m.timestamp || ''}</span>`;

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
    function removeTypingIndicator() { const el = document.getElementById('enochTyping'); if (el) el.remove(); }

    /* ── Send ── */
    async function send() {
        const text = input.value.trim();
        if (!text) return;
        input.value = '';
        const body = { content: text };
        if (replyToId) { body.reply_to_id = replyToId; clearReply(); }
        try {
            const resp = await fetch('/hall/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            const data = await resp.json();
            if (data.success) {
                appendMsg({ ...data.message, user_id: myId });
                if (data.enoch_reply) {
                    showTypingIndicator();
                    setTimeout(() => { removeTypingIndicator(); appendMsg(data.enoch_reply); }, 1500 + Math.random() * 1500);
                }
                if (data.earned_items && data.earned_items.length && window.showAwardQueue) window.showAwardQueue(data.earned_items);
            }
        } catch (e) { console.error('Send failed:', e); }
    }
    sendBtn.addEventListener('click', send);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

    /* ── Image upload ── */
    if (imgInput) {
        imgInput.addEventListener('change', async () => {
            const file = imgInput.files[0];
            if (!file) return;
            const fd = new FormData();
            fd.append('image', file);
            fd.append('content', input.value.trim() || '[image]');
            if (replyToId) { fd.append('reply_to_id', replyToId); clearReply(); }
            imgInput.value = '';
            try {
                const resp = await fetch('/hall/upload-image', { method: 'POST', body: fd });
                const data = await resp.json();
                if (data.success) { input.value = ''; appendMsg({ ...data.message, user_id: myId }); }
            } catch (e) { console.error('Upload failed:', e); }
        });
    }

    /* ── Paste image ── */
    input.addEventListener('paste', (e) => {
        const items = e.clipboardData?.items;
        if (!items) return;
        for (const item of items) {
            if (item.type.startsWith('image/')) {
                e.preventDefault();
                const file = item.getAsFile();
                const fd = new FormData();
                fd.append('image', file, 'pasted.png');
                fd.append('content', input.value.trim() || '[image]');
                if (replyToId) { fd.append('reply_to_id', replyToId); clearReply(); }
                fetch('/hall/upload-image', { method: 'POST', body: fd })
                    .then(r => r.json())
                    .then(data => { if (data.success) { input.value = ''; appendMsg({ ...data.message, user_id: myId }); } })
                    .catch(e => console.error('Paste upload failed:', e));
                break;
            }
        }
    });

    /* ── Polling ── */
    async function poll() {
        try {
            const resp = await fetch(`/hall/poll?after=${lastMsgId}`);
            const data = await resp.json();
            if (data.messages && data.messages.length) {
                for (const m of data.messages) {
                    if (!messages.querySelector(`[data-msg-id="${m.id}"]`)) appendMsg(m);
                }
            }
        } catch (e) { console.error('Poll failed:', e); }
    }
    setInterval(poll, 3000);

    /* ── Reply banner ── */
    const replyBanner = document.getElementById('replyBanner');
    const replyBannerName = document.getElementById('replyBannerName');
    const replyBannerPreview = document.getElementById('replyBannerPreview');
    const replyBannerClose = document.getElementById('replyBannerClose');

    function setReply(msgId, name, preview) {
        replyToId = msgId;
        replyToName = name;
        if (replyBanner) { replyBanner.style.display = 'flex'; replyBannerName.textContent = name; replyBannerPreview.textContent = preview.slice(0, 80); }
        input.focus();
    }
    function clearReply() {
        replyToId = null;
        replyToName = '';
        if (replyBanner) replyBanner.style.display = 'none';
    }
    if (replyBannerClose) replyBannerClose.addEventListener('click', clearReply);

    /* ── Long-press / context menu ── */
    const ctxMenu = document.getElementById('msgContextMenu');
    const ctxReply = document.getElementById('ctxReply');
    const ctxEdit = document.getElementById('ctxEdit');
    const ctxDelete = document.getElementById('ctxDelete');
    const ctxEmojiMore = document.getElementById('ctxEmojiMore');
    let ctxMsgId = null;
    let ctxMsgRow = null;
    let longPressTimer = null;

    function showCtxMenu(row, x, y) {
        ctxMsgRow = row;
        ctxMsgId = parseInt(row.dataset.msgId);
        const isOwn = !parseInt(row.dataset.isBot) && parseInt(row.dataset.userId) === myId;
        ctxEdit.style.display = isOwn ? '' : 'none';
        ctxDelete.style.display = isOwn ? '' : 'none';
        ctxMenu.style.display = '';
        const vw = window.innerWidth, vh = window.innerHeight;
        let left = Math.min(x, vw - 240), top = Math.min(y, vh - 160);
        if (left < 8) left = 8;
        if (top < 8) top = 8;
        ctxMenu.style.left = left + 'px';
        ctxMenu.style.top = top + 'px';
    }

    function hideCtxMenu() {
        ctxMenu.style.display = 'none';
        ctxMsgId = null;
        ctxMsgRow = null;
    }

    messages.addEventListener('pointerdown', (e) => {
        const row = e.target.closest('.msg-row');
        if (!row || e.target.closest('.msg-reaction-pill') || e.target.closest('.msg-expand-btn') || e.target.closest('.msg-reply-preview')) return;
        longPressTimer = setTimeout(() => {
            longPressTimer = null;
            showCtxMenu(row, e.clientX, e.clientY);
        }, 500);
    });
    messages.addEventListener('pointerup', () => { if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; } });
    messages.addEventListener('pointermove', () => { if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; } });
    messages.addEventListener('pointercancel', () => { if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; } });

    messages.addEventListener('contextmenu', (e) => {
        const row = e.target.closest('.msg-row');
        if (row) { e.preventDefault(); showCtxMenu(row, e.clientX, e.clientY); }
    });

    document.addEventListener('click', (e) => {
        if (ctxMenu.style.display !== 'none' && !ctxMenu.contains(e.target)) hideCtxMenu();
    });

    /* ── Context menu actions ── */
    document.querySelectorAll('.msg-ctx-emoji').forEach(btn => {
        if (btn.id === 'ctxEmojiMore') return;
        btn.addEventListener('click', () => {
            if (!ctxMsgId) return;
            sendReaction(ctxMsgId, btn.dataset.emoji);
            hideCtxMenu();
        });
    });

    if (ctxEmojiMore) {
        ctxEmojiMore.addEventListener('click', () => {
            hideCtxMenu();
            if (emojiPicker) { emojiPicker.classList.add('open'); emojiToggle.classList.add('active'); }
        });
    }

    ctxReply.addEventListener('click', () => {
        if (!ctxMsgRow) return;
        const isBot = ctxMsgRow.dataset.isBot === '1';
        const name = isBot ? 'Enoch' : (ctxMsgRow.querySelector('.msg-text')?.closest('.msg-group')?.querySelector('.msg-author')?.textContent || myName);
        setReply(ctxMsgId, name, ctxMsgRow.dataset.content || '');
        hideCtxMenu();
    });

    ctxEdit.addEventListener('click', () => {
        if (!ctxMsgRow) return;
        const bubble = ctxMsgRow.querySelector('.msg-bubble');
        const textEl = ctxMsgRow.querySelector('.msg-text');
        if (!bubble || !textEl) { hideCtxMenu(); return; }
        const oldText = ctxMsgRow.dataset.content || textEl.textContent;
        const editInput = document.createElement('input');
        editInput.type = 'text';
        editInput.className = 'msg-edit-input';
        editInput.value = oldText;
        editInput.maxLength = 2000;
        textEl.style.display = 'none';
        bubble.insertBefore(editInput, textEl);
        editInput.focus();
        const id = ctxMsgId;

        function finishEdit() {
            const newText = editInput.value.trim();
            editInput.remove();
            textEl.style.display = '';
            if (newText && newText !== oldText) {
                fetch('/hall/edit', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message_id: id, content: newText }) })
                    .then(r => r.json()).then(d => {
                        if (d.success) {
                            textEl.textContent = newText;
                            ctxMsgRow.dataset.content = newText;
                            if (!bubble.querySelector('.msg-edited')) {
                                const ed = document.createElement('span');
                                ed.className = 'msg-edited';
                                ed.textContent = '(edited)';
                                bubble.appendChild(ed);
                            }
                        }
                    });
            }
        }
        editInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') finishEdit(); if (e.key === 'Escape') { editInput.remove(); textEl.style.display = ''; } });
        editInput.addEventListener('blur', finishEdit);
        hideCtxMenu();
    });

    ctxDelete.addEventListener('click', () => {
        if (!ctxMsgId) return;
        const id = ctxMsgId;
        const row = ctxMsgRow;
        hideCtxMenu();
        if (!confirm('Delete this message?')) return;
        fetch('/hall/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message_id: id }) })
            .then(r => r.json()).then(d => {
                if (d.success && row) {
                    row.style.opacity = '0';
                    setTimeout(() => row.remove(), 300);
                }
            });
    });

    /* ── Reaction click (inline pill) ── */
    messages.addEventListener('click', (e) => {
        const pill = e.target.closest('.msg-reaction-pill');
        if (pill) { sendReaction(parseInt(pill.dataset.msgId), pill.dataset.emoji); return; }
        const expandBtn = e.target.closest('.msg-expand-btn');
        if (expandBtn) {
            const text = expandBtn.previousElementSibling;
            if (text) text.classList.toggle('msg-text-long');
            expandBtn.textContent = text && text.classList.contains('msg-text-long') ? 'Show more' : 'Show less';
            return;
        }
        const replyPrev = e.target.closest('.msg-reply-preview');
        if (replyPrev) {
            const target = messages.querySelector(`[data-msg-id="${replyPrev.dataset.replyId}"]`);
            if (target) { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); target.classList.add('msg-row-highlight'); setTimeout(() => target.classList.remove('msg-row-highlight'), 1500); }
        }
    });

    async function sendReaction(msgId, emoji) {
        try {
            const resp = await fetch('/hall/react', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message_id: msgId, emoji }) });
            const data = await resp.json();
            const row = messages.querySelector(`[data-msg-id="${msgId}"]`);
            if (!row) return;
            let container = row.querySelector('.msg-reactions');
            if (data.action === 'added') {
                if (!container) { container = document.createElement('div'); container.className = 'msg-reactions'; const timeEl = row.querySelector('.msg-time'); row.insertBefore(container, timeEl); }
                let pill = container.querySelector(`[data-emoji="${emoji}"]`);
                if (!pill) {
                    pill = document.createElement('button');
                    pill.className = 'msg-reaction-pill msg-reaction-mine';
                    pill.dataset.emoji = emoji;
                    pill.dataset.msgId = msgId;
                    pill.innerHTML = `${emoji}<span class="msg-reaction-count"></span>`;
                    container.appendChild(pill);
                } else { pill.classList.add('msg-reaction-mine'); }
            } else if (data.action === 'removed') {
                if (container) {
                    const pill = container.querySelector(`[data-emoji="${emoji}"]`);
                    if (pill) { pill.classList.remove('msg-reaction-mine'); }
                }
            }
        } catch (e) { console.error('Reaction failed:', e); }
    }

    /* ── Expand/collapse long messages (server-rendered) ── */
    document.querySelectorAll('.msg-expand-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.previousElementSibling;
            if (text) text.classList.toggle('msg-text-long');
            btn.textContent = text && text.classList.contains('msg-text-long') ? 'Show more' : 'Show less';
        });
    });

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
                btn.addEventListener('click', () => { activeTab = i; renderTabs(); renderGrid(); });
                emojiTabs.appendChild(btn);
            });
        }

        function renderGrid() {
            emojiGrid.innerHTML = '';
            const seg = typeof Intl !== 'undefined' && Intl.Segmenter ? new Intl.Segmenter('en', { granularity: 'grapheme' }) : null;
            const chars = seg ? [...seg.segment(EMOJI_DATA[activeTab].emojis)].map(s => s.segment) : [...EMOJI_DATA[activeTab].emojis];
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
            if (open && !emojiGrid.children.length) { renderTabs(); renderGrid(); }
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && emojiPicker.classList.contains('open')) { emojiPicker.classList.remove('open'); emojiToggle.classList.remove('active'); }
        });
    }
});
