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
let preMovefen = null;
let _audioUnlocked = false;

function unlockCryptAudio() {
    if (_audioUnlocked) return;
    _audioUnlocked = true;
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        if (ctx.state === 'suspended') ctx.resume();
        const buf = ctx.createBuffer(1, 1, 22050);
        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ctx.destination);
        src.start(0);
    } catch(e) {}
    if (cryptAmbient._a && !cryptAmbient._a.paused) return;
    if (cryptAmbient._a && !enochMuted) {
        cryptAmbient._a.play().catch(() => {});
    }
}

document.addEventListener('click', unlockCryptAudio, { once: true });
document.addEventListener('touchstart', unlockCryptAudio, { once: true });
document.addEventListener('keydown', unlockCryptAudio, { once: true });

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
const $invStrip   = document.getElementById('inventoryStrip');
const $boardActions = document.getElementById('boardActions');
const $btnDeploy  = document.getElementById('btnDeploy');
const $btnAbandon = document.getElementById('btnAbandon');
const $btnArmory  = document.getElementById('btnArmory');
const $armoryOverlay = document.getElementById('armoryOverlay');
const $armoryClose = document.getElementById('armoryClose');
const $armoryGold  = document.getElementById('armoryGold');
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
const $cascadeIntro = document.getElementById('cascadeIntro');
const $cascadeBonusMsg = document.getElementById('cascadeBonusMsg');
const $btnStartCascade = document.getElementById('btnStartCascade');
const $cascadeHud = document.getElementById('cascadeHud');
const $cascadeBar = document.getElementById('cascadeBar');
const $cascadeTickCount = document.getElementById('cascadeTickCount');

let cascadeTimer = null;
let cascadeInterval = 1500;
let cascadeMaxTicks = 20;
let cascadeTick = 0;
let cascadePaused = false;

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

/* ── Crypt Ambient Music (crossfade looper) ──────────── */

const XFADE = 2.0;

const cryptAmbient = {
    normalSrc: null,
    bossSrc: null,
    cascadeSrc: null,
    ghostHowl: null,
    activeKey: null,
    playing: false,
    _a: null,
    _b: null,
    _raf: null,
    _howlTimer: null,
};

function _makeAudio(src, vol) {
    const a = new Audio(src);
    a.preload = 'auto';
    a.volume = vol;
    return a;
}

function initAmbientAudio() {
    const base = (window.STATIC_BASE || '/static/') + 'audio/crypt/';
    cryptAmbient.normalSrc  = base + 'ambient_loop.mp3';
    cryptAmbient.bossSrc    = base + 'boss_ambient.mp3';
    cryptAmbient.cascadeSrc = base + 'cascade_intense.mp3';

    cryptAmbient.ghostHowl = new Audio(base + 'ghost_howl.mp3');
    cryptAmbient.ghostHowl.preload = 'auto';
    cryptAmbient.ghostHowl.volume = 0.15;
}
initAmbientAudio();

function _ambientVol(key) {
    if (key === 'boss') return 0.3;
    if (key === 'cascade') return 0.35;
    return 0.25;
}

function _ambientSrc(key) {
    if (key === 'boss') return cryptAmbient.bossSrc;
    if (key === 'cascade') return cryptAmbient.cascadeSrc;
    return cryptAmbient.normalSrc;
}

function _tickCrossfade() {
    const a = cryptAmbient._a;
    if (!a || a.paused || !a.duration) {
        cryptAmbient._raf = requestAnimationFrame(_tickCrossfade);
        return;
    }
    const remaining = a.duration - a.currentTime;
    if (remaining <= XFADE && remaining > 0) {
        if (!cryptAmbient._b) {
            const key = cryptAmbient.activeKey;
            const src = _ambientSrc(key);
            const vol = _ambientVol(key);
            const b = _makeAudio(src, 0);
            b.currentTime = 0;
            b.play().catch(() => {});
            cryptAmbient._b = b;
        }
        const t = 1 - (remaining / XFADE);
        const vol = _ambientVol(cryptAmbient.activeKey);
        a.volume = vol * (1 - t);
        cryptAmbient._b.volume = vol * t;
    }
    if (a.ended || a.currentTime >= a.duration - 0.05) {
        a.pause();
        if (cryptAmbient._b) {
            cryptAmbient._b.volume = _ambientVol(cryptAmbient.activeKey);
            cryptAmbient._a = cryptAmbient._b;
            cryptAmbient._b = null;
        }
    }
    cryptAmbient._raf = requestAnimationFrame(_tickCrossfade);
}

