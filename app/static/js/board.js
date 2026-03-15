import { Chessground } from 'https://cdn.jsdelivr.net/npm/@lichess-org/chessground@10.1.0/+esm';

const PIECE_URL = 'https://lichess1.org/assets/piece/cburnett/';
const PROMO_ROLES = [
    { letter: 'q', role: 'queen',  label: 'Queen' },
    { letter: 'r', role: 'rook',   label: 'Rook' },
    { letter: 'b', role: 'bishop', label: 'Bishop' },
    { letter: 'n', role: 'knight', label: 'Knight' },
];

/* ── Enoch Audio System ──
   Queue-based playback: lines never overlap. If the player moves faster
   than Enoch speaks, the latest triggered line waits for the current one
   to finish. Audio files are pre-cached as Audio objects so playback
   starts instantly with no fetch delay.
*/

let audioTextToUrl = null;
const audioQueue = [];
let audioPlaying = false;
let currentAudio = null;
let enochMuted = localStorage.getItem('enochMuted') === 'true';
let audioUnlocked = false;
let pendingInitialLine = null;

function unlockAudio() {
    if (audioUnlocked) return;
    audioUnlocked = true;
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume();
    const buf = ctx.createBuffer(1, 1, 22050);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(ctx.destination);
    src.start(0);
    if (pendingInitialLine) {
        playEnochAudio(pendingInitialLine);
        pendingInitialLine = null;
    }
}

function loadAudioManifest() {
    const cfg = window.GAME_CONFIG;
    if (!cfg || !cfg.audioManifestUrl) return Promise.resolve();
    const base = cfg.audioBaseUrl || '/static/audio/enoch/';
    const loader = (window.EnochCache && window.EnochCache.getManifest)
        ? window.EnochCache.getManifest(cfg.audioManifestUrl, cfg.manifestVersion || '1')
        : fetch(cfg.audioManifestUrl).then(r => r.json());
    return loader
        .then(manifest => {
            audioTextToUrl = new Map();
            for (const [, entry] of Object.entries(manifest)) {
                audioTextToUrl.set(entry.text, base + entry.file);
            }
        })
        .catch(e => console.warn('Audio manifest unavailable:', e));
}

function _drainQueue() {
    if (audioPlaying || enochMuted || audioQueue.length === 0) return;

    const url = audioQueue.shift();
    audioPlaying = true;

    const play = (audio) => {
        currentAudio = audio;
        const done = () => {
            audio.removeEventListener('ended', done);
            audio.removeEventListener('error', done);
            audioPlaying = false;
            currentAudio = null;
            _drainQueue();
        };
        audio.addEventListener('ended', done);
        audio.addEventListener('error', done);
        audio.play().catch(() => { done(); });
    };

    if (window.EnochCache) {
        window.EnochCache.getAudio(url).then(play).catch(() => {
            audioPlaying = false;
            _drainQueue();
        });
    } else {
        play(new Audio(url));
    }
}

function playEnochAudio(line) {
    if (enochMuted || !audioTextToUrl || !line) return;
    const url = audioTextToUrl.get(line);
    if (!url) return;

    audioQueue.push(url);
    if (audioQueue.length > 2) {
        audioQueue.splice(0, audioQueue.length - 2);
    }
    _drainQueue();
}

function initMuteButton() {
    const btn = document.getElementById('enochMuteBtn');
    if (!btn) return;
    const iconOn = btn.querySelector('.mute-icon-on');
    const iconOff = btn.querySelector('.mute-icon-off');

    function updateIcon() {
        iconOn.style.display = enochMuted ? 'none' : '';
        iconOff.style.display = enochMuted ? '' : 'none';
    }
    updateIcon();

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        unlockAudio();
        enochMuted = !enochMuted;
        localStorage.setItem('enochMuted', String(enochMuted));
        updateIcon();
        if (enochMuted) {
            audioQueue.length = 0;
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
                audioPlaying = false;
                currentAudio = null;
            }
        }
    });
}

/* ── Chess Move Sounds ── */

const chessSounds = {};

function initChessSounds() {
    const base = (window.AUDIO_CDN || (window.STATIC_BASE || '/static/') + 'audio/') + 'chess/';
    const files = {
        move: 'Move.mp3', capture: 'Capture.mp3',
        check: 'GenericNotify.mp3', end: 'Confirmation.mp3',
        win: 'Win.wav', lose: 'Lose.wav',
    };
    const promises = [];
    for (const [key, file] of Object.entries(files)) {
        const url = base + file;
        const a = new Audio(url);
        a.preload = 'auto';
        chessSounds[key] = a;
        promises.push(new Promise(resolve => {
            if (a.readyState >= 4) { resolve(); return; }
            a.addEventListener('canplaythrough', resolve, { once: true });
            a.addEventListener('error', resolve, { once: true });
        }));
    }
    return Promise.all(promises);
}

