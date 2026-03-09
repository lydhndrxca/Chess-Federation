/* The Reckoning — four-player chess UI */
(function () {
    'use strict';

    /* ── Audio System ───────────────────────────────────────────── */
    var rkAudioMap = null;
    var rkAudioQueue = [];
    var rkAudioPlaying = false;
    var rkMuted = localStorage.getItem('rkEnochMuted') === 'true';
    var rkAudioUnlocked = false;

    function rkUnlockAudio() {
        if (rkAudioUnlocked) return;
        rkAudioUnlocked = true;
        try {
            var ctx = new (window.AudioContext || window.webkitAudioContext)();
            if (ctx.state === 'suspended') ctx.resume();
            var buf = ctx.createBuffer(1, 1, 22050);
            var src = ctx.createBufferSource();
            src.buffer = buf;
            src.connect(ctx.destination);
            src.start(0);
        } catch (e) {}
    }

    function rkLoadManifest() {
        var cfg = window.RK_AUDIO_CONFIG;
        if (!cfg || !cfg.manifestUrl) return Promise.resolve();
        var base = cfg.audioBase || '/static/audio/enoch/';
        var loader = (window.EnochCache && window.EnochCache.getManifest)
            ? window.EnochCache.getManifest(cfg.manifestUrl, cfg.manifestVersion || '1')
            : fetch(cfg.manifestUrl).then(function (r) { return r.json(); });
        return loader
            .then(function (manifest) {
                rkAudioMap = {};
                for (var key in manifest) {
                    if (key.indexOf('reckoning/') === 0) {
                        rkAudioMap[manifest[key].text] = base + manifest[key].file;
                    }
                }
            })
            .catch(function () {});
    }

    function rkDrainQueue() {
        if (rkAudioPlaying || rkMuted || rkAudioQueue.length === 0) return;
        var url = rkAudioQueue.shift();
        rkAudioPlaying = true;

        var play = function (audio) {
            var done = function () {
                audio.removeEventListener('ended', done);
                audio.removeEventListener('error', done);
                rkAudioPlaying = false;
                rkDrainQueue();
            };
            audio.addEventListener('ended', done);
            audio.addEventListener('error', done);
            audio.play().catch(function () { done(); });
        };

        if (window.EnochCache) {
            window.EnochCache.getAudio(url).then(play).catch(function () {
                rkAudioPlaying = false;
                rkDrainQueue();
            });
        } else {
            play(new Audio(url));
        }
    }

    function rkPlayLine(text) {
        if (rkMuted || !rkAudioMap || !text) return;
        var url = rkAudioMap[text];
        if (!url) return;
        rkAudioQueue.push(url);
        if (rkAudioQueue.length > 2) rkAudioQueue.splice(0, rkAudioQueue.length - 2);
        rkDrainQueue();
    }

    function rkShowCommentary(text) {
        if (!text) return;
        var bar = document.getElementById('rkEnochBar');
        var textEl = document.getElementById('rkEnochText');
        if (!bar || !textEl) return;
        textEl.textContent = '"' + text + '"';
        bar.style.display = 'flex';
        bar.classList.remove('rk-enoch-fade');
        void bar.offsetWidth;
        bar.classList.add('rk-enoch-fade');
        rkPlayLine(text);
    }

    /* ── Mute button ── */
    var muteBtn = document.getElementById('rkMuteBtn');
    if (muteBtn) {
        muteBtn.textContent = rkMuted ? '\uD83D\uDD07' : '\uD83D\uDD08';
        muteBtn.addEventListener('click', function () {
            rkMuted = !rkMuted;
            localStorage.setItem('rkEnochMuted', rkMuted ? 'true' : 'false');
            muteBtn.textContent = rkMuted ? '\uD83D\uDD07' : '\uD83D\uDD08';
        });
    }

    document.addEventListener('click', rkUnlockAudio, { once: true });
    document.addEventListener('touchstart', rkUnlockAudio, { once: true });

    var container = document.getElementById('rkGame');
    if (!container) {
        var joinBtn = document.getElementById('btnJoinReckoning');
        if (joinBtn) {
            joinBtn.addEventListener('click', function () {
                joinBtn.disabled = true;
                joinBtn.textContent = 'Descending\u2026';
                fetch('/reckoning/join', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                })
                    .then(function (r) { return r.json(); })
                    .then(function (d) {
                        if (d.url) window.location.href = d.url;
                        else {
                            alert(d.error || 'Failed');
                            joinBtn.disabled = false;
                            joinBtn.textContent = 'Take a Seat';
                        }
                    });
            });
        }

        var waitingEl = document.getElementById('rkWaiting');
        if (waitingEl) {
            var waitGameId = waitingEl.dataset.gameId;
            (function pollWaiting() {
                fetch('/reckoning/' + waitGameId + '/state')
                    .then(function (r) { return r.json(); })
                    .then(function (d) {
                        if (d.status === 'active') {
                            window.location.reload();
                            return;
                        }
                        setTimeout(pollWaiting, 3000);
                    })
                    .catch(function () { setTimeout(pollWaiting, 5000); });
            })();
        }
        return;
    }

    rkLoadManifest();

    var gameId = container.dataset.gameId;
    var mySeat = container.dataset.mySeat || null;
    var currentTurn = container.dataset.currentTurn;
    var gameStatus = container.dataset.status;
    var legalMoves = {};
    try { legalMoves = JSON.parse(container.dataset.legal || '{}'); } catch (e) {}

    var board = document.getElementById('rkBoard');
    var statusEl = document.getElementById('rkStatus');
    var logEl = document.getElementById('rkLog');
    var selectedSq = null;
    var highlightedCells = [];
    var mcEl = container.querySelector('.rk-move-count');
    var lastMoveCount = mcEl ? parseInt(mcEl.textContent.replace('#', ''), 10) || 0 : 0;

    var COLOR_CSS = {
        south: '#f5f5f5', west: '#4a9eff',
        north: '#f0c040', east: '#ff5252',
    };

    /* ── Selection & move highlights ────────────────────────────── */

    board.addEventListener('click', function (e) {
        if (gameStatus !== 'active' || mySeat !== currentTurn) return;

        var cell = e.target.closest('.rk-cell-sq');
        if (!cell) return;
        var r = cell.dataset.r, c = cell.dataset.c;
        var key = r + ',' + c;

        if (selectedSq && isLegalTarget(selectedSq, key)) {
            sendMove(selectedSq, key);
            clearHighlights();
            selectedSq = null;
            return;
        }

        clearHighlights();
        if (legalMoves[key]) {
            selectedSq = key;
            cell.classList.add('rk-cell-selected');
            highlightedCells.push(cell);

            legalMoves[key].forEach(function (ms) {
                var parts = ms.split('-');
                var dest = parts[1].split('=')[0];
                var dr = dest.split(',')[0], dc = dest.split(',')[1];
                var destCell = board.querySelector('[data-r="' + dr + '"][data-c="' + dc + '"]');
                if (destCell) {
                    destCell.classList.add('rk-cell-legal');
                    highlightedCells.push(destCell);
                }
            });
        } else {
            selectedSq = null;
        }
    });

    function isLegalTarget(fromKey, toKey) {
        if (!legalMoves[fromKey]) return false;
        return legalMoves[fromKey].some(function (ms) {
            var dest = ms.split('-')[1].split('=')[0];
            return dest === toKey;
        });
    }

    function clearHighlights() {
        highlightedCells.forEach(function (el) {
            el.classList.remove('rk-cell-selected', 'rk-cell-legal');
        });
        highlightedCells = [];
    }

    /* ── Send move ──────────────────────────────────────────────── */

    function sendMove(fromKey, toKey) {
        var moveStr = fromKey + '-' + toKey;
        var matching = (legalMoves[fromKey] || []).filter(function (ms) {
            return ms.split('-')[1].split('=')[0] === toKey;
        });

        if (matching.length > 1) {
            var promos = matching.map(function (ms) {
                var eq = ms.indexOf('=');
                return eq >= 0 ? ms.substring(eq + 1) : '';
            }).filter(Boolean);
            if (promos.length > 0) {
                moveStr = fromKey + '-' + toKey + '=Q';
            }
        } else if (matching.length === 1 && matching[0].indexOf('=') >= 0) {
            moveStr = matching[0];
        }

        statusEl.innerHTML = '<span class="rk-status-wait">Submitting\u2026</span>';

        fetch('/reckoning/' + gameId + '/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ move: moveStr }),
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    statusEl.innerHTML = '<span class="rk-status-turn">' + data.error + '</span>';
                    return;
                }
                if (data.state) applyState(data.state);
                if (data.recent_moves) addRecentMoves(data.recent_moves, true);
                if (data.game_over) {
                    gameStatus = 'completed';
                    window.location.reload();
                }
            })
            .catch(function () {
                statusEl.innerHTML = '<span class="rk-status-turn">Error — try again</span>';
            });
    }

    /* ── State application (from poll or move response) ─────────── */

    function applyState(st) {
        currentTurn = st.turn;
        legalMoves = st.legal || {};

        redrawBoard(st.grid);
        updatePlayers(st);
        updateStatus(st);

        var matEl;
        for (var color in st.material) {
            matEl = document.getElementById('rkMat-' + color);
            if (matEl) matEl.textContent = st.material[color];
        }
    }

    function redrawBoard(grid) {
        var cells = board.querySelectorAll('.rk-cell');
        var idx = 0;
        for (var i = 0; i < grid.length; i++) {
            for (var j = 0; j < grid[i].length; j++) {
                var cell = cells[idx++];
                if (!cell) continue;
                var data = grid[i][j];
                if (data === null) continue;

                var existing = cell.querySelector('.rk-piece');
                if (existing) existing.remove();

                if (data && !data.empty && data.code) {
                    var span = document.createElement('span');
                    span.className = 'rk-piece rk-piece-' + data.color;
                    span.dataset.code = data.code;
                    span.textContent = data.symbol;
                    cell.appendChild(span);
                }
            }
        }
    }

    function updatePlayers(st) {
        ['south', 'west', 'north', 'east'].forEach(function (seat) {
            var el = document.getElementById('rkPlayer-' + seat);
            if (!el) return;
            el.classList.toggle('rk-player-turn', st.turn === seat && gameStatus === 'active');
            el.classList.toggle('rk-player-eliminated', st.eliminated.indexOf(seat) >= 0);

            var indicator = el.querySelector('.rk-turn-indicator');
            if (indicator) indicator.style.display = st.turn === seat ? '' : 'none';
        });
    }

    function updateStatus(st) {
        if (gameStatus === 'completed') {
            statusEl.innerHTML = '<span class="rk-status-done">The Reckoning is complete.</span>';
        } else if (mySeat && mySeat === st.turn) {
            statusEl.innerHTML = '<span class="rk-status-turn">Your move (' + capitalize(mySeat) + ')</span>';
        } else {
            statusEl.innerHTML = '<span class="rk-status-wait">' + capitalize(st.turn) + '\'s turn\u2026</span>';
        }
    }

    function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

    /* ── Polling ────────────────────────────────────────────────── */

    function poll() {
        if (gameStatus === 'completed') return;

        fetch('/reckoning/' + gameId + '/state')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.status === 'active' && data.state) {
                    if (data.move_count !== lastMoveCount) {
                        lastMoveCount = data.move_count;
                        applyState(data.state);
                        addRecentMoves(data.recent_moves, true);
                    }
                }
                if (data.game_over) {
                    gameStatus = 'completed';
                    window.location.reload();
                    return;
                }
                if (data.status === 'waiting') {
                    if (data.filled_seats >= 4) {
                        window.location.reload();
                        return;
                    }
                }
                setTimeout(poll, 3000);
            })
            .catch(function () { setTimeout(poll, 5000); });
    }

    function addRecentMoves(moves, playLatest) {
        if (!moves || !logEl) return;
        logEl.innerHTML = '';
        moves.forEach(function (m, idx) {
            var div = document.createElement('div');
            div.className = 'rk-log-entry';
            div.innerHTML =
                '<span class="rk-log-num">' + m.number + '.</span>' +
                '<span class="rk-log-color" style="color:' + (COLOR_CSS[m.color] || '#aaa') + '">' + capitalize(m.color) + '</span>' +
                '<span class="rk-log-move">' + m.move_str + '</span>' +
                (m.commentary ? '<span class="rk-log-commentary">"' + m.commentary + '"</span>' : '');
            logEl.appendChild(div);
        });
        if (playLatest && moves.length > 0) {
            var latest = moves[moves.length - 1];
            if (latest.commentary) rkShowCommentary(latest.commentary);
        }
    }

    if (gameStatus === 'active' || gameStatus === 'waiting') {
        setTimeout(poll, 3000);
    }

    /* ── Zoom controls ─────────────────────────────────────────── */

    var rkBoardEl = document.getElementById('rkBoard');
    var rkBoardWrap = document.getElementById('rkBoardWrap');
    var rkZoomIn = document.getElementById('rkZoomIn');
    var rkZoomOut = document.getElementById('rkZoomOut');
    var rkZoomReset = document.getElementById('rkZoomReset');
    var zoomLevel = 1;
    var ZOOM_MIN = 1;
    var ZOOM_MAX = 2.5;
    var ZOOM_STEP = 0.25;

    function applyZoom() {
        if (!rkBoardEl) return;
        rkBoardEl.style.transform = 'scale(' + zoomLevel + ')';
        if (zoomLevel > 1) {
            rkBoardEl.style.width = 'min(100%, 560px)';
            if (rkBoardWrap) rkBoardWrap.style.overflow = 'auto';
        } else {
            if (rkBoardWrap) rkBoardWrap.style.overflow = 'auto';
        }
    }

    if (rkZoomIn) rkZoomIn.addEventListener('click', function () {
        zoomLevel = Math.min(ZOOM_MAX, zoomLevel + ZOOM_STEP);
        applyZoom();
    });
    if (rkZoomOut) rkZoomOut.addEventListener('click', function () {
        zoomLevel = Math.max(ZOOM_MIN, zoomLevel - ZOOM_STEP);
        applyZoom();
    });
    if (rkZoomReset) rkZoomReset.addEventListener('click', function () {
        zoomLevel = 1;
        applyZoom();
    });
})();
