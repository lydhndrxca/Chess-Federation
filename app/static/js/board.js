const PIECE_CHARS = {
    'K': '\u265A', 'Q': '\u265B', 'R': '\u265C', 'B': '\u265D', 'N': '\u265E', 'P': '\u265F',
    'k': '\u265A', 'q': '\u265B', 'r': '\u265C', 'b': '\u265D', 'n': '\u265E', 'p': '\u265F',
};

class ChessBoard {
    constructor(config) {
        this.container = document.getElementById('chessBoard');
        this.gameId = config.gameId;
        this.playerColor = config.playerColor;
        this.isPlayerTurn = config.isPlayerTurn;
        this.fen = config.fen;
        this.legalMoves = config.legalMoves || [];
        this.gameOver = config.gameOver || false;
        this.isParticipant = config.isParticipant;
        this.lastMoveUci = config.lastMoveUci || null;
        this.selectedSquare = null;
        this.flipped = config.playerColor === 'black';
        this.pollInterval = null;

        this.render();

        if (!this.gameOver && !this.isPlayerTurn && this.isParticipant) {
            this.startPolling();
        }

        this.setupResign();
        this.setupToggleMoves();
        this.startDeadlineTimer();
    }

    parseFEN(fen) {
        const board = {};
        const rows = fen.split(' ')[0].split('/');
        for (let r = 0; r < 8; r++) {
            let col = 0;
            for (const ch of rows[r]) {
                if (ch >= '1' && ch <= '8') {
                    col += parseInt(ch);
                } else {
                    const file = String.fromCharCode(97 + col);
                    const rank = 8 - r;
                    board[`${file}${rank}`] = ch;
                    col++;
                }
            }
        }
        return board;
    }

    lastMoveSquares() {
        if (!this.lastMoveUci || this.lastMoveUci.length < 4) return new Set();
        return new Set([
            this.lastMoveUci.substring(0, 2),
            this.lastMoveUci.substring(2, 4),
        ]);
    }

    render() {
        this.container.innerHTML = '';
        const pieces = this.parseFEN(this.fen);
        const ranks = this.flipped ? [1,2,3,4,5,6,7,8] : [8,7,6,5,4,3,2,1];
        const files = this.flipped ? 'hgfedcba'.split('') : 'abcdefgh'.split('');
        const highlighted = this.lastMoveSquares();

        for (const rank of ranks) {
            for (const file of files) {
                const sq = `${file}${rank}`;
                const isLight = (file.charCodeAt(0) - 97 + rank) % 2 === 1;
                const div = document.createElement('div');
                let cls = `sq ${isLight ? 'sq-light' : 'sq-dark'}`;
                if (highlighted.has(sq)) cls += isLight ? ' sq-hl-light' : ' sq-hl-dark';
                div.className = cls;
                div.dataset.square = sq;

                if (file === files[0]) {
                    const rl = document.createElement('span');
                    rl.className = 'sq-label rank-label';
                    rl.textContent = rank;
                    div.appendChild(rl);
                }
                if (rank === (this.flipped ? 8 : 1)) {
                    const fl = document.createElement('span');
                    fl.className = 'sq-label file-label';
                    fl.textContent = file;
                    div.appendChild(fl);
                }

                if (pieces[sq]) {
                    const span = document.createElement('span');
                    span.className = 'piece';
                    span.textContent = PIECE_CHARS[pieces[sq]];
                    span.classList.add(pieces[sq] === pieces[sq].toUpperCase() ? 'w-piece' : 'b-piece');
                    div.appendChild(span);
                }

                div.addEventListener('click', () => this.onSquareClick(sq));
                this.container.appendChild(div);
            }
        }
    }

    onSquareClick(sq) {
        if (this.gameOver || !this.isPlayerTurn) return;

        if (this.selectedSquare) {
            const matchingMoves = this.legalMoves.filter(
                m => m.from === this.selectedSquare && m.to === sq
            );

            if (matchingMoves.length > 0) {
                const hasPromotion = matchingMoves.some(m => m.promotion);
                if (hasPromotion) {
                    this.showPromotionDialog(this.selectedSquare, sq, matchingMoves);
                } else {
                    this.sendMove(matchingMoves[0].uci);
                }
                return;
            }
            this.clearSelection();
        }

        const movesFrom = this.legalMoves.filter(m => m.from === sq);
        if (movesFrom.length > 0) {
            this.selectedSquare = sq;
            const sqEl = this.container.querySelector(`[data-square="${sq}"]`);
            if (sqEl) sqEl.classList.add('sq-selected');

            const targets = new Set(movesFrom.map(m => m.to));
            for (const t of targets) {
                const tEl = this.container.querySelector(`[data-square="${t}"]`);
                if (tEl) tEl.classList.add('sq-target');
            }
        }
    }

    clearSelection() {
        this.selectedSquare = null;
        this.container.querySelectorAll('.sq-selected, .sq-target')
            .forEach(el => el.classList.remove('sq-selected', 'sq-target'));
    }

    showPromotionDialog(from, to, moves) {
        const modal = document.getElementById('promotionModal');
        const choices = document.getElementById('promotionChoices');
        choices.innerHTML = '';

        const isWhite = this.playerColor === 'white';
        const promoPieces = [
            { letter: 'q', char: isWhite ? '\u2655' : '\u265B', label: 'Queen' },
            { letter: 'r', char: isWhite ? '\u2656' : '\u265C', label: 'Rook' },
            { letter: 'b', char: isWhite ? '\u2657' : '\u265D', label: 'Bishop' },
            { letter: 'n', char: isWhite ? '\u2658' : '\u265E', label: 'Knight' },
        ];

        for (const p of promoPieces) {
            const btn = document.createElement('button');
            btn.className = 'promo-btn';
            btn.textContent = p.char;
            btn.title = p.label;
            btn.addEventListener('click', () => {
                modal.classList.remove('active');
                const uci = `${from}${to}${p.letter}`;
                this.sendMove(uci);
            });
            choices.appendChild(btn);
        }

        modal.classList.add('active');
    }

    async sendMove(uci) {
        this.clearSelection();
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
                this.render();
                appendMove(data.move_number, data.san, this.playerColor);

                if (data.game_over) {
                    this.gameOver = true;
                    showResult(data.result, data.result_type, data.rating_change);
                } else {
                    updateTurn(false);
                    this.startPolling();
                }
            } else {
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
                if (data.last_move) {
                    this.lastMoveUci = data.last_move.uci;
                }
                this.render();

                if (data.last_move) {
                    appendMove(null, data.last_move.san, data.last_move.color);
                }

                if (data.status === 'completed' || data.status === 'forfeited') {
                    this.gameOver = true;
                    this.stopPolling();
                    showResult(data.result, data.result_type, data.rating_change);
                    return;
                }

                if (data.is_your_turn) {
                    this.isPlayerTurn = true;
                    this.legalMoves = data.legal_moves;
                    this.stopPolling();
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
                    showResult(data.result, data.result_type, data.rating_change);
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

function initBoard() {
    if (typeof GAME_CONFIG !== 'undefined') {
        new ChessBoard(GAME_CONFIG);
    }
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBoard);
} else {
    initBoard();
}
