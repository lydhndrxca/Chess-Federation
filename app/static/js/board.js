import { Chessground } from 'https://cdn.jsdelivr.net/npm/@lichess-org/chessground@10.1.0/+esm';

const PIECE_URL = 'https://lichess1.org/assets/piece/cburnett/';
const PROMO_ROLES = [
    { letter: 'q', role: 'queen',  label: 'Queen' },
    { letter: 'r', role: 'rook',   label: 'Rook' },
    { letter: 'b', role: 'bishop', label: 'Bishop' },
    { letter: 'n', role: 'knight', label: 'Knight' },
];

function buildDests(legalMoves) {
    const dests = new Map();
    for (const m of legalMoves) {
        if (!dests.has(m.from)) dests.set(m.from, []);
        const arr = dests.get(m.from);
        if (!arr.includes(m.to)) arr.push(m.to);
    }
    return dests;
}

function uciToLastMove(uci) {
    if (!uci || uci.length < 4) return undefined;
    return [uci.substring(0, 2), uci.substring(2, 4)];
}

class ChessBoard {
    constructor(config) {
        this.gameId = config.gameId;
        this.playerColor = config.playerColor;
        this.isPlayerTurn = config.isPlayerTurn;
        this.fen = config.fen;
        this.legalMoves = config.legalMoves || [];
        this.gameOver = config.gameOver || false;
        this.isParticipant = config.isParticipant;
        this.lastMoveUci = config.lastMoveUci || null;
        this.hasCommended = config.hasCommended || false;
        this.pollInterval = null;

        const orientation = this.playerColor === 'black' ? 'black' : 'white';
        const movableColor = (this.isPlayerTurn && !this.gameOver && this.isParticipant)
            ? this.playerColor : undefined;

        this.ground = Chessground(document.getElementById('chessBoard'), {
            fen: this.fen,
            orientation,
            turnColor: this.isPlayerTurn ? this.playerColor : this.otherColor(),
            lastMove: uciToLastMove(this.lastMoveUci),
            coordinates: true,
            viewOnly: this.gameOver || !this.isParticipant,
            animation: { enabled: true, duration: 200 },
            highlight: { lastMove: true, check: true },
            draggable: { enabled: true, showGhost: true },
            selectable: { enabled: true },
            movable: {
                free: false,
                color: movableColor,
                dests: buildDests(this.legalMoves),
                showDests: true,
                events: { after: (orig, dest) => this.onMove(orig, dest) },
            },
            premovable: { enabled: false },
        });

        if (!this.gameOver && !this.isPlayerTurn && this.isParticipant) {
            this.startPolling();
        }

        this.setupResign();
        this.setupToggleMoves();
        this.startDeadlineTimer();
    }

    otherColor() {
        return this.playerColor === 'white' ? 'black' : 'white';
    }

    onMove(orig, dest) {
        this.ground.set({ movable: { color: undefined } });

        const matchingMoves = this.legalMoves.filter(m => m.from === orig && m.to === dest);
        const hasPromo = matchingMoves.some(m => m.promotion);

        if (hasPromo) {
            this.showPromotionDialog(orig, dest);
        } else {
            this.sendMove(`${orig}${dest}`);
        }
    }

    showPromotionDialog(from, to) {
        const modal = document.getElementById('promotionModal');
        const choices = document.getElementById('promotionChoices');
        choices.innerHTML = '';

        const colorPrefix = this.playerColor === 'white' ? 'w' : 'b';

        for (const p of PROMO_ROLES) {
            const btn = document.createElement('button');
            btn.className = 'promo-btn';
            btn.title = p.label;
            const img = document.createElement('img');
            img.src = `${PIECE_URL}${colorPrefix}${p.letter.toUpperCase()}.svg`;
            img.alt = p.label;
            img.style.width = '100%';
            img.style.height = '100%';
            btn.appendChild(img);
            btn.addEventListener('click', () => {
                modal.classList.remove('active');
                this.sendMove(`${from}${to}${p.letter}`);
            });
            choices.appendChild(btn);
        }

        modal.classList.add('active');
    }

