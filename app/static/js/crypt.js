import { Chessground } from 'https://cdn.jsdelivr.net/npm/@lichess-org/chessground@10.1.0/+esm';

const PIECE_URL = 'https://lichess1.org/assets/piece/cburnett/';

const cfg = window.CRYPT_CONFIG;
if (!cfg) throw new Error('CRYPT_CONFIG missing');

const GAME_ID = cfg.gameId;
const MAX_WAVES = cfg.maxWaves || 10;

/* ── State ────────────────────────────────────────────── */

let ground = null;
let phase = cfg.phase;
let inventory = cfg.inventory.slice();
let availableInv = [];
let placedPieces = {};
let selectedPieceIdx = -1;
let gold = cfg.gold;
let score = cfg.score;
let kills = cfg.kills;
let wave = cfg.wave;
let currentLegalMoves = cfg.legalMoves || [];
let pendingMove = null;

/* ── Piece helpers ────────────────────────────────────── */

const SYM_TO_ROLE = {
    K: 'king', Q: 'queen', R: 'rook', B: 'bishop', N: 'knight', P: 'pawn',
    k: 'king', q: 'queen', r: 'rook', b: 'bishop', n: 'knight', p: 'pawn',
};
const SYM_TO_LABEL = {K:'King',Q:'Queen',R:'Rook',B:'Bishop',N:'Knight',P:'Pawn'};

function buildDests(moves) {
    const dests = new Map();
    for (const m of moves) {
        if (!dests.has(m.from)) dests.set(m.from, []);
        dests.get(m.from).push(m.to);
    }
    return dests;
}

/* ── DOM refs ─────────────────────────────────────────── */

const $board      = document.getElementById('cryptBoard');
const $invGrid    = document.getElementById('invGrid');
const $btnDeploy  = document.getElementById('btnDeploy');
const $btnAbandon = document.getElementById('btnAbandon');
const $panelPlace = document.getElementById('panelPlacement');
const $panelBattle= document.getElementById('panelBattle');
const $panelWave  = document.getElementById('panelWaveDone');
const $panelOver  = document.getElementById('panelGameover');
const $enochSay   = document.getElementById('enochSay');
const $confirmBar = document.getElementById('crConfirmBar');
const $confirmYes = document.getElementById('crConfirmYes');
const $confirmNo  = document.getElementById('crConfirmNo');
const $hudWave    = document.getElementById('hudWave');
const $hudScore   = document.getElementById('hudScore');
const $hudGold    = document.getElementById('hudGold');
const $hudKills   = document.getElementById('hudKills');
const $milestoneBox = document.getElementById('milestoneBox');
const $milestoneMsg = document.getElementById('milestoneMsg');
const $btnCashout   = document.getElementById('btnCashout');
const $btnContinue  = document.getElementById('btnContinue');
const $btnNextWave  = document.getElementById('btnNextWave');
const $waveDoneTitle = document.getElementById('waveDoneTitle');
const $gameoverTitle = document.getElementById('gameoverTitle');
const $gameoverRating = document.getElementById('gameoverRating');
const $ladderCompact = document.getElementById('ladderCompact');

/* ── Chess Sounds ─────────────────────────────────────── */

const chessSounds = {};
function initSounds() {
    const base = (window.AUDIO_CDN || (window.STATIC_BASE || '/static/') + 'audio/') + 'chess/';
    const files = { move:'Move.mp3', capture:'Capture.mp3', check:'GenericNotify.mp3', end:'Confirmation.mp3' };
    for (const [k,f] of Object.entries(files)) {
        const a = new Audio(base + f);
        a.preload = 'auto';
        chessSounds[k] = a;
    }
}
initSounds();

function playSound(san, over) {
    let key = 'move';
    if (over || (san && san.includes('#'))) key = 'end';
    else if (san && san.includes('+')) key = 'check';
    else if (san && san.includes('x')) key = 'capture';
    const s = chessSounds[key];
    if (s) { try { s.currentTime = 0; } catch(e){} s.play().catch(()=>{}); }
}

/* ── Enoch Voice ──────────────────────────────────────── */

let audioTextToUrl = null;
let enochQueue = [];
let enochPlaying = false;
let enochMuted = false;
let currentEnochAudio = null;