function playMoveSound(san, gameOver) {
    if (!san || !chessSounds.move) return;
    let key;
    if (gameOver || san.includes('#'))   key = 'end';
    else if (san.includes('+'))          key = 'check';
    else if (san.includes('x'))          key = 'capture';
    else                                 key = 'move';
    const s = chessSounds[key];
    if (!s) return;
    try { s.currentTime = 0; } catch (e) {}
    s.play().catch(() => {});
}

function playResultSound(result, playerColor) {
    if (!result || !playerColor) return;
    const whiteWins = result === '1-0';
    const blackWins = result === '0-1';
    const isDraw = result === '1/2-1/2';
    let key;
    if (isDraw)                                              key = 'end';
    else if ((whiteWins && playerColor === 'white') ||
             (blackWins && playerColor === 'black'))         key = 'win';
    else                                                     key = 'lose';
    const s = chessSounds[key];
    if (!s) return;
    s.currentTime = 0;
    s.play().catch(() => {});
}

/* ── Check Banner ── */

function showCheckBanner(checkColor, playerColor) {
    let banner = document.getElementById('checkBanner');
    if (!checkColor) {
        if (banner) banner.style.display = 'none';
        return;
    }
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'checkBanner';
        banner.style.cssText = 'position:absolute;top:0;left:0;right:0;z-index:50;' +
            'background:linear-gradient(90deg,rgba(220,40,40,0.9),rgba(180,20,20,0.85));' +
            'color:#fff;text-align:center;font-weight:700;font-size:0.85rem;' +
            'padding:6px 12px;letter-spacing:0.04em;text-transform:uppercase;' +
            'border-bottom:2px solid rgba(255,80,80,0.6);pointer-events:none;';
        const boardWrap = document.querySelector('.gv-board-wrap');
        if (boardWrap) {
            boardWrap.style.position = 'relative';
            boardWrap.prepend(banner);
        } else {
            document.body.prepend(banner);
        }
    }
    const isYou = checkColor === playerColor;
    banner.textContent = isYou ? 'You are in check!' : 'Check!';
    banner.style.display = 'block';
}

/* ── Material / Captured Pieces Display ── */

const CAP_CHARS = {
    white: { q: '\u265b', r: '\u265c', b: '\u265d', n: '\u265e', p: '\u265f' },
    black: { q: '\u2655', r: '\u2656', b: '\u2657', n: '\u2658', p: '\u2659' },
};

function updateCaptures(captures) {
    if (!captures) return;
    for (const color of ['white', 'black']) {
        const el = document.getElementById(`captures-${color}`);
        if (!el) continue;
        const caps = captures[`${color}_captures`] || [];
        const diff = captures.material_diff || 0;
        const chars = CAP_CHARS[color];
        const cls = color === 'white' ? 'gv-cap-w' : 'gv-cap-b';

        let html = '';
        for (const p of caps) {
            html += `<span class="gv-cap-piece ${cls}" data-piece="${p}">${chars[p] || ''}</span>`;
        }
        const advantage = color === 'white' ? diff : -diff;
        if (advantage > 0) {
            html += `<span class="gv-mat-diff">+${advantage}</span>`;
        }
        el.innerHTML = html;
    }
}

function buildDests(legalMoves) {
    const dests = new Map();
    for (const m of legalMoves) {
        if (!dests.has(m.from)) dests.set(m.from, []);
        const arr = dests.get(m.from);
        if (!arr.includes(m.to)) arr.push(m.to);
    }
    return dests;
}

/* ── Opponent piece preview (client-side pseudo-legal squares) ── */

function parseFenBoard(fen) {
    const board = new Map();
    const ranks = fen.split(' ')[0].split('/');
    for (let r = 0; r < 8; r++) {
        let f = 0;
        for (const ch of ranks[r]) {
            if (ch >= '1' && ch <= '8') { f += parseInt(ch); }
            else {
                const sq = 'abcdefgh'[f] + (8 - r);
                const color = ch === ch.toUpperCase() ? 'white' : 'black';
                const piece = ch.toLowerCase();
                board.set(sq, { color, piece });
                f++;
            }
        }
    }
    return board;
}