function startAmbient(keyOrBoss) {
    stopAmbient();
    const key = (typeof keyOrBoss === 'string') ? keyOrBoss : (keyOrBoss ? 'boss' : 'normal');
    const src = _ambientSrc(key);
    const vol = _ambientVol(key);

    cryptAmbient.activeKey = key;
    cryptAmbient.playing = true;
    cryptAmbient._a = _makeAudio(src, vol);
    cryptAmbient._a.currentTime = 0;
    if (!enochMuted) {
        cryptAmbient._a.play().catch(() => {});
    }
    cryptAmbient._raf = requestAnimationFrame(_tickCrossfade);
    scheduleGhostHowl();
    scheduleLightning();
}

function resumeAmbient(keyOrBoss) {
    const key = (typeof keyOrBoss === 'string') ? keyOrBoss : (keyOrBoss ? 'boss' : 'normal');
    if (cryptAmbient.activeKey === key && cryptAmbient.playing && cryptAmbient._a && !cryptAmbient._a.paused) return;
    if (cryptAmbient.activeKey === key && cryptAmbient._a && cryptAmbient._a.paused && !enochMuted) {
        cryptAmbient._a.play().catch(() => {});
        cryptAmbient.playing = true;
        if (!cryptAmbient._raf) cryptAmbient._raf = requestAnimationFrame(_tickCrossfade);
        return;
    }
    startAmbient(key);
}

function _pauseAmbientAudio() {
    if (cryptAmbient._a) try { cryptAmbient._a.pause(); } catch(e) {}
    if (cryptAmbient._b) try { cryptAmbient._b.pause(); } catch(e) {}
}

function _resumeAmbientAudio() {
    if (cryptAmbient._a) cryptAmbient._a.play().catch(() => {});
}

function stopAmbient() {
    _pauseAmbientAudio();
    if (cryptAmbient._a) { cryptAmbient._a.src = ''; cryptAmbient._a = null; }
    if (cryptAmbient._b) { cryptAmbient._b.src = ''; cryptAmbient._b = null; }
    if (cryptAmbient._raf) { cancelAnimationFrame(cryptAmbient._raf); cryptAmbient._raf = null; }
    cryptAmbient.activeKey = null;
    cryptAmbient.playing = false;
    if (cryptAmbient._howlTimer) {
        clearTimeout(cryptAmbient._howlTimer);
        cryptAmbient._howlTimer = null;
    }
    stopLightning();
}

function scheduleGhostHowl() {
    const delay = 15000 + Math.random() * 30000;
    cryptAmbient._howlTimer = setTimeout(() => {
        if (!enochMuted && cryptAmbient.playing && cryptAmbient._a && !cryptAmbient._a.paused) {
            const howl = cryptAmbient.ghostHowl;
            howl.currentTime = 0;
            howl.play().catch(() => {});
        }
        if (cryptAmbient.playing) scheduleGhostHowl();
    }, delay);
}

/* ── Lightning & Thunder ──────────────────────────────── */

const thunderSounds = [];
let _lightningTimer = null;
const _lightningOverlay = document.createElement('div');
_lightningOverlay.className = 'cr-lightning-overlay';
document.body.appendChild(_lightningOverlay);

function initThunderAudio() {
    const base = (window.STATIC_BASE || '/static/') + 'audio/crypt/';
    const files = ['thunder_close.mp3', 'thunder_distant.mp3', 'thunder_sharp.mp3'];
    files.forEach(f => {
        const a = new Audio(base + f);
        a.preload = 'auto';
        a.volume = 0.2;
        thunderSounds.push(a);
    });
}
initThunderAudio();