function loadEnochManifest() {
    if (!cfg.audioManifestUrl) return Promise.resolve();
    const base = cfg.audioBaseUrl || '/static/audio/enoch/';
    const loader = (window.EnochCache && window.EnochCache.getManifest)
        ? window.EnochCache.getManifest(cfg.audioManifestUrl, cfg.manifestVersion || '1')
        : fetch(cfg.audioManifestUrl).then(r => r.json());
    return loader.then(manifest => {
        audioTextToUrl = new Map();
        for (const [, entry] of Object.entries(manifest)) {
            audioTextToUrl.set(entry.text, base + entry.file);
        }
    }).catch(e => console.warn('Enoch manifest unavailable:', e));
}

function drainEnochQueue() {
    if (enochPlaying || enochMuted || enochQueue.length === 0) return;
    const url = enochQueue.shift();
    enochPlaying = true;
    const play = (audio) => {
        currentEnochAudio = audio;
        const done = () => {
            audio.removeEventListener('ended', done);
            audio.removeEventListener('error', done);
            enochPlaying = false;
            currentEnochAudio = null;
            drainEnochQueue();
        };
        audio.addEventListener('ended', done);
        audio.addEventListener('error', done);
        audio.play().catch(() => { done(); });
    };
    if (window.EnochCache) {
        window.EnochCache.getAudio(url).then(play).catch(() => {
            enochPlaying = false;
            drainEnochQueue();
        });
    } else {
        play(new Audio(url));
    }
}

function playEnochLine(text) {
    if (enochMuted || !audioTextToUrl || !text) return;
    const url = audioTextToUrl.get(text);
    if (!url) return;
    enochQueue.push(url);
    if (enochQueue.length > 3) enochQueue.splice(0, enochQueue.length - 2);
    drainEnochQueue();
}

loadEnochManifest();

/* ── HUD ──────────────────────────────────────────────── */

function updateHud() {
    if ($hudWave)  $hudWave.innerHTML  = wave + '<span class="cr-hud-max">/' + MAX_WAVES + '</span>';
    if ($hudScore) $hudScore.textContent = score;
    if ($hudGold)  $hudGold.textContent  = gold;
    if ($hudKills) $hudKills.textContent = kills;
}

function setEnoch(text) {
    if ($enochSay && text) {
        $enochSay.textContent = text;
        $enochSay.classList.add('cr-enoch-flash');
        setTimeout(() => $enochSay.classList.remove('cr-enoch-flash'), 600);
    }
    playEnochLine(text);
}

/* ── Progression Ladder ───────────────────────────────── */

function updateLadder(currentWave) {
    if (!$ladderCompact) return;
    const steps = $ladderCompact.querySelectorAll('.cr-lc-step');
    steps.forEach(step => {
        const w = parseInt(step.dataset.wave);
        step.classList.remove('cr-lc-current', 'cr-lc-cleared');
        if (w < currentWave) step.classList.add('cr-lc-cleared');
        else if (w === currentWave) step.classList.add('cr-lc-current');
    });
}

/* ── Panels ───────────────────────────────────────────── */

function showPanel(name) {
    $panelPlace.style.display = name === 'placement' ? '' : 'none';
    $panelBattle.style.display = name === 'battle' ? '' : 'none';
    $panelWave.style.display = name === 'wave' ? '' : 'none';
    $panelOver.style.display = name === 'gameover' ? '' : 'none';
}

/* ── Init board ───────────────────────────────────────── */

ground = Chessground($board, {
    orientation: 'white',
    movable: { free: false, color: undefined },
    draggable: { enabled: false },
    selectable: { enabled: false },
    animation: { enabled: true, duration: 200 },
    coordinates: true,
});

/* ═══════════════════════════════════════════════════════
   PLACEMENT PHASE
   ═══════════════════════════════════════════════════════ */

function enterPlacement() {
    phase = 'placement';
    placedPieces = {};
    selectedPieceIdx = -1;
    availableInv = inventory.slice();

    showPanel('placement');
    updateLadder(wave);

    ground.set({
        fen: '8/8/8/8/8/8/8/8',
        movable: { free: false, color: undefined },
        draggable: { enabled: false },
        selectable: { enabled: false },
        lastMove: undefined,
        check: false,
    });

    renderInventory();
    updateDeployBtn();
    updateShopButtons();
}