const STANDARD_KNIGHT = [[2,1],[2,-1],[-2,1],[-2,-1],[1,2],[1,-2],[-1,2],[-1,-2]];
const EXTENDED_KNIGHT = [[3,2],[3,-2],[-3,2],[-3,-2],[2,3],[2,-3],[-2,3],[-2,-3]];

function pseudoLegalSquares(sq, board, customRule) {
    const info = board.get(sq);
    if (!info) return [];
    const { color, piece } = info;
    const f = sq.charCodeAt(0) - 97;
    const r = parseInt(sq[1]) - 1;
    const targets = [];

    function inBounds(ff, rr) { return ff >= 0 && ff <= 7 && rr >= 0 && rr <= 7; }
    function sqName(ff, rr) { return 'abcdefgh'[ff] + (rr + 1); }
    function canLand(ff, rr) {
        const s = sqName(ff, rr);
        const occ = board.get(s);
        return !occ || occ.color !== color;
    }
    function isEmpty(ff, rr) { return !board.get(sqName(ff, rr)); }

    function addSlide(df, dr) {
        let ff = f + df, rr = r + dr;
        while (inBounds(ff, rr)) {
            const s = sqName(ff, rr);
            const occ = board.get(s);
            if (occ) {
                if (occ.color !== color) targets.push(s);
                break;
            }
            targets.push(s);
            ff += df; rr += dr;
        }
    }

    if (piece === 'p') {
        const dir = color === 'white' ? 1 : -1;
        const startRank = color === 'white' ? 1 : 6;
        if (inBounds(f, r + dir) && isEmpty(f, r + dir)) {
            targets.push(sqName(f, r + dir));
            if (r === startRank && isEmpty(f, r + 2 * dir))
                targets.push(sqName(f, r + 2 * dir));
        }
        for (const df of [-1, 1]) {
            if (inBounds(f + df, r + dir)) {
                const s = sqName(f + df, r + dir);
                const occ = board.get(s);
                if (occ && occ.color !== color) targets.push(s);
            }
        }
    } else if (piece === 'n') {
        if (customRule && customRule.includes('Lame Knees')) {
            // Knights are frozen — no moves at all
        } else {
            const offsets = (customRule && customRule.includes('Extended Knight'))
                ? EXTENDED_KNIGHT : STANDARD_KNIGHT;
            for (const [df, dr] of offsets) {
                if (inBounds(f+df, r+dr) && canLand(f+df, r+dr))
                    targets.push(sqName(f+df, r+dr));
            }
        }
    } else if (piece === 'b') {
        for (const [df, dr] of [[1,1],[1,-1],[-1,1],[-1,-1]]) addSlide(df, dr);
    } else if (piece === 'r') {
        for (const [df, dr] of [[1,0],[-1,0],[0,1],[0,-1]]) addSlide(df, dr);
    } else if (piece === 'q') {
        for (const [df, dr] of [[1,1],[1,-1],[-1,1],[-1,-1],[1,0],[-1,0],[0,1],[0,-1]]) addSlide(df, dr);
    } else if (piece === 'k') {
        for (const [df, dr] of [[1,1],[1,-1],[-1,1],[-1,-1],[1,0],[-1,0],[0,1],[0,-1]]) {
            if (inBounds(f+df, r+dr) && canLand(f+df, r+dr))
                targets.push(sqName(f+df, r+dr));
        }
    }
    return targets;
}

