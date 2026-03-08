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

    /* ── Chat unread badge (runs on every page) ── */
    const chatBadge = document.getElementById('chatBadge');
    if (chatBadge) {
        const isHallPage = !!document.getElementById('chatMessages');

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
                } else {
                    chatBadge.classList.remove('active');
                }
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
    window._awardBell = new Audio((window.STATIC_BASE || '/static/') + 'audio/chess/Bell.wav');
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