function renderInventory() {
    $invGrid.innerHTML = '';
    availableInv.forEach((sym, idx) => {
        const btn = document.createElement('button');
        btn.className = 'cr-inv-btn' + (idx === selectedPieceIdx ? ' selected' : '');
        btn.dataset.idx = idx;
        btn.title = SYM_TO_LABEL[sym] || sym;
        if (sym === 'K') btn.classList.add('cr-inv-king');

        const piece = document.createElement('span');
        piece.className = 'cr-piece-icon';
        piece.style.backgroundImage = `url(${PIECE_URL}w${sym}.svg)`;
        btn.appendChild(piece);

        btn.addEventListener('click', () => selectInventoryPiece(idx));
        $invGrid.appendChild(btn);
    });
}

function selectInventoryPiece(idx) {
    if (phase !== 'placement') return;
    selectedPieceIdx = (selectedPieceIdx === idx) ? -1 : idx;
    renderInventory();
    highlightPlacementSquares();
}

function highlightPlacementSquares() {
    if (selectedPieceIdx < 0) {
        ground.set({ drawable: { shapes: [] } });
        return;
    }
    const shapes = [];
    for (let f = 0; f < 8; f++) {
        for (let r = 0; r < 2; r++) {
            const sq = 'abcdefgh'[f] + (r + 1);
            if (!placedPieces[sq]) {
                shapes.push({ orig: sq, brush: 'green' });
            }
        }
    }
    ground.set({ drawable: { shapes } });
}

function onPlacementClick(sq) {
    if (phase !== 'placement') return;
    const rank = parseInt(sq[1]);

    if (placedPieces[sq]) {
        const sym = placedPieces[sq];
        delete placedPieces[sq];
        availableInv.push(sym);
        updateBoardFromPlacement();
        renderInventory();
        updateDeployBtn();
        return;
    }

    if (rank > 2 || selectedPieceIdx < 0) return;

    const sym = availableInv[selectedPieceIdx];
    placedPieces[sq] = sym;
    availableInv.splice(selectedPieceIdx, 1);
    selectedPieceIdx = -1;
    updateBoardFromPlacement();
    renderInventory();
    updateDeployBtn();
    highlightPlacementSquares();
}

function updateBoardFromPlacement() {
    const pieces = new Map();
    for (const [sq, sym] of Object.entries(placedPieces)) {
        pieces.set(sq, { role: SYM_TO_ROLE[sym], color: 'white' });
    }
    ground.setPieces(pieces, false);

    const allSquares = [];
    for (let f = 0; f < 8; f++) {
        for (let r = 0; r < 8; r++) {
            allSquares.push('abcdefgh'[f] + (r + 1));
        }
    }
    const usedSquares = new Set(Object.keys(placedPieces));
    const emptyPieces = new Map();
    for (const sq of allSquares) {
        if (!usedSquares.has(sq)) {
            emptyPieces.set(sq, undefined);
        }
    }
    ground.setPieces(emptyPieces, false);
    for (const [sq, sym] of Object.entries(placedPieces)) {
        const m = new Map();
        m.set(sq, { role: SYM_TO_ROLE[sym], color: 'white' });
        ground.setPieces(m, false);
    }
}

function updateDeployBtn() {
    const hasKing = Object.values(placedPieces).includes('K');
    $btnDeploy.disabled = !hasKing;
}

function updateShopButtons() {
    document.querySelectorAll('.cr-shop-btn').forEach(btn => {
        const price = parseInt(btn.dataset.price);
        btn.disabled = gold < price;
    });
}

/* ── Shop ─────────────────────────────────────────────── */

document.querySelectorAll('.cr-shop-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (phase !== 'placement') return;
        const piece = btn.dataset.piece;
        fetch(`/crypt/${GAME_ID}/buy`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({piece}),
        })
        .then(r => r.json())
        .then(d => {
            if (!d.ok) return;
            gold = d.gold;
            inventory = d.inventory;
            rebuildAvailable();
            updateHud();
            renderInventory();
            updateShopButtons();
            if (d.enoch) setEnoch(d.enoch);
        });
    });
});

