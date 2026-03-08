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

    const avatarInput = document.querySelector('.avatar-upload-form input[type="file"]');
    if (avatarInput) {
        avatarInput.addEventListener('change', () => {
            if (avatarInput.files.length) avatarInput.closest('form').submit();
        });
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