function setupOpponentPreview(boardInstance) {
    const el = document.getElementById('chessBoard');
    if (!el) return;

    let previewSq = null;

    el.addEventListener('click', (e) => {
        if (boardInstance.gameOver) return;
        const cg = el.querySelector('cg-board');
        if (!cg) return;
        const rect = cg.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const orientation = boardInstance.playerColor || 'white';
        let fileIdx = Math.floor(x / (rect.width / 8));
        let rankIdx = Math.floor(y / (rect.height / 8));
        if (orientation === 'white') {
            rankIdx = 7 - rankIdx;
        } else {
            fileIdx = 7 - fileIdx;
        }
        if (fileIdx < 0 || fileIdx > 7 || rankIdx < 0 || rankIdx > 7) {
            boardInstance.ground.setAutoShapes([]);
            previewSq = null;
            return;
        }
        const sq = 'abcdefgh'[fileIdx] + (rankIdx + 1);

        if (previewSq === sq) {
            boardInstance.ground.setAutoShapes([]);
            previewSq = null;
            return;
        }

        const board = parseFenBoard(boardInstance.fen);
        const info = board.get(sq);
        if (!info || info.color === boardInstance.playerColor) {
            boardInstance.ground.setAutoShapes([]);
            previewSq = null;
            return;
        }

        const customRule = boardInstance.customRuleName || '';
        const targets = pseudoLegalSquares(sq, board, customRule);
        if (targets.length === 0) {
            boardInstance.ground.setAutoShapes([]);
            previewSq = null;
            return;
        }

        const shapes = [{ orig: sq, brush: 'red' }];
        for (const t of targets) {
            shapes.push({ orig: sq, dest: t, brush: 'red' });
        }
        boardInstance.ground.setAutoShapes(shapes);
        previewSq = sq;
    });
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
        this.isPractice = config.isPractice || false;
        this.customRuleName = config.customRuleName || '';
        this.inCheck = config.inCheck || false;
        this.pollInterval = null;

        const orientation = this.playerColor === 'black' ? 'black' : 'white';
        const movableColor = (this.isPlayerTurn && !this.gameOver && this.isParticipant)
            ? this.playerColor : undefined;

        const shouldAnimateLastMove = this.isPlayerTurn && this.lastMoveUci
            && config.prevFen && this.isParticipant && !this.gameOver;

        this.ground = Chessground(document.getElementById('chessBoard'), {
            fen: shouldAnimateLastMove ? config.prevFen : this.fen,
            orientation,
            turnColor: this.isPlayerTurn ? this.playerColor : this.otherColor(),
            lastMove: shouldAnimateLastMove ? undefined : uciToLastMove(this.lastMoveUci),
            check: shouldAnimateLastMove ? false : this.inCheck,
            coordinates: true,
            viewOnly: this.gameOver || !this.isParticipant,
            animation: { enabled: true, duration: shouldAnimateLastMove ? 400 : 200 },
            highlight: { lastMove: true, check: true },
            draggable: { enabled: true, showGhost: true },
            selectable: { enabled: true },
            movable: {
                free: false,
                color: shouldAnimateLastMove ? undefined : movableColor,
                dests: buildDests(this.legalMoves),
                showDests: true,
                events: { after: (orig, dest) => this.onMove(orig, dest) },
            },
            premovable: { enabled: false },
        });

        showCheckBanner(this.inCheck, this.playerColor);

        if (shouldAnimateLastMove) {
            setTimeout(() => {
                this.ground.set({
                    fen: this.fen,
                    lastMove: uciToLastMove(this.lastMoveUci),
                    check: this.inCheck,
                    animation: { enabled: true, duration: 400 },
                    movable: {
                        color: movableColor,
                        dests: buildDests(this.legalMoves),
                        showDests: true,
                    },
                });
                showCheckBanner(this.inCheck, this.playerColor);
                if (this.lastMoveUci) {
                    const moves = document.querySelectorAll('.gv-ms, .gv-ms-b');
                    const lastMoveEl = moves.length ? moves[moves.length - 1] : null;
                    const san = lastMoveEl ? lastMoveEl.textContent : '';
                    playMoveSound(san, false);
                }
            }, 600);
        }

        const boardEl = document.getElementById('chessBoard');
        if (boardEl) {
            boardEl.addEventListener('mousedown', unlockAudio, { once: true });
            boardEl.addEventListener('touchstart', unlockAudio, { once: true });
        }

        if (!this.gameOver && !this.isPlayerTurn && this.isParticipant && !this.isPractice) {
            this.startPolling();
        }

        this.setupResign();
        this.setupToggleMoves();
        this.startDeadlineTimer();
        setupOpponentPreview(this);
    }

    otherColor() {
        return this.playerColor === 'white' ? 'black' : 'white';
    }

    onMove(orig, dest) {
        unlockAudio();
        this.ground.setAutoShapes([]);
        this.pendingOrig = orig;
        this.pendingDest = dest;
        this.preMoveLastMove = this.lastMoveUci ? uciToLastMove(this.lastMoveUci) : undefined;

        this.ground.set({
            lastMove: [orig, dest],
            movable: { color: undefined },
        });

        const bar = document.getElementById('moveConfirmBar');
        if (bar) bar.classList.add('active');
    }

    confirmMove() {
        unlockAudio();
        const bar = document.getElementById('moveConfirmBar');
        if (bar) bar.classList.remove('active');

        const orig = this.pendingOrig;
        const dest = this.pendingDest;
        this.pendingOrig = null;
        this.pendingDest = null;
        this.preMoveLastMove = undefined;

        if (!orig || !dest) return;

        const matchingMoves = this.legalMoves.filter(m => m.from === orig && m.to === dest);
        const hasPromo = matchingMoves.some(m => m.promotion);
        const isCapture = matchingMoves.some(m => m.san && m.san.includes('x'));

        playMoveSound(isCapture ? 'x' : 'e4', false);

        if (hasPromo) {
            this.showPromotionDialog(orig, dest);
        } else {
            this.sendMove(`${orig}${dest}`, true);
        }
    }

    cancelMove() {
        const bar = document.getElementById('moveConfirmBar');
        if (bar) bar.classList.remove('active');

        this.ground.set({
            fen: this.fen,
            lastMove: this.preMoveLastMove,
            turnColor: this.playerColor,
            movable: {
                color: this.playerColor,
                dests: buildDests(this.legalMoves),
                showDests: true,
            },
            viewOnly: false,
        });

        this.pendingOrig = null;
        this.pendingDest = null;
        this.preMoveLastMove = undefined;
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
                playMoveSound('e4', false);
                this.sendMove(`${from}${to}${p.letter}`, true);
            });
            choices.appendChild(btn);
        }

        modal.classList.add('active');
    }

    async sendMove(uci, soundPlayed = false) {
        if (this.isPractice) {
            updateTurn('thinking');
            setEnochThinking(true);
            this.ground.set({
                movable: { color: undefined, dests: new Map() },
                viewOnly: true,
            });
        }

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

                if (data.is_practice && data.enoch_move) {
                    const playerFen = data.player_fen || data.fen;
                    this.ground.set({
                        fen: playerFen,
                        lastMove: uciToLastMove(uci),
                        turnColor: this.otherColor(),
                        viewOnly: false,
                        animation: { enabled: true, duration: 150 },
                    });
                    appendMove(data.move_number, data.san, this.playerColor);
                    if (!soundPlayed) playMoveSound(data.san, false);

                    await new Promise(r => setTimeout(r, 300));
                    setEnochThinking(false);

                    this.ground.set({
                        fen: data.fen,
                        lastMove: uciToLastMove(data.enoch_move.uci),
                        animation: { enabled: true, duration: 200 },
                    });
                    appendMove(null, data.enoch_move.san, this.otherColor());
                    playMoveSound(data.enoch_move.san, data.game_over);

                    this.fen = data.fen;
                    this.lastMoveUci = data.enoch_move.uci;

                    updateCaptures(data.captures);
                    if (data.enoch) updateEnoch(data.enoch);

                    if (data.game_over) {
                        this.gameOver = true;
                        this.ground.set({ viewOnly: true });
                        runPracticeEnd(data);
                    } else {
                        this.isPlayerTurn = true;
                        const legalResp = await fetch(`/game/${this.gameId}/state`);
                        const legalData = await legalResp.json();
                        this.legalMoves = legalData.legal_moves || [];
                        this.ground.set({
                            turnColor: this.playerColor,
                            check: legalData.check || false,
                            movable: {
                                color: this.playerColor,
                                dests: buildDests(this.legalMoves),
                            },
                            viewOnly: false,
                        });
                        showCheckBanner(legalData.check, this.playerColor);
                        updateTurn(true);
                    }
                } else if (data.is_practice && !data.enoch_move) {
                    setEnochThinking(false);
                    this.ground.set({
                        fen: data.fen,
                        lastMove: uciToLastMove(uci),
                        viewOnly: true,
                    });
                    appendMove(data.move_number, data.san, this.playerColor);
                    if (!soundPlayed) playMoveSound(data.san, data.game_over);
                    updateCaptures(data.captures);
                    if (data.enoch) updateEnoch(data.enoch);
                    if (data.game_over) {
                        this.gameOver = true;
                        runPracticeEnd(data);
                    }
                } else {
                    this.ground.set({
                        fen: data.fen,
                        lastMove: uciToLastMove(uci),
                        turnColor: this.otherColor(),
                        check: data.check || false,
                        movable: { color: undefined, dests: new Map() },
                        viewOnly: false,
                    });
                    showCheckBanner(false, this.playerColor);

                    appendMove(data.move_number, data.san, this.playerColor);
                    if (!soundPlayed) playMoveSound(data.san, data.game_over);
                    updateCaptures(data.captures);

                    if (data.enoch) updateEnoch(data.enoch);
                    if (data.sequence) updateSequence(data.sequence);
                    if (data.can_name_sequence) showNamingPrompt(this.gameId, data.can_name_sequence);

                    if (data.game_over) {
                        this.gameOver = true;
                        this.ground.set({ viewOnly: true });
                        runEndSequence(data, this.gameId, this.hasCommended);
                    } else {
                        updateTurn(false);
                        this.startPolling();
                        if (data.next_game) {
                            showNextGameBanner(data.next_game);
                        }
                    }
                }
            } else {
                if (this.isPractice) setEnochThinking(false);
                this.ground.set({
                    fen: this.fen,
                    lastMove: uciToLastMove(this.lastMoveUci),
                    movable: {
                        color: this.playerColor,
                        dests: buildDests(this.legalMoves),
                    },
                    viewOnly: false,
                });
                updateTurn(true);
                console.error('Move rejected:', data.error);
            }
        } catch (err) {
            if (this.isPractice) setEnochThinking(false);
            updateTurn(true);
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
                    check: data.check || false,
                });

                if (data.last_move) {
                    appendMove(null, data.last_move.san, data.last_move.color);
                    playMoveSound(data.last_move.san, data.status === 'completed' || data.status === 'forfeited');
                }
                if (data.captures) updateCaptures(data.captures);
                if (data.enoch) updateEnoch(data.enoch);
                if (data.sequence) updateSequence(data.sequence);
                showCheckBanner(data.check, this.playerColor);

                if (data.status === 'completed' || data.status === 'forfeited') {
                    this.gameOver = true;
                    this.stopPolling();
                    this.ground.set({ viewOnly: true });
                    showCheckBanner(false, this.playerColor);
                    runEndSequence(data, this.gameId, this.hasCommended);
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
                    if (data.is_practice) {
                        if (data.enoch) updateEnoch(data.enoch);
                        runPracticeEnd(data);
                    } else {
                        runEndSequence(data, this.gameId, this.hasCommended);
                    }
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
            if (diff <= 0) {
                el.textContent = 'Time up';
                if (this._deadlineInterval) {
                    clearInterval(this._deadlineInterval);
                    this._deadlineInterval = null;
                }
                return;
            }
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
        this._deadlineInterval = setInterval(tick, 60000);
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

function setEnochThinking(active) {
    const bars = document.querySelectorAll('.gv-player-bar');
    const bar = bars.length > 0 ? bars[0] : null;
    if (!bar) return;
    const nameEl = bar.querySelector('.gv-player-name');
    if (!nameEl) return;
    const existing = bar.querySelector('.gv-thinking-tag');
    if (active && !existing) {
        const tag = document.createElement('span');
        tag.className = 'gv-thinking-tag';
        tag.innerHTML = 'thinking<span class="gv-thinking-dots"></span>';
        nameEl.parentNode.insertBefore(tag, nameEl.nextSibling);
    } else if (!active && existing) {
        existing.remove();
    }
}

function updateTurn(state) {
    const el = document.getElementById('turnIndicator');
    if (!el) return;
    if (state === 'thinking') {
        el.innerHTML = '<span class="enoch-thinking">Enoch is thinking<span class="gv-thinking-dots"></span></span>';
    } else if (state === true || state === 'yours') {
        el.innerHTML = '<span class="turn-yours">Your turn</span>';
    } else {
        el.innerHTML = '<span class="turn-waiting">Waiting for opponent</span>';
    }
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

function updateEnoch(line) {
    const bar = document.getElementById('enochBar');
    const text = document.getElementById('enochText');
    if (!bar || !text) return;
    if (!line) { bar.style.display = 'none'; return; }
    text.textContent = line;
    bar.style.display = '';
    bar.classList.remove('enoch-fade');
    void bar.offsetWidth;
    bar.classList.add('enoch-fade');
    playEnochAudio(line);
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
            if (data.success) {
                close();
                if (data.earned_items && data.earned_items.length) {
                    await showEnochQueue(data.earned_items);
                }
            } else {
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

/* ── Enoch Intervention Modal (delegates to universal award popup) ── */

async function showEnochQueue(items) {
    if (window.showAwardQueue) {
        await window.showAwardQueue(items);
    }
}

async function runEndSequence(data, gameId, hasCommended) {
    setTimeout(() => playResultSound(data.result, window.GAME_CONFIG.playerColor), 350);
    const items = data.earned_items || [];
    if (items.length > 0) {
        await showEnochQueue(items);
    }
    showResult(data.result, data.result_type, data.rating_change);
    if (data.show_commend && !hasCommended) showCommendPrompt(gameId);
}

/* ── Practice Mode: End Summary ── */

async function runPracticeEnd(data) {
    setTimeout(() => playResultSound(data.result, window.GAME_CONFIG.playerColor), 350);
    const summary = data.practice_summary;
    const settlement = data.wager_settlement;
    const modal = document.getElementById('practiceSummaryModal');
    if (!modal || !summary) {
        showResult(data.result, data.result_type, null);
        return;
    }

    showResult(data.result, data.result_type, null);

    const wagerItems = (settlement && settlement.earned_items) || [];
    const loreItems = (summary && summary.earned_lore) || [];
    const allItems = wagerItems.concat(loreItems);
    if (allItems.length > 0) {
        await showEnochQueue(allItems);
    }

    const titleEl = document.getElementById('practiceSummaryTitle');
    const resultEl = document.getElementById('practiceSummaryResult');
    const movesEl = document.getElementById('practiceSummaryMoves');
    const enochEl = document.getElementById('practiceSummaryEnoch');
    const loreEl = document.getElementById('practiceSummaryLore');

    if (settlement) {
        if (titleEl) titleEl.textContent = 'Wager Settled';
        if (resultEl) {
            const sign = settlement.points_change >= 0 ? '+' : '';
            const cls = settlement.points_change > 0 ? 'rating-up' : (settlement.points_change < 0 ? 'rating-down' : '');
            resultEl.innerHTML = `<span class="wager-settlement-line ${cls}">${sign}${settlement.points_change} rating points</span>`;
        }
        if (enochEl) {
            enochEl.innerHTML = `<em>"${settlement.dialogue}"</em>`;
        }
        if (movesEl) movesEl.textContent = `Moves: ${summary.move_count} · New Rating: ${settlement.new_rating}`;
    } else {
        if (resultEl) resultEl.textContent = `Result: ${summary.result}`;
        if (movesEl) movesEl.textContent = `Moves: ${summary.move_count}`;
        if (enochEl && data.enoch) {
            enochEl.innerHTML = `<em>"${data.enoch}"</em>`;
        }
    }

    if (loreEl) {
        let html = `<p class="practice-lore-wins">Victories over the Steward: <strong>${summary.total_wins}</strong></p>`;
        if (summary.next_milestone) {
            html += `<p class="practice-lore-next">Next Milestone: ${summary.next_milestone.title} (${summary.next_milestone.wins} Wins)</p>`;
        } else {
            html += `<p class="practice-lore-next">All Enoch milestones achieved.</p>`;
        }
        loreEl.innerHTML = html;
    }

    const rematch = document.getElementById('practiceRematch');
    if (rematch) {
        rematch.addEventListener('click', async () => {
            rematch.disabled = true;
            rematch.textContent = 'Descending\u2026';
            try {
                const resp = await fetch('/practice/new', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                const d = await resp.json();
                if (d.url) window.location.href = d.url;
            } catch (e) {
                console.error(e);
            }
        });
    }

    setTimeout(() => modal.classList.add('active'), 400);
}

/* ── Replay controls ── */

function initReplay() {
    const fens = window.GAME_CONFIG && window.GAME_CONFIG.replayFens;
    if (!fens || fens.length < 2) return;

    const bar = document.getElementById('replayBar');
    if (!bar) return;

    const plyLabel = document.getElementById('replayPly');
    const total = fens.length - 1;
    let current = total;

    const moveSans = document.querySelectorAll('.move-san[data-ply]');
    const cgWrap = document.querySelector('#chessBoard .cg-wrap');

    function highlight(ply) {
        moveSans.forEach(el => {
            el.classList.toggle('replay-active', parseInt(el.dataset.ply) === ply);
        });
    }

    function goTo(ply) {
        current = Math.max(0, Math.min(total, ply));
        plyLabel.textContent = `${current} / ${total}`;

        const fen = fens[current];
        if (cgWrap && cgWrap.cg) {
            cgWrap.cg.set({ fen: fen });
        } else if (window._cg) {
            window._cg.set({ fen: fen });
        }

        highlight(current);
    }

    const rStart = document.getElementById('replayStart');
    const rPrev  = document.getElementById('replayPrev');
    const rNext  = document.getElementById('replayNext');
    const rEnd   = document.getElementById('replayEnd');
    if (rStart) rStart.addEventListener('click', () => goTo(0));
    if (rPrev)  rPrev.addEventListener('click', () => goTo(current - 1));
    if (rNext)  rNext.addEventListener('click', () => goTo(current + 1));
    if (rEnd)   rEnd.addEventListener('click', () => goTo(total));

    moveSans.forEach(el => {
        el.style.cursor = 'pointer';
        el.addEventListener('click', () => goTo(parseInt(el.dataset.ply)));
    });

    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowLeft') { e.preventDefault(); goTo(current - 1); }
        else if (e.key === 'ArrowRight') { e.preventDefault(); goTo(current + 1); }
        else if (e.key === 'Home') { e.preventDefault(); goTo(0); }
        else if (e.key === 'End') { e.preventDefault(); goTo(total); }
    });

    highlight(total);
}

/* ── PGN copy ── */

function initPgnCopy() {
    const btn = document.getElementById('pgnCopyBtn');
    const text = document.getElementById('pgnText');
    if (!btn || !text) return;

    btn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(text.textContent);
            btn.textContent = 'Copied';
            setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
        } catch {
            const range = document.createRange();
            range.selectNodeContents(text);
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            btn.textContent = 'Selected';
            setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
        }
    });
}