function rebuildAvailable() {
    const placedList = Object.values(placedPieces);
    const placedCount = {};
    for (const p of placedList) placedCount[p] = (placedCount[p]||0)+1;
    const invCount = {};
    for (const p of inventory) invCount[p] = (invCount[p]||0)+1;
    availableInv = [];
    for (const [sym, total] of Object.entries(invCount)) {
        const placed = placedCount[sym] || 0;
        for (let i = 0; i < total - placed; i++) availableInv.push(sym);
    }
}

/* ── Deploy ───────────────────────────────────────────── */

$btnDeploy.addEventListener('click', () => {
    if (phase !== 'placement') return;
    if (!Object.values(placedPieces).includes('K')) return;
    $btnDeploy.disabled = true;
    $btnDeploy.textContent = 'Deploying…';

    fetch(`/crypt/${GAME_ID}/deploy`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({placement: placedPieces}),
    })
    .then(r => r.json())
    .then(d => {
        $btnDeploy.textContent = 'Deploy Forces';
        if (!d.ok) { $btnDeploy.disabled = false; alert(d.error); return; }
        animateWaveEntry(d);
    });
});

/* ── Abandon ──────────────────────────────────────────── */

$btnAbandon.addEventListener('click', () => {
    if (!confirm('Abandon this run? You will receive your safety-net rating.')) return;
    fetch(`/crypt/${GAME_ID}/abandon`, {method:'POST', headers:{'Content-Type':'application/json'}})
    .then(r => r.json())
    .then(d => {
        window.location.href = '/crypt';
    });
});

/* ═══════════════════════════════════════════════════════
   WAVE ENTRY ANIMATION
   ═══════════════════════════════════════════════════════ */

async function animateWaveEntry(data) {
    showPanel('battle');
    updateLadder(data.wave);
    if (data.enoch) setEnoch(data.enoch);

    ground.set({
        fen: data.fen,
        movable: { free: false, color: undefined },
        turnColor: 'white',
        lastMove: undefined,
        check: false,
    });

    const playerPieces = new Map();
    for (const [sq, sym] of Object.entries(placedPieces)) {
        playerPieces.set(sq, { role: SYM_TO_ROLE[sym], color: 'white' });
    }

    const clearAll = new Map();
    for (let f = 0; f < 8; f++) {
        for (let r = 0; r < 8; r++) {
            clearAll.set('abcdefgh'[f] + (r+1), undefined);
        }
    }
    ground.setPieces(clearAll, false);
    ground.setPieces(playerPieces, false);

    for (const ep of data.enemy_pieces) {
        await new Promise(r => setTimeout(r, 150));
        const m = new Map();
        m.set(ep.square, { role: SYM_TO_ROLE[ep.piece], color: 'black' });
        ground.setPieces(m, false);
        playSound(null);
    }

    await new Promise(r => setTimeout(r, 300));

    currentLegalMoves = data.legal_moves || [];
    enableBattle();
}

/* ═══════════════════════════════════════════════════════
   BATTLE PHASE
   ═══════════════════════════════════════════════════════ */

function enableBattle() {
    phase = 'battle';

    ground.set({
        movable: {
            free: false,
            color: 'white',
            dests: buildDests(currentLegalMoves),
            showDests: true,
        },
        draggable: { enabled: true },
        selectable: { enabled: true },
        turnColor: 'white',
        events: { move: onPlayerMove },
    });
}

function onPlayerMove(orig, dest) {
    const match = currentLegalMoves.find(m => m.from === orig && m.to === dest);
    if (!match) return;

    const isPromo = match.promotion && match.promotion !== '';
    let uci = orig + dest;
    if (isPromo) uci += 'q';

    pendingMove = { orig, dest, uci, san: match.san };

    ground.set({
        movable: { free: false, color: undefined, dests: new Map() },
        draggable: { enabled: false },
    });

    $confirmBar.style.display = 'flex';
}

$confirmYes.addEventListener('click', () => {
    if (!pendingMove) return;
    $confirmBar.style.display = 'none';
    playSound(pendingMove.san, false);
    sendMove(pendingMove.uci);
    pendingMove = null;
});