function triggerLightning() {
    const flashClass = ['flash-1', 'flash-2', 'flash-3'][Math.floor(Math.random() * 3)];
    _lightningOverlay.classList.remove('flash-1', 'flash-2', 'flash-3');
    void _lightningOverlay.offsetWidth;
    _lightningOverlay.classList.add(flashClass);

    if (!enochMuted && thunderSounds.length) {
        const snd = thunderSounds[Math.floor(Math.random() * thunderSounds.length)];
        const delay = 200 + Math.random() * 800;
        setTimeout(() => {
            snd.currentTime = 0;
            snd.volume = 0.12 + Math.random() * 0.15;
            snd.play().catch(() => {});
        }, delay);
    }
}

function scheduleLightning() {
    const delay = 12000 + Math.random() * 25000;
    _lightningTimer = setTimeout(() => {
        if (cryptAmbient.playing && cryptAmbient._a && !cryptAmbient._a.paused) {
            triggerLightning();
        }
        if (cryptAmbient.playing) scheduleLightning();
    }, delay);
}

function stopLightning() {
    if (_lightningTimer) {
        clearTimeout(_lightningTimer);
        _lightningTimer = null;
    }
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

const $placementEnoch = document.getElementById('placementEnochSay');

function setEnoch(text) {
    if (text) {
        if ($enochSay) {
            $enochSay.textContent = text;
            $enochSay.classList.add('cr-enoch-flash');
            setTimeout(() => $enochSay.classList.remove('cr-enoch-flash'), 600);
        }
        if ($placementEnoch) {
            $placementEnoch.textContent = text;
            $placementEnoch.classList.add('cr-enoch-flash');
            setTimeout(() => $placementEnoch.classList.remove('cr-enoch-flash'), 600);
        }
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
    $panelBattle.style.display = (name === 'battle' || name === 'cascade') ? '' : 'none';
    $panelWave.style.display = name === 'wave' ? '' : 'none';
    $panelOver.style.display = name === 'gameover' ? '' : 'none';

    const isPlacement = name === 'placement';
    if ($invStrip) $invStrip.style.display = isPlacement ? '' : 'none';
    if ($boardActions) $boardActions.style.display = isPlacement ? 'flex' : 'none';

    if ($ladderCompact) $ladderCompact.style.display = (name === 'wave') ? '' : 'none';

    if ($cascadeHud) $cascadeHud.style.display = (name === 'cascade') ? '' : 'none';

    if (name !== 'battle' && name !== 'cascade') {
        if ($confirmBar) $confirmBar.style.display = 'none';
        pendingMove = null;
    }
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

/* ── Armory modal ─────────────────────────────────────── */

function openArmory() {
    if ($armoryOverlay) {
        if ($armoryGold) $armoryGold.textContent = gold;
        updateShopButtons();
        $armoryOverlay.style.display = 'flex';
    }
}
function closeArmory() {
    if ($armoryOverlay) $armoryOverlay.style.display = 'none';
}
if ($btnArmory) $btnArmory.addEventListener('click', openArmory);
if ($armoryClose) $armoryClose.addEventListener('click', closeArmory);
if ($armoryOverlay) $armoryOverlay.addEventListener('click', (e) => {
    if (e.target === $armoryOverlay) closeArmory();
});

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
            if ($armoryGold) $armoryGold.textContent = gold;
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
    unlockCryptAudio();
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
    showPanel(data.is_cascade ? 'cascade' : 'battle');
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

    if (data.is_cascade) {
        cascadeInterval = data.cascade_interval || 1500;
        cascadeMaxTicks = data.cascade_max_ticks || 20;
        cascadeTick = 0;
        showCascadeIntro();
    } else {
        enableBattle();
    }
}

/* ═══════════════════════════════════════════════════════
   BATTLE PHASE
   ═══════════════════════════════════════════════════════ */

function enableBattle() {
    phase = 'battle';
    resumeAmbient(wave >= MAX_WAVES);

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

    ground.set({
        movable: { free: false, color: undefined, dests: new Map() },
        draggable: { enabled: false },
    });

    playSound(match.san, false);
    sendMove(uci);
}

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
    stopAmbient();
    stopCascade();
    showPanel('wave');
    updateLadder(d.next_wave);

    const waveCleared = d.wave_cleared || (d.next_wave - 1);

    if (d.victory) {
        $waveDoneTitle.textContent = 'THE CRYPT IS CONQUERED!';
    } else if (d.cascade_survived) {
        $waveDoneTitle.textContent = `Cascade Wave ${waveCleared} Survived!`;
    } else {
        $waveDoneTitle.textContent = `Wave ${waveCleared} Cleared!`;
    }

    let statsHtml = `
        <div class="cr-wd-row"><span>Wave</span><strong>${waveCleared} / ${MAX_WAVES}</strong></div>
        <div class="cr-wd-row"><span>Bonus Gold</span><strong>+${d.bonus_gold || 0}g</strong></div>
        <div class="cr-wd-row"><span>Bonus Score</span><strong>+${d.bonus_score || 0}</strong></div>
        <div class="cr-wd-row"><span>Total Gold</span><strong>${d.gold}g</strong></div>
        <div class="cr-wd-row"><span>Total Score</span><strong>${d.score}</strong></div>
    `;
    if (d.next_is_cascade && d.cascade_bonus_pieces && d.cascade_bonus_pieces.length) {
        const labels = {Q:'Queen', N:'Knight', B:'Bishop', R:'Rook', P:'Pawn'};
        const names = d.cascade_bonus_pieces.map(p => labels[p] || p).join(', ');
        statsHtml += `<div class="cr-wd-row" style="color:#4d4;font-weight:700"><span>Cascade Bonus</span><strong>+${names}</strong></div>`;
    }

    const stats = document.getElementById('waveDoneStats');
    stats.innerHTML = statsHtml;

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
    stopAmbient();
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
        $muteBtn.title = enochMuted ? 'Unmute' : 'Mute';
        if (enochMuted) {
            if (currentEnochAudio) try { currentEnochAudio.pause(); } catch(e){}
            _pauseAmbientAudio();
            if (cryptAmbient.ghostHowl) try { cryptAmbient.ghostHowl.pause(); } catch(e){}
            thunderSounds.forEach(s => { try { s.pause(); } catch(e){} });
        } else {
            if (cryptAmbient.playing && (phase === 'battle' || phase === 'cascade')) {
                _resumeAmbientAudio();
            }
        }
    });
}