    async sendMove(uci) {
        try {
            const resp = await fetch(`/game/${this.gameId}/move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ uci }),
            });
            const data = await resp.json();

            if (data.success) {
                this.fen = data.fen;
                this.lastMoveUci = uci;
                this.isPlayerTurn = false;
                this.legalMoves = [];

                this.ground.set({
                    fen: data.fen,
                    lastMove: uciToLastMove(uci),
                    turnColor: this.otherColor(),
                    movable: { color: undefined, dests: new Map() },
                    viewOnly: false,
                });

                appendMove(data.move_number, data.san, this.playerColor);

                if (data.sequence) updateSequence(data.sequence);
                if (data.can_name_sequence) showNamingPrompt(this.gameId, data.can_name_sequence);

                if (data.game_over) {
                    this.gameOver = true;
                    this.ground.set({ viewOnly: true });
                    showResult(data.result, data.result_type, data.rating_change);
                    if (data.show_commend && !this.hasCommended) showCommendPrompt(this.gameId);
                } else {
                    updateTurn(false);
                    this.startPolling();
                }
            } else {
                this.ground.set({
                    fen: this.fen,
                    lastMove: uciToLastMove(this.lastMoveUci),
                    movable: {
                        color: this.playerColor,
                        dests: buildDests(this.legalMoves),
                    },
                });
                console.error('Move rejected:', data.error);
            }
        } catch (err) {
            console.error('Move failed:', err);
        }
    }

    startPolling() {
        this.stopPolling();
        this.pollInterval = setInterval(() => this.poll(), 3000);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    async poll() {
        try {
            const resp = await fetch(`/game/${this.gameId}/state`);
            const data = await resp.json();

            if (data.fen !== this.fen) {
                this.fen = data.fen;
                if (data.last_move) this.lastMoveUci = data.last_move.uci;

                this.ground.set({
                    fen: data.fen,
                    lastMove: data.last_move ? [data.last_move.uci.substring(0, 2), data.last_move.uci.substring(2, 4)] : undefined,
                    turnColor: data.turn,
                });

                if (data.last_move) {
                    appendMove(null, data.last_move.san, data.last_move.color);
                }
                if (data.sequence) updateSequence(data.sequence);

                if (data.status === 'completed' || data.status === 'forfeited') {
                    this.gameOver = true;
                    this.stopPolling();
                    this.ground.set({ viewOnly: true });
                    showResult(data.result, data.result_type, data.rating_change);
                    if (!this.hasCommended) showCommendPrompt(this.gameId);
                    return;
                }

                if (data.is_your_turn) {
                    this.isPlayerTurn = true;
                    this.legalMoves = data.legal_moves;
                    this.stopPolling();

                    this.ground.set({
                        movable: {
                            color: this.playerColor,
                            dests: buildDests(data.legal_moves),
                        },
                        viewOnly: false,
                    });

                    updateTurn(true);
                }
            }
        } catch (err) {
            console.error('Poll error:', err);
        }
    }

    setupResign() {
        const btn = document.getElementById('resignBtn');
        if (!btn) return;
        btn.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to resign?')) return;
            try {
                const resp = await fetch(`/game/${this.gameId}/resign`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                const data = await resp.json();
                if (data.success) {
                    this.gameOver = true;
                    this.stopPolling();
                    this.ground.set({ viewOnly: true });
                    showResult(data.result, data.result_type, data.rating_change);
                    if (data.show_commend && !this.hasCommended) showCommendPrompt(this.gameId);
                }
            } catch (err) {
                console.error('Resign failed:', err);
            }
        });
    }

    setupToggleMoves() {
        const btn = document.getElementById('toggleMovesBtn');
        const panel = document.getElementById('moveListPanel');
        if (!btn || !panel) return;
        btn.addEventListener('click', () => {
            panel.classList.toggle('open');
            btn.classList.toggle('active');
        });
    }

    startDeadlineTimer() {
        const el = document.getElementById('deadlineTimer');
        if (!el) return;
        const dl = el.dataset.deadline;
        if (!dl) return;
        const deadline = new Date(dl);
        const tick = () => {
            const diff = deadline - Date.now();
            if (diff <= 0) { el.textContent = 'Time up'; return; }
            const h = Math.floor(diff / 3600000);
            const m = Math.floor((diff % 3600000) / 60000);
            if (h >= 24) {
                const d = Math.floor(h / 24);
                el.textContent = d === 1 ? '1 day' : `${d} days`;
            } else {
                el.textContent = `${h}h ${m}m`;
            }
        };
        tick();
        setInterval(tick, 60000);
    }
}

/* ── UI helpers (unchanged logic) ── */

function appendMove(moveNum, san, color) {
    const strip = document.getElementById('movesStrip');
    if (strip) {
        const empty = strip.querySelector('.gv-ms-empty');
        if (empty) empty.remove();
        if (color === 'white') {
            const num = moveNum || (strip.querySelectorAll('.gv-mn').length + 1);
            strip.insertAdjacentHTML('beforeend',
                `<span class="gv-mn">${num}.</span><span class="gv-ms">${san}</span>`);
        } else {
            strip.insertAdjacentHTML('beforeend',
                `<span class="gv-ms gv-ms-b">${san}</span>`);
        }
        strip.scrollLeft = strip.scrollWidth;
    }

    const list = document.getElementById('moveList');
    if (!list) return;

    if (color === 'white') {
        const row = document.createElement('div');
        row.className = 'move-row';
        const num = moveNum || Math.ceil((list.querySelectorAll('.move-san.white-move').length + 1));
        row.innerHTML = `<span class="move-num">${num}.</span><span class="move-san white-move">${san}</span>`;
        list.appendChild(row);
    } else {
        const rows = list.querySelectorAll('.move-row');
        const lastRow = rows[rows.length - 1];
        if (lastRow && !lastRow.querySelector('.black-move')) {
            const span = document.createElement('span');
            span.className = 'move-san black-move';
            span.textContent = san;
            lastRow.appendChild(span);
        } else {
            const row = document.createElement('div');
            row.className = 'move-row';
            row.innerHTML = `<span class="move-num">...</span><span class="move-san black-move">${san}</span>`;
            list.appendChild(row);
        }
    }

    list.scrollTop = list.scrollHeight;
}

function updateTurn(isYourTurn) {
    const el = document.getElementById('turnIndicator');
    if (!el) return;
    el.innerHTML = isYourTurn
        ? '<span class="turn-yours">Your turn</span>'
        : '<span class="turn-waiting">Waiting for opponent</span>';
}

function showResult(result, resultType, ratingChange) {
    const el = document.getElementById('turnIndicator');
    if (el) {
        let html = `<span class="game-over-text">${result} — ${resultType}</span>`;
        if (ratingChange != null) {
            const sign = ratingChange >= 0 ? '+' : '';
            const cls = ratingChange >= 0 ? 'rating-up' : 'rating-down';
            html += `<span class="rating-impact ${cls}">${sign}${ratingChange.toFixed(1)} rating</span>`;
        }
        el.innerHTML = html;
    }
    const btn = document.getElementById('resignBtn');
    if (btn) btn.style.display = 'none';
}

function updateSequence(seq) {
    const bar = document.getElementById('sequenceBar');
    if (!bar || !seq) return;
    bar.innerHTML =
        `<span class="gv-seq-category">${seq.category}</span>` +
        `<span class="gv-seq-name">${seq.name}</span>` +
        `<span class="gv-seq-creator">by ${seq.creator}</span>`;
    bar.style.display = '';
}

function showNamingPrompt(gameId, info) {
    const modal = document.getElementById('namingModal');
    if (!modal) return;
    document.getElementById('namingCategory').textContent = info.category.toLowerCase();
    modal.classList.add('active');

    const input = document.getElementById('namingInput');
    const submitBtn = document.getElementById('namingSubmit');
    const skipBtn = document.getElementById('namingSkip');
    const overlay = document.getElementById('namingOverlay');

    input.value = '';
    input.focus();

    const close = () => { modal.classList.remove('active'); };
    skipBtn.onclick = close;
    overlay.onclick = close;

    submitBtn.onclick = async () => {
        const name = input.value.trim();
        if (!name) { input.focus(); return; }
        submitBtn.disabled = true;
        try {
            const resp = await fetch(`/game/${gameId}/name-sequence`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    moves_key: info.moves_key,
                    half_moves: info.half_moves,
                    category: info.category,
                }),
            });
            const data = await resp.json();
            if (data.success) {
                updateSequence(data.sequence);
                close();
            } else {
                input.value = '';
                input.placeholder = data.error || 'Try again…';
            }
        } catch (e) {
            console.error('Naming failed:', e);
        }
        submitBtn.disabled = false;
    };

    input.onkeydown = (e) => { if (e.key === 'Enter') submitBtn.click(); };
}

function showCommendPrompt(gameId) {
    const modal = document.getElementById('commendModal');
    if (!modal) return;

    let selectedKind = null;
    const typeBtns = modal.querySelectorAll('.commend-type-btn');
    const textarea = document.getElementById('commendText');
    const submitBtn = document.getElementById('commendSubmit');
    const skipBtn = document.getElementById('commendSkip');
    const overlay = document.getElementById('commendOverlay');

    textarea.value = '';
    submitBtn.disabled = true;

    const close = () => { modal.classList.remove('active'); };
    skipBtn.onclick = close;
    overlay.onclick = close;

    typeBtns.forEach(btn => {
        btn.classList.remove('selected');
        btn.onclick = () => {
            typeBtns.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedKind = btn.dataset.kind;
            submitBtn.disabled = false;
            textarea.focus();
        };
    });

    submitBtn.onclick = async () => {
        const text = textarea.value.trim();
        if (!selectedKind || !text) {
            textarea.focus();
            return;
        }
        submitBtn.disabled = true;
        try {
            const resp = await fetch(`/game/${gameId}/commend`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ kind: selectedKind, text }),
            });
            const data = await resp.json();
            if (data.success) close();
            else {
                textarea.value = '';
                textarea.placeholder = data.error || 'Try again…';
            }
        } catch (e) {
            console.error('Commend failed:', e);
        }
        submitBtn.disabled = false;
    };

    setTimeout(() => modal.classList.add('active'), 600);
}

/* ── Init ── */

const cfg = window.GAME_CONFIG;
if (cfg) new ChessBoard(cfg);