/* ── Init ── */

const _loadBar = document.getElementById('loadingBarFill');
let _loadPct = 0;
function _setLoadPct(pct) {
    _loadPct = Math.min(100, Math.max(_loadPct, pct));
    if (_loadBar) _loadBar.style.width = _loadPct + '%';
}

function dismissLoading() {
    _setLoadPct(100);
    const overlay = document.getElementById('gameLoading');
    const container = document.getElementById('gameContainer');
    if (container) container.style.visibility = '';
    setTimeout(() => { if (overlay) overlay.classList.add('done'); }, 120);
}

function preloadPieceImages() {
    const BASE = 'https://lichess1.org/assets/piece/cburnett/';
    const pieces = ['wK','wQ','wR','wB','wN','wP','bK','bQ','bR','bB','bN','bP'];
    const exts = ['.svg'];
    const promises = pieces.flatMap(p =>
        exts.map(ext => new Promise(resolve => {
            const img = new Image();
            img.onload = resolve;
            img.onerror = resolve;
            img.src = BASE + p + ext;
        }))
    );
    return Promise.all(promises);
}

const cfg = window.GAME_CONFIG;
const _assetsReady = sessionStorage.getItem('chess_assets_loaded') === '1';

if (_assetsReady) {
    dismissLoading();
}

