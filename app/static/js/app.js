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

    const deadlineEl = document.querySelector('.deadline-display');
    if (deadlineEl) {
        const iso = deadlineEl.dataset.deadline;
        if (iso) {
            const target = new Date(iso);
            const timerSpan = document.getElementById('deadlineTimer');

            function tick() {
                const now = new Date();
                const diff = target - now;
                if (diff <= 0) {
                    timerSpan.textContent = 'Deadline passed';
                    return;
                }
                const d = Math.floor(diff / 86400000);
                const h = Math.floor((diff % 86400000) / 3600000);
                const m = Math.floor((diff % 3600000) / 60000);
                timerSpan.textContent = `${d}d ${h}h ${m}m remaining`;
            }

            tick();
            setInterval(tick, 60000);
        }
    }
});