$confirmNo.addEventListener('click', () => {
    pendingMove = null;
    $confirmBar.style.display = 'none';
    ground.set({
        movable: {
            free: false,
            color: 'white',
            dests: buildDests(currentLegalMoves),
            showDests: true,
        },
        draggable: { enabled: true },
        selectable: { enabled: true },
        events: { move: onPlayerMove },
    });
});

function sendMove(uci) {
    ground.set({ movable: { color: undefined, dests: new Map() }, draggable: { enabled: false } });

    fetch(`/crypt/${GAME_ID}/move`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({uci}),
    })
    .then(r => r.json())
    .then(d => {
        if (!d.ok) { alert(d.error); return; }

        gold = d.gold;
        score = d.score;
        kills = d.kills;
        wave = d.wave;
        updateHud();

        if (d.enoch) setEnoch(d.enoch);

        if (d.ai_move) {
            setTimeout(() => {
                ground.set({ fen: d.fen, lastMove: [d.ai_move.uci.slice(0,2), d.ai_move.uci.slice(2,4)] });
                playSound(d.ai_move.san, d.game_over);

                if (d.game_over) {
                    showGameOver(d);
                } else if (d.wave_complete) {
                    showWaveComplete(d);
                } else {
                    currentLegalMoves = d.legal_moves || [];
                    enableBattle();
                }
            }, 300);
        } else {
            ground.set({ fen: d.fen });
            if (d.game_over) {
                showGameOver(d);
            } else if (d.wave_complete) {
                showWaveComplete(d);
            } else {
                currentLegalMoves = d.legal_moves || [];
                enableBattle();
            }
        }
    });
}

/* ═══════════════════════════════════════════════════════
   WAVE COMPLETE / MILESTONE
   ═══════════════════════════════════════════════════════ */

function showWaveComplete(d) {
    phase = 'wave_done';
    showPanel('wave');
    updateLadder(d.next_wave);

    const waveCleared = d.wave_cleared || (d.next_wave - 1);

    if (d.victory) {
        $waveDoneTitle.textContent = 'THE CRYPT IS CONQUERED!';
    } else {
        $waveDoneTitle.textContent = `Wave ${waveCleared} Cleared!`;
    }

    const stats = document.getElementById('waveDoneStats');
    stats.innerHTML = `
        <div class="cr-wd-row"><span>Wave</span><strong>${waveCleared} / ${MAX_WAVES}</strong></div>
        <div class="cr-wd-row"><span>Bonus Gold</span><strong>+${d.bonus_gold}g</strong></div>
        <div class="cr-wd-row"><span>Bonus Score</span><strong>+${d.bonus_score}</strong></div>
        <div class="cr-wd-row"><span>Total Gold</span><strong>${d.gold}g</strong></div>
        <div class="cr-wd-row"><span>Total Score</span><strong>${d.score}</strong></div>
    `;

    inventory = d.inventory;
    gold = d.gold;
    score = d.score;
    wave = d.next_wave;
    kills = d.kills;
    updateHud();

    if (d.enoch_milestone) {
        setEnoch(d.enoch_milestone);
    }

    if (d.is_milestone && d.cashout_value !== null && d.cashout_value !== undefined) {
        $milestoneBox.style.display = '';
        const netLabel = d.cashout_value >= 0 ? `+${d.cashout_value}` : `${d.cashout_value}`;
        const safetyLabel = d.safety_net >= 0 ? `+${d.safety_net}` : `${d.safety_net}`;
        $milestoneMsg.innerHTML = `
            <div class="cr-ms-title">MILESTONE REACHED</div>
            <div class="cr-ms-detail">
                Cash out now: <strong>${netLabel} rating points</strong><br>
                Safety net locked in: <strong>${safetyLabel} points</strong>
                (guaranteed if you lose from here)
            </div>
        `;
        $btnNextWave.style.display = 'none';
    } else {
        $milestoneBox.style.display = 'none';
        $btnNextWave.style.display = '';
    }
}

/* ── Cashout ──────────────────────────────────────────── */