function showNextGameBanner(nextGame) {
    let banner = document.getElementById('nextGameBanner');
    if (banner) banner.remove();
    banner = document.createElement('div');
    banner.id = 'nextGameBanner';
    banner.className = 'gv-next-game-banner';
    banner.innerHTML = `<span>Your turn vs <strong>${nextGame.opponent}</strong></span><a href="${nextGame.url}" class="btn btn-sm btn-primary">Go &rarr;</a>`;
    const container = document.getElementById('gameContainer');
    const toolbar = container && container.querySelector('.gv-toolbar');
    if (toolbar) toolbar.parentNode.insertBefore(banner, toolbar);
    else if (container) container.appendChild(banner);
    let countdown = 8;
    const timer = setInterval(() => {
        countdown--;
        if (countdown <= 0) {
            clearInterval(timer);
            window.location.href = nextGame.url;
        }
        const goBtn = banner.querySelector('.btn');
        if (goBtn) goBtn.textContent = `Go (${countdown}s) →`;
    }, 1000);
    banner.addEventListener('click', (e) => {
        if (e.target.tagName !== 'A') return;
        clearInterval(timer);
    });
}

_setLoadPct(5);
const soundsReady = initChessSounds().then(() => _setLoadPct(40));
const manifestReady = loadAudioManifest().then(() => _setLoadPct(65));
const piecesReady = preloadPieceImages().then(() => _setLoadPct(85));

if (cfg) {
    const board = new ChessBoard(cfg);
    window._cg = board.ground;

    const confirmYes = document.getElementById('moveConfirmYes');
    const confirmNo = document.getElementById('moveConfirmNo');
    if (confirmYes) confirmYes.addEventListener('click', () => board.confirmMove());
    if (confirmNo) confirmNo.addEventListener('click', () => board.cancelMove());
}
initReplay();
initPgnCopy();
initMuteButton();
_setLoadPct(20);

const MAX_WAIT = _assetsReady ? 500 : 6000;
const timeout = new Promise(resolve => setTimeout(resolve, MAX_WAIT));

Promise.race([
    Promise.all([soundsReady, manifestReady, piecesReady]),
    timeout,
]).then(() => {
    if (!_assetsReady) dismissLoading();
    try { sessionStorage.setItem('chess_assets_loaded', '1'); } catch (e) {}
    const initialLine = cfg && cfg.initialEnochLine;
    if (initialLine) {
        if (audioUnlocked) {
            playEnochAudio(initialLine);
        } else {
            pendingInitialLine = initialLine;
        }
    }
});