/* ═══════════════════════════════════════════════════════
   CASCADE WAVE MODE
   ═══════════════════════════════════════════════════════ */

function showCascadeIntro() {
    if ($cascadeBonusMsg) {
        $cascadeBonusMsg.textContent = 'Bonus pieces granted: Queen, Knight, Bishop!';
    }
    if ($cascadeIntro) $cascadeIntro.style.display = '';
}

if ($btnStartCascade) {
    $btnStartCascade.addEventListener('click', () => {
        if ($cascadeIntro) $cascadeIntro.style.display = 'none';
        startCascade();
    });
}

function startCascade() {
    phase = 'cascade';
    cascadePaused = false;
    resumeAmbient('cascade');
    showPanel('cascade');
    updateCascadeHud();

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
        events: { move: onCascadePlayerMove },
    });

    scheduleCascadeTick();
}

function onCascadePlayerMove(orig, dest) {
    const match = currentLegalMoves.find(m => m.from === orig && m.to === dest);
    if (!match) return;

    const isPromo = match.promotion && match.promotion !== '';
    let uci = orig + dest;
    if (isPromo) uci += 'q';

    playSound(match.san, false);

    fetch(`/crypt/${GAME_ID}/cascade-move`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({uci}),
    })
    .then(r => r.json())
    .then(d => {
        if (!d.ok) return;

        gold = d.gold;
        score = d.score;
        kills = d.kills;
        updateHud();

        if (d.enoch) setEnoch(d.enoch);

        if (d.wave_complete) {
            stopCascade();
            showWaveComplete(d);
            return;
        }
        if (d.game_over) {
            stopCascade();
            showGameOver(d);
            return;
        }

        ground.set({ fen: d.fen, turnColor: 'white' });
        currentLegalMoves = d.legal_moves || [];
        ground.set({
            movable: {
                free: false,
                color: 'white',
                dests: buildDests(currentLegalMoves),
                showDests: true,
            },
            events: { move: onCascadePlayerMove },
        });
    });
}