$btnCashout.addEventListener('click', () => {
    if (!confirm('Cash out your points? You will exit The Crypt.')) return;
    $btnCashout.disabled = true;
    fetch(`/crypt/${GAME_ID}/cashout`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
    })
    .then(r => r.json())
    .then(d => {
        if (d.ok) {
            if (d.enoch) setEnoch(d.enoch);
            setTimeout(() => {
                window.location.href = '/crypt';
            }, 2000);
        } else {
            alert(d.error);
            $btnCashout.disabled = false;
        }
    });
});

$btnContinue.addEventListener('click', () => {
    $milestoneBox.style.display = 'none';
    enterPlacement();
});

$btnNextWave.addEventListener('click', () => {
    enterPlacement();
});

/* ═══════════════════════════════════════════════════════
   GAME OVER
   ═══════════════════════════════════════════════════════ */

function showGameOver(d) {
    phase = 'gameover';
    showPanel('gameover');

    if (d.victory) {
        $gameoverTitle.textContent = 'VICTORY — The Crypt is Conquered!';
        $gameoverTitle.classList.add('cr-victory-title');
    } else {
        $gameoverTitle.textContent = 'The Crypt Claims You';
    }

    const stats = document.getElementById('gameoverStats');
    stats.innerHTML = `
        <div class="cr-wd-row"><span>Final Wave</span><strong>${d.final_wave} / ${MAX_WAVES}</strong></div>
        <div class="cr-wd-row"><span>Score</span><strong>${d.final_score}</strong></div>
        <div class="cr-wd-row"><span>Kills</span><strong>${d.final_kills}</strong></div>
        <div class="cr-wd-row"><span>Gold Earned</span><strong>${d.gold_earned}g</strong></div>
        <div class="cr-wd-row"><span>Gold Spent</span><strong>${d.gold_spent}g</strong></div>
    `;

    const ratingChange = d.rating_change || 0;
    const prefix = ratingChange >= 0 ? '+' : '';
    $gameoverRating.innerHTML = `
        <div class="cr-rating-result ${ratingChange >= 0 ? 'cr-rating-pos' : 'cr-rating-neg'}">
            Rating: <strong>${prefix}${ratingChange} points</strong>
        </div>
    `;

    if (d.is_new_best) {
        const badge = document.createElement('div');
        badge.className = 'cr-new-best';
        badge.textContent = '★ New Personal Best! ★';
        stats.prepend(badge);
    }

    const enochDiv = document.getElementById('gameoverEnoch');
    let text = d.enoch || '';
    if (d.enoch_highscore) text += '\n' + d.enoch_highscore;
    enochDiv.textContent = text;
}

/* ═══════════════════════════════════════════════════════
   BOARD CLICK HANDLER (placement mode)
   ═══════════════════════════════════════════════════════ */

$board.addEventListener('click', (e) => {
    if (phase !== 'placement') return;
    const cg = $board.querySelector('cg-board');
    if (!cg) return;
    const rect = cg.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const fileIdx = Math.floor(x / (rect.width / 8));
    const rankIdx = 7 - Math.floor(y / (rect.height / 8));
    if (fileIdx < 0 || fileIdx > 7 || rankIdx < 0 || rankIdx > 7) return;
    const sq = 'abcdefgh'[fileIdx] + (rankIdx + 1);
    onPlacementClick(sq);
});

/* ── Mute button ──────────────────────────────────────── */

const $muteBtn = document.getElementById('cryptMuteBtn');
if ($muteBtn) {
    $muteBtn.addEventListener('click', () => {
        enochMuted = !enochMuted;
        $muteBtn.innerHTML = enochMuted ? '&#128263;' : '&#128264;';
        $muteBtn.title = enochMuted ? 'Unmute Enoch' : 'Mute Enoch';
        if (enochMuted && currentEnochAudio) {
            try { currentEnochAudio.pause(); } catch(e){}
        }
    });
}

/* ═══════════════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════════════ */

updateLadder(wave);

if (phase === 'placement') {
    enterPlacement();
} else if (phase === 'battle' && cfg.fen) {
    showPanel('battle');
    ground.set({ fen: cfg.fen, turnColor: 'white' });
    currentLegalMoves = cfg.legalMoves || [];
    enableBattle();
} else if (phase === 'gameover') {
    showPanel('gameover');
    if (cfg.fen) ground.set({ fen: cfg.fen });
}
