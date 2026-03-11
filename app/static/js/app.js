document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');
    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('open');
            toggle.classList.toggle('active');
        });
    }

    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => {
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 300);
        }, 4000);
    });

    const avatarInput = document.querySelector('.avatar-form input[type="file"]');
    if (avatarInput) {
        avatarInput.addEventListener('change', () => {
            if (avatarInput.files.length) avatarInput.closest('form').submit();
        });
    }

    /* ═══════════════════════════════════════════════════════
       NOTIFICATION SYSTEM
       ═══════════════════════════════════════════════════════ */

    const NOTIF_PREF_KEY = 'cfNotifPref';
    const NOTIF_PROMPTED_KEY = 'cfNotifPrompted';

    function getNotifPref() {
        return localStorage.getItem(NOTIF_PREF_KEY);
    }

    function notifAllowed() {
        return getNotifPref() === 'granted' &&
               typeof Notification !== 'undefined' &&
               Notification.permission === 'granted';
    }

    function showNotif(title, body, tag, url) {
        if (!notifAllowed() || document.hasFocus()) return;
        try {
            const n = new Notification(title, {
                body: body,
                icon: (window.STATIC_BASE || '/static/') + 'img/enoch.png',
                tag: tag,
                renotify: true,
            });
            if (url) {
                n.addEventListener('click', () => {
                    window.focus();
                    window.location.href = url;
                    n.close();
                });
            }
            setTimeout(() => n.close(), 8000);
        } catch (e) { /* ignore */ }
    }

    const ENOCH_NOTIF_LINES = [
        "I can send you notifications — a small alert on your device when it is your turn to move, or when someone mentions you in the chat. I have installed a bell on a wire down here for this very purpose. Allow it?",
        "Would you like notifications? I will alert your device when the board demands your move, or when your name appears in the Hall. There is a copper pipe I can whisper through. You will hear it.",
        "I can notify you — push a message to your screen when it is your turn, or when someone says your name in the chat. I keep watch always. Allow me to tap the glass when it matters?",
        "Enable notifications? I will send an alert to your device when it is your move, or when your name surfaces in conversation. The spiders have agreed to carry these messages. Permit this arrangement.",
        "Turn on notifications? I can alert you when it is your turn to play, or when someone mentions you in the chat. A rusted thimble and damp string — but it works. Say the word.",
    ];

    function showNotifPrompt() {
        if (typeof Notification === 'undefined') return;
        if (localStorage.getItem(NOTIF_PROMPTED_KEY)) return;
        if (Notification.permission === 'granted') {
            localStorage.setItem(NOTIF_PREF_KEY, 'granted');
            localStorage.setItem(NOTIF_PROMPTED_KEY, '1');
            return;
        }
        if (Notification.permission === 'denied') {
            localStorage.setItem(NOTIF_PROMPTED_KEY, '1');
            return;
        }

        const line = ENOCH_NOTIF_LINES[Math.floor(Math.random() * ENOCH_NOTIF_LINES.length)];
        const imgSrc = (window.STATIC_BASE || '/static/') + 'img/enoch.png';

        const overlay = document.createElement('div');
        overlay.className = 'notif-prompt-overlay';

        const modal = document.createElement('div');
        modal.className = 'notif-prompt-modal';
        modal.innerHTML = `
            <img src="${imgSrc}" class="notif-prompt-avatar" alt="Enoch">
            <p class="notif-prompt-enoch-text">${line}</p>
            <div class="notif-prompt-actions">
                <button class="notif-prompt-yes" id="notifYes">Allow Enoch's Alerts</button>
                <button class="notif-prompt-no" id="notifNo">Leave me in silence</button>
            </div>`;

        document.body.appendChild(overlay);
        document.body.appendChild(modal);
        requestAnimationFrame(() => {
            overlay.classList.add('active');
            modal.classList.add('active');
        });

        function dismiss() {
            overlay.classList.remove('active');
            modal.classList.remove('active');
            setTimeout(() => { overlay.remove(); modal.remove(); }, 400);
        }

        document.getElementById('notifYes').addEventListener('click', () => {
            Notification.requestPermission().then(perm => {
                localStorage.setItem(NOTIF_PREF_KEY, perm);
                localStorage.setItem(NOTIF_PROMPTED_KEY, '1');
                dismiss();
            });
        });
        document.getElementById('notifNo').addEventListener('click', () => {
            localStorage.setItem(NOTIF_PREF_KEY, 'dismissed');
            localStorage.setItem(NOTIF_PROMPTED_KEY, '1');
            dismiss();
        });
        overlay.addEventListener('click', () => {
            localStorage.setItem(NOTIF_PREF_KEY, 'dismissed');
            localStorage.setItem(NOTIF_PROMPTED_KEY, '1');
            dismiss();
        });
    }

    setTimeout(showNotifPrompt, 2500);

    /* ── Chat unread badge + notifications (runs on every page) ── */
    const chatBadge = document.getElementById('chatBadge');
    let prevUnreadCount = 0;
    let prevMentionCount = 0;

    if (chatBadge) {
        const isHallPage = !!document.getElementById('chatMessages');
        const isSPChat = !!document.getElementById('spChatMessages');

        function getLastSeenChat() {
            return parseInt(localStorage.getItem('chatLastSeen') || '0', 10);
        }

        async function checkUnread() {
            try {
                const resp = await fetch(`/hall/unread?after=${getLastSeenChat()}`);
                const data = await resp.json();
                if (data.count > 0) {
                    chatBadge.textContent = data.count > 99 ? '99+' : data.count;
                    chatBadge.classList.add('active');

                    const newMentions = (data.mentions || 0);
                    if (newMentions > prevMentionCount) {
                        showNotif(
                            'You were mentioned in the Hall',
                            'Someone said your name in Federation Hall',
                            'cf-mention',
                            '/hall'
                        );
                    } else if (data.count > prevUnreadCount && !isHallPage && !isSPChat) {
                        showNotif(
                            'New message in Federation Hall',
                            data.count === 1 ? '1 unread message' : data.count + ' unread messages',
                            'cf-chat',
                            '/hall'
                        );
                    }
                    prevMentionCount = newMentions;
                } else {
                    chatBadge.classList.remove('active');
                    prevMentionCount = 0;
                }
                prevUnreadCount = data.count;
                if (isHallPage && data.latest_id) {
                    localStorage.setItem('chatLastSeen', String(data.latest_id));
                    chatBadge.classList.remove('active');
                }
            } catch (e) { /* ignore */ }
        }

        if (isHallPage) {
            const existing = document.querySelectorAll('.chat-msg');
            if (existing.length) {
                const last = existing[existing.length - 1].dataset.msgId;
                if (last) localStorage.setItem('chatLastSeen', last);
            }
            chatBadge.classList.remove('active');
        }

        checkUnread();
        setInterval(checkUnread, 15000);
    }

    /* ── Turn notifications (runs on every page) ── */
    let prevTurnCount = -1;
    const isGamePage = !!document.getElementById('chessBoard');

    async function checkTurns() {
        try {
            const resp = await fetch('/api/my-turns');
            const data = await resp.json();
            if (prevTurnCount >= 0 && data.count > prevTurnCount && !isGamePage) {
                const newest = data.turns[0];
                showNotif(
                    'Your turn!',
                    'It\'s your move against ' + newest.opponent,
                    'cf-turn-' + newest.game_id,
                    '/game/' + newest.game_id
                );
            }
            prevTurnCount = data.count;
        } catch (e) { /* ignore */ }
    }
    checkTurns();
    setInterval(checkTurns, 20000);

    /* ── Enoch daily login greeting (runs once per day) ── */
    if (chatBadge) {
        const today = new Date().toDateString();
        const lastGreeting = localStorage.getItem('enochGreetingDate');
        if (lastGreeting !== today) {
            setTimeout(async () => {
                try {
                    const resp = await fetch('/hall/login-greeting');
                    const data = await resp.json();
                    if (data.greeting) {
                        localStorage.setItem('enochGreetingDate', today);
                        showEnochGreeting(data.greeting, data.audio_url);
                    }
                } catch (e) { /* ignore */ }
            }, 1500);
        }
    }

    function showEnochGreeting(text, audioUrl) {
        const toast = document.createElement('div');
        toast.className = 'enoch-login-toast';
        toast.innerHTML = `
            <img src="${window.STATIC_BASE || '/static/'}img/enoch.png" class="enoch-login-sigil" alt="Enoch">
            <div class="enoch-login-body">
                <div class="enoch-login-label">Enoch mutters…</div>
                <div class="enoch-login-text">${text}</div>
            </div>
            <button class="enoch-login-close" aria-label="Dismiss">&times;</button>`;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('active'));

        toast.querySelector('.enoch-login-close').addEventListener('click', () => {
            toast.classList.remove('active');
            setTimeout(() => toast.remove(), 400);
        });

        if (audioUrl) {
            const playGreeting = (audio) => {
                audio.play().catch(() => {});
                audio.addEventListener('ended', () => {
                    setTimeout(() => {
                        toast.classList.remove('active');
                        setTimeout(() => toast.remove(), 400);
                    }, 1500);
                });
            };
            if (window.EnochCache) {
                window.EnochCache.getAudio(audioUrl).then(playGreeting).catch(() => {});
            } else {
                playGreeting(new Audio(audioUrl));
            }
        } else {
            setTimeout(() => {
                toast.classList.remove('active');
                setTimeout(() => toast.remove(), 400);
            }, 8000);
        }
    }

    /* ── Universal Award Popup (available globally) ── */
    window._awardBell = new Audio((window.AUDIO_CDN || (window.STATIC_BASE || '/static/') + 'audio/') + 'chess/Bell.wav');
    window._awardBell.preload = 'auto';

    window.showAwardItem = function(item) {
        return new Promise(resolve => {
            const modal = document.getElementById('awardModal');
            if (!modal) { resolve(); return; }

            document.getElementById('awardName').textContent = item.name;
            document.getElementById('awardCollection').textContent = item.collection;
            document.getElementById('awardDesc').textContent = item.desc;
            document.getElementById('awardQuote').textContent = '"' + item.enoch + '"';

            modal.classList.add('active');
            if (window._awardBell) {
                window._awardBell.currentTime = 0;
                window._awardBell.play().catch(() => {});
            }

            const dismiss = document.getElementById('awardDismiss');
            dismiss.onclick = () => {
                modal.classList.remove('active');
                resolve();
            };
        });
    };

    window.showAwardQueue = async function(items) {
        const counter = document.getElementById('awardCounter');
        for (let i = 0; i < items.length; i++) {
            if (counter && items.length > 1) {
                counter.textContent = (i + 1) + ' of ' + items.length;
                counter.style.display = '';
            } else if (counter) {
                counter.style.display = 'none';
            }
            await window.showAwardItem(items[i]);
        }
    };

});