function scheduleCascadeTick() {
    if (cascadeTimer) clearTimeout(cascadeTimer);
    cascadeTimer = setTimeout(doCascadeTick, cascadeInterval);
}

function doCascadeTick() {
    if (phase !== 'cascade' || cascadePaused) return;

    fetch(`/crypt/${GAME_ID}/cascade-tick`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
    })
    .then(r => r.json())
    .then(d => {
        if (!d.ok) return;

        cascadeTick = d.tick;
        cascadeMaxTicks = d.max_ticks;
        gold = d.gold;
        score = d.score;
        kills = d.kills;
        updateHud();
        updateCascadeHud();

        if (d.enoch) setEnoch(d.enoch);

        if (d.ai_move) {
            ground.set({
                fen: d.fen,
                lastMove: [d.ai_move.from, d.ai_move.to],
                turnColor: 'white',
            });
            playSound(d.ai_move.san, false);
        } else {
            ground.set({ fen: d.fen, turnColor: 'white' });
        }

        if (d.spawned) {
            setTimeout(() => {
                const m = new Map();
                m.set(d.spawned.square, { role: SYM_TO_ROLE[d.spawned.piece], color: 'black' });
                ground.setPieces(m, false);
                playSound(null);
            }, 200);
        }

        if (d.wave_complete) {
            stopCascade();
            showWaveComplete(d);
            return;
        }
        if (d.game_over) {
            stopCascade();
            showGameOver(d);
            return;
        }

        currentLegalMoves = d.legal_moves || [];
        ground.set({
            movable: {
                free: false,
                color: 'white',
                dests: buildDests(currentLegalMoves),
                showDests: true,
            },
            events: { move: onCascadePlayerMove },
        });

        scheduleCascadeTick();
    });
}

function stopCascade() {
    if (cascadeTimer) {
        clearTimeout(cascadeTimer);
        cascadeTimer = null;
    }
    cascadePaused = true;
    if ($cascadeHud) $cascadeHud.style.display = 'none';
}

function updateCascadeHud() {
    if (!$cascadeBar || !$cascadeTickCount) return;
    const pct = cascadeMaxTicks > 0 ? Math.min(100, (cascadeTick / cascadeMaxTicks) * 100) : 0;
    $cascadeBar.style.width = pct + '%';
    $cascadeTickCount.textContent = `${cascadeTick} / ${cascadeMaxTicks}`;
}


/* ═══════════════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════════════ */

if (phase === 'placement') {
    enterPlacement();
} else if (phase === 'battle' && cfg.fen) {
    showPanel('battle');
    ground.set({ fen: cfg.fen, turnColor: 'white' });
    currentLegalMoves = cfg.legalMoves || [];
    enableBattle();
} else if (phase === 'cascade' && cfg.fen) {
    showPanel('cascade');
    ground.set({ fen: cfg.fen, turnColor: 'white' });
    currentLegalMoves = cfg.legalMoves || [];
    if (cfg.cascadeConf) {
        cascadeInterval = cfg.cascadeConf.interval;
        cascadeMaxTicks = cfg.cascadeConf.maxTicks;
        cascadeTick = cfg.cascadeConf.tick;
    }
    showCascadeIntro();
} else if (phase === 'gameover') {
    showPanel('gameover');
    if (cfg.fen) ground.set({ fen: cfg.fen });
}
