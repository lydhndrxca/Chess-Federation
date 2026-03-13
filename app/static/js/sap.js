/* Spectacle Lake — Enoch's Maple Forest
   Zelda-style exploration + tap-to-kill harvest defense */
(function () {
    'use strict';

    var C = window.SAP_CONFIG;
    var GRID = 10, SCREENS = 5, MAP = GRID * SCREENS;
    var HARVEST_BASE = 30000;

    // ── audio system ────────────────────────────────────
    var sapAudioMap = {};
    var sapAudioQueue = [];
    var sapAudioPlaying = false;
    var sapManifestReady = false;

    function sapLoadManifest() {
        if (!C.manifestUrl) return Promise.resolve();
        return fetch(C.manifestUrl)
            .then(function (r) { return r.json(); })
            .then(function (manifest) {
                var base = C.audioBase || '';
                Object.keys(manifest).forEach(function (key) {
                    if (key.indexOf('sap_') === 0) {
                        sapAudioMap[manifest[key].text] = base + manifest[key].file;
                    }
                });
                sapManifestReady = true;
            })
            .catch(function () {});
    }

    function sapPlayLine(text) {
        var url = sapAudioMap[text];
        if (!url) return;
        sapAudioQueue.push(url);
        if (!sapAudioPlaying) sapPlayNext();
    }

    function sapPlayNext() {
        if (!sapAudioQueue.length) { sapAudioPlaying = false; return; }
        sapAudioPlaying = true;
        var url = sapAudioQueue.shift();
        var audio = new Audio(url);
        audio.volume = 0.8;
        audio.onended = function () { sapPlayNext(); };
        audio.onerror = function () { sapPlayNext(); };
        audio.play().catch(function () { sapPlayNext(); });
    }
    var QUEEN_CHAR = '♛';
    var TREE_CHAR = '🌲';
    var CABIN_CHAR = '🏠';
    var MERCHANT_CHAR = '🏪';
    var NPC_CHARS = ['♟','♙'];
    var ENEMY_POOL = ['♟','♞','♝','♜'];

    // ── seeded PRNG ─────────────────────────────────────
    var _seed = C.seed;
    function rng() {
        _seed = (_seed * 16807 + 0) % 2147483647;
        return (_seed - 1) / 2147483646;
    }
    function rngInt(min, max) { return Math.floor(rng() * (max - min + 1)) + min; }

    // ── NPC & Enoch dialogue ────────────────────────────
    var NPC_ENCOUNTERS = [
        ["Oh! A visitor! I've been counting pinecones all morning. I'm up to eleven.","That sounds peaceful.","Why pinecones?","It IS peaceful. The squirrels don't judge. Not like HIM down there.","He told me to. Said every pinecone is a soul. I don't ask questions anymore."],
        ["Shh! I'm listening to the sap move inside the tree. You can hear it if you press your ear real close.","I'll try that.","That's weird.","It sounds like a tiny river! A river that goes UP. Isn't that wonderful?","Maybe. But the trees don't think so. They told me you'd say that."],
        ["Hello friend! Would you like a leaf? I collected the best ones today.","Sure, I'll take one.","No thanks.","Here! This one looks like a hand waving. I named it Gerald.","Oh. That's okay. Gerald doesn't mind. Gerald doesn't mind anything."],
        ["I built a tiny house out of bark! It has a door and everything. Want to see?","Show me!","Maybe later.","Look! The door even opens! I put a beetle inside. He's the mayor.","The mayor will be disappointed. He prepared a speech."],
        ["Do you ever wonder what clouds taste like? I think they taste like cold bread.","Cold bread?","I don't think about clouds.","Yes! The kind that's been in the cellar too long. But in a nice way.","Oh. I think about them all the time. Every single one has a name."],
        ["I found a feather yesterday! A real one! From a real bird! Probably!","That's great!","Are you sure it's real?","I know! I'm going to use it to write important things. Like 'hello' and 'tree'.","Well... it FEELS real. And isn't that what matters? That's what the moth said."],
        ["The mushrooms here glow at night. Not bright, just... enough to read by.","What do you read?","That sounds eerie.","The same note, over and over. It says 'YOU ARE SAFE HERE.' I believe it.","Not eerie. Cozy. Everything down — I mean, out HERE — is cozy."],
        ["I used to live somewhere darker. But I can't remember where. Isn't that nice?","I'm glad you're happier now.","Doesn't that worry you?","Me too! The sunlight here is warm. It doesn't flicker like candles.","Worry? No. Worrying is for places with stone walls. This is a FOREST."],
        ["Would you like to hear a song? I only know one note, but I sing it very well.","Let's hear it.","One note isn't a song.","Laaaaaaaaaa! ... Thank you for listening. You're my favorite audience.","It is if you mean it hard enough. That's what the owl told me before it left."],
        ["I planted a seed here last week. Nothing's grown yet, but I check every day.","I hope it grows.","It might be dead.","It WILL grow! I can feel it thinking about it down there in the dirt.","No! Seeds are just... patient. Very, very patient. Like me."],
        ["There's a stream nearby that runs backwards sometimes. Only when no one's watching.","How would you know if no one's watching?","Streams don't run backwards.","I... hm. You're cleverer than the last visitor. The deer didn't ask that.","THIS one does. It told me so. In bubbles."],
        ["I keep a collection of nice stones. This one is my favorite. It's warm.","Can I hold it?","It's just a rock.","Careful! It... it means a lot to me. It was a gift. From someone below.","To you, maybe. To me, it remembers where it's been. All rocks do."],
        ["The trees whisper to each other at dusk. I've been learning their language.","What do they say?","Trees can't talk.","Mostly 'stay' and 'grow' and 'he's coming.' I try not to think about the last one.","Not with mouths. With roots. Everything important happens underground."],
        ["I made a crown out of twigs! Look! Am I a king now?","You are the king of this clearing!","Crowns are for people with kingdoms.","Ha! I decree that all acorns shall be free! This is the best day!","My kingdom is this patch of moss. That's enough. Some kingdoms are too big."],
        ["Something left footprints near my favorite stump. Big ones. I put flowers in them.","What kind of footprints?","That was brave.","The kind without toes. Like something was dragged. But the flowers make it better.","Brave? Or... I just don't want to think about what made them. The flowers help."],
        ["I've been here so long I forgot what rain feels like. Does it still happen?","It rains all the time.","I'm not sure anymore.","How wonderful! I only get the dew. The dew is gentle. Rain sounds exciting.","Exactly. Some things just... stop. And that's okay. The sun is reliable."],
        ["Want to play a game? I hide behind the tree, and you pretend you can't see me.","Okay, I'll play!","I can still see you.","*giggling from behind tree* You're very good at pretending! Best game ever!","That's... that's the whole point. Pretending is the best part of everything."],
        ["The fireflies spelled out a word last night. I think it was 'STAY.'","That's beautiful.","That's creepy.","I thought so too. I'm going to stay. I was always going to stay.","Creepy things can be beautiful. That's what HE always says. From below."],
        ["I drew a map of the forest on a leaf! But the wind took it. So now the wind has a map.","The wind doesn't need a map.","That's actually poetic.","Then it has one for free! Lucky wind!","Thank you! I also wrote a poem once. It was one word: 'moss.' I think it captured everything."],
        ["I found a key buried in the roots. It doesn't fit anything up here. I keep it anyway.","Maybe it fits something below.","Throw it away.","Below... yes. I think it does. I dream about a door sometimes. A heavy one.","No. I'll keep it. Some things are worth holding even when they open nothing."],
    ];

    var HARVEST_FURY = [
        "NO!","MINE!","That sap is MINE!","GET AWAY FROM MY TREE!","STOP TOUCHING IT!",
        "I PLANTED THAT!","THIEF!","Little RAT!","HANDS OFF!","You DARE?!",
        "I'LL DROWN YOU IN MAPLE!","The forest HATES you!","Every drop is MINE!",
        "I can SMELL your greed!","You'll PAY for that!","The roots remember!",
        "GET OUT!","VERMIN!","My PRECIOUS sap!","I waited YEARS for this!",
        "The trees SCREAM!","Leave! LEAVE!","I'll BURY you here!","WRETCHED tapper!",
        "Not ONE drop!","The bark weeps!","BACK! BACK!","From the BASEMENT I send them!",
        "My minions! SWARM!","Choke on amber!","This forest is my KINGDOM!",
        "I found this place FIRST!","Every bucket you fill — I FEEL IT!",
        "The pipes beneath carry MY sap!","Crawl back to your cabin!",
        "The spiders are on MY side!","Drown in maple! DROWN!",
        "You think you can take from ME?!","I've been collecting since BEFORE you!",
        "Each tap is a WOUND!",
    ];

    var HARVEST_SURVIVED = [
        "No... no no no no no...","You... got one. Fine. FINE. It won't happen again.",
        "Enjoy that bucket. It's the last one you'll ever fill.",
        "The forest will remember this theft.","One tree. ONE. The next won't be so easy.",
        "I'm going to find BIGGER pieces next time.",
        "That sap was forty years old. FORTY.",
        "You'll choke on it. Eventually. They all do.",
        "I can hear the tree crying. You monster.",
        "Fine. Take it. But the forest is watching now.",
    ];

    var HARVEST_DEFEATED = [
        "HA! Yes! YES! The forest RECLAIMS!",
        "Down you go. Into the roots. Where you BELONG.",
        "Did you really think you could steal from ME?",
        "The sap stays in the bark. AS IT SHOULD.",
        "Another little thief, consumed by the forest.",
        "I told you. I TOLD you. But you didn't listen.",
        "My pieces! My BEAUTIFUL pieces! They did it!",
        "The maple runs red today. Poetic.",
        "Back to the cabin with NOTHING. Perfect.",
        "The Ledger records: zero buckets. Wonderful.",
    ];

    // ── DOM refs ────────────────────────────────────────
    var grid = document.getElementById('sapGrid');
    var gridWrap = document.getElementById('sapGridWrap');
    var harvestBar = document.getElementById('sapHarvestBar');
    var harvestFill = document.getElementById('sapHarvestFill');
    var lightning = document.getElementById('sapLightning');
    var furyEl = document.getElementById('sapFury');
    var dialogueBox = document.getElementById('sapDialogue');
    var dialogueText = document.getElementById('sapDialogueText');
    var dialogueBtnA = document.getElementById('sapDialogueA');
    var dialogueBtnB = document.getElementById('sapDialogueB');
    var merchantBox = document.getElementById('sapMerchant');
    var merchantItems = document.getElementById('sapMerchantItems');
    var merchantClose = document.getElementById('sapMerchantClose');
    var resultBox = document.getElementById('sapResult');
    var resultTitle = document.getElementById('sapResultTitle');
    var resultText = document.getElementById('sapResultText');
    var resultBtns = document.getElementById('sapResultBtns');
    var startOverlay = document.getElementById('sapStart');
    var startBtn = document.getElementById('sapStartBtn');
    var abilitiesBar = document.getElementById('sapAbilities');
    var hudTrees = document.getElementById('sapTrees');
    var hudRating = document.getElementById('sapRating');
    var hudGold = document.getElementById('sapGold');
    var hudDiff = document.getElementById('sapDifficulty');

    // ── game state ──────────────────────────────────────
    var map = [];           // MAP x MAP tile array
    var entities = [];      // MAP x MAP entity array (null, 'tree', 'npc', 'merchant', 'cabin')
    var visited = [];       // SCREENS x SCREENS
    var harvestedSet = {};  // "x,y" => true
    var talkedSet = {};     // "x,y" => true
    var screenX = 2, screenY = 2;
    var playerX = 5, playerY = 5; // within screen
    var state = 'start';    // start, explore, harvest, dialogue, merchant, result, gameover
    var treesCount = 0;
    var difficulty = C.difficulty;
    var playerAbilities = C.abilities.slice();
    var gold = C.gold;
    var rating = C.rating;
    var enemies = [];       // [{x,y,char,hp}]
    var harvestTimer = null;
    var harvestElapsed = 0;
    var harvestTarget = null; // {x,y}
    var enemyInterval = null;
    var spawnInterval = null;
    var furyInterval = null;
    var lightningInterval = null;
    var hasShield = false;

    // ── map generation ──────────────────────────────────
    function generateMap() {
        var i, j;
        map = [];
        entities = [];
        for (i = 0; i < MAP; i++) {
            map[i] = [];
            entities[i] = [];
            for (j = 0; j < MAP; j++) {
                map[i][j] = 'grass';
                entities[i][j] = null;
            }
        }

        // dense forest patches
        for (i = 0; i < 120; i++) {
            var cx = rngInt(0, MAP - 1), cy = rngInt(0, MAP - 1);
            var size = rngInt(1, 3);
            for (var dx = -size; dx <= size; dx++) {
                for (var dy = -size; dy <= size; dy++) {
                    var nx = cx + dx, ny = cy + dy;
                    if (nx >= 0 && nx < MAP && ny >= 0 && ny < MAP && rng() < 0.6) {
                        map[ny][nx] = 'dense';
                    }
                }
            }
        }

        // water features
        for (i = 0; i < 8; i++) {
            var wx = rngInt(5, MAP - 6), wy = rngInt(5, MAP - 6);
            var wl = rngInt(3, 7);
            var dir = rng() < 0.5 ? 0 : 1;
            for (j = 0; j < wl; j++) {
                var px = dir === 0 ? wx + j : wx;
                var py = dir === 1 ? wy + j : wy;
                if (px < MAP && py < MAP) map[py][px] = 'water';
            }
        }

        // ensure starting screen (2,2) is clear grass
        var sx0 = 2 * GRID, sy0 = 2 * GRID;
        for (i = sy0; i < sy0 + GRID; i++) {
            for (j = sx0; j < sx0 + GRID; j++) {
                map[i][j] = 'grass';
            }
        }

        // cabin at center of starting screen
        entities[sy0 + 5][sx0 + 5] = 'cabin';

        // place trees (15-18)
        var treePlaced = 0;
        var attempts = 0;
        while (treePlaced < 16 && attempts < 500) {
            var tx = rngInt(0, MAP - 1), ty = rngInt(0, MAP - 1);
            var ts = Math.floor(tx / GRID), tr = Math.floor(ty / GRID);
            if (ts === 2 && tr === 2) { attempts++; continue; }
            if (map[ty][tx] === 'grass' && !entities[ty][tx]) {
                entities[ty][tx] = 'tree';
                map[ty][tx] = 'grass';
                treePlaced++;
            }
            attempts++;
        }

        // place NPCs (8-10)
        var npcPlaced = 0;
        attempts = 0;
        while (npcPlaced < 9 && attempts < 400) {
            var nx2 = rngInt(0, MAP - 1), ny2 = rngInt(0, MAP - 1);
            if (map[ny2][nx2] === 'grass' && !entities[ny2][nx2]) {
                entities[ny2][nx2] = 'npc';
                npcPlaced++;
            }
            attempts++;
        }

        // place merchants (2-3)
        var mPlaced = 0;
        attempts = 0;
        while (mPlaced < 2 && attempts < 300) {
            var mx2 = rngInt(0, MAP - 1), my2 = rngInt(0, MAP - 1);
            var ms = Math.floor(mx2 / GRID), mr = Math.floor(my2 / GRID);
            if (ms === 2 && mr === 2) { attempts++; continue; }
            if (map[my2][mx2] === 'grass' && !entities[my2][mx2]) {
                entities[my2][mx2] = 'merchant';
                mPlaced++;
            }
            attempts++;
        }

        // visited screens
        visited = [];
        for (i = 0; i < SCREENS; i++) {
            visited[i] = [];
            for (j = 0; j < SCREENS; j++) visited[i][j] = false;
        }
        visited[2][2] = true;
    }

    // ── rendering ───────────────────────────────────────
    function renderScreen() {
        grid.innerHTML = '';
        var ox = screenX * GRID, oy = screenY * GRID;
        var isVisited = visited[screenY] && visited[screenY][screenX];

        for (var r = 0; r < GRID; r++) {
            for (var c = 0; c < GRID; c++) {
                var cell = document.createElement('div');
                cell.className = 'sap-cell';
                var my = oy + r, mx = ox + c;

                if (!isVisited && !(screenX === screenX && screenY === screenY)) {
                    cell.classList.add('fog');
                    grid.appendChild(cell);
                    continue;
                }

                var tile = map[my] ? map[my][mx] : 'grass';
                var ent = entities[my] ? entities[my][mx] : null;

                if (tile === 'dense') cell.classList.add('dense');
                else if (tile === 'water') cell.classList.add('water');
                else cell.classList.add((r + c) % 2 === 0 ? 'grass' : 'grass-alt');

                if (ent === 'cabin') {
                    cell.classList.add('cabin');
                    cell.innerHTML = '<span class="entity">' + CABIN_CHAR + '</span>';
                } else if (ent === 'tree' && !harvestedSet[mx + ',' + my]) {
                    cell.classList.add('tree-tile');
                    cell.innerHTML = '<span class="entity tree-icon">' + TREE_CHAR + '</span>';
                } else if (ent === 'npc' && !talkedSet[mx + ',' + my]) {
                    cell.innerHTML = '<span class="entity npc">' + NPC_CHARS[rngInt(0,1)] + '</span>';
                } else if (ent === 'merchant') {
                    cell.innerHTML = '<span class="entity merchant-icon">' + MERCHANT_CHAR + '</span>';
                }

                // harvest zone highlight
                if (state === 'harvest' && harvestTarget) {
                    var dist = Math.max(Math.abs(mx - harvestTarget.x), Math.abs(my - harvestTarget.y));
                    if (dist <= 5) {
                        var zone = document.createElement('div');
                        zone.className = 'harvest-zone';
                        cell.appendChild(zone);
                    }
                }

                // player queen
                if (r === playerY && c === playerX) {
                    cell.classList.add('queen-cell');
                    var q = document.createElement('span');
                    q.className = 'entity queen-marker';
                    q.textContent = QUEEN_CHAR;
                    cell.appendChild(q);
                }

                cell.dataset.r = r;
                cell.dataset.c = c;
                grid.appendChild(cell);
            }
        }

        // render enemies on top
        renderEnemies();
    }

    function renderEnemies() {
        // remove old enemy spans
        var old = grid.querySelectorAll('.enemy');
        for (var i = 0; i < old.length; i++) old[i].remove();

        for (var e = 0; e < enemies.length; e++) {
            var en = enemies[e];
            var cellIdx = en.y * GRID + en.x;
            var cell = grid.children[cellIdx];
            if (!cell) continue;
            var sp = document.createElement('span');
            sp.className = 'entity enemy';
            sp.textContent = en.char;
            sp.dataset.eidx = e;
            sp.addEventListener('touchstart', onTapEnemy, { passive: false });
            sp.addEventListener('click', onTapEnemy);
            cell.appendChild(sp);
        }
    }

    function updateHud() {
        hudTrees.textContent = treesCount;
        hudRating.textContent = rating;
        hudGold.textContent = gold;
        hudDiff.textContent = difficulty;
    }

    // ── movement ────────────────────────────────────────
    function canMoveTo(r, c) {
        var my = screenY * GRID + r, mx = screenX * GRID + c;
        if (my < 0 || my >= MAP || mx < 0 || mx >= MAP) return false;
        var tile = map[my][mx];
        return tile !== 'dense' && tile !== 'water';
    }

    function isQueenMove(r, c) {
        if (r === playerY && c === playerX) return false;
        var dr = r - playerY, dc = c - playerX;
        // adjacent only (one step, any direction)
        return Math.abs(dr) <= 1 && Math.abs(dc) <= 1;
    }

    function movePlayer(r, c) {
        playerX = c;
        playerY = r;

        // check screen edges for transition
        var transitioned = false;
        if (playerX < 0 && screenX > 0) { screenX--; playerX = GRID - 1; transitioned = true; }
        if (playerX >= GRID && screenX < SCREENS - 1) { screenX++; playerX = 0; transitioned = true; }
        if (playerY < 0 && screenY > 0) { screenY--; playerY = GRID - 1; transitioned = true; }
        if (playerY >= GRID && screenY < SCREENS - 1) { screenY++; playerY = 0; transitioned = true; }

        if (transitioned) {
            visited[screenY][screenX] = true;
            grid.classList.add('transitioning');
            setTimeout(function () {
                renderScreen();
                grid.classList.remove('transitioning');
            }, 200);
        } else {
            renderScreen();
        }

        checkTileInteraction();
    }

    function checkTileInteraction() {
        var my = screenY * GRID + playerY, mx = screenX * GRID + playerX;
        var ent = entities[my] ? entities[my][mx] : null;

        if (ent === 'npc' && !talkedSet[mx + ',' + my]) {
            showNpcDialogue(mx, my);
        } else if (ent === 'merchant') {
            showMerchant();
        } else {
            checkNearbyTree();
        }
    }

    function checkNearbyTree() {
        var ox = screenX * GRID, oy = screenY * GRID;
        var pmx = ox + playerX, pmy = oy + playerY;

        for (var r = 0; r < GRID; r++) {
            for (var c = 0; c < GRID; c++) {
                var my = oy + r, mx = ox + c;
                var ent = entities[my] ? entities[my][mx] : null;
                if (ent === 'tree' && !harvestedSet[mx + ',' + my]) {
                    var dist = Math.max(Math.abs(pmx - mx), Math.abs(pmy - my));
                    if (dist <= 5) {
                        promptHarvest(mx, my);
                        return;
                    }
                }
            }
        }
    }

    // ── harvest prompt ──────────────────────────────────
    function promptHarvest(tx, ty) {
        state = 'result';
        resultTitle.textContent = '🌲 Begin Harvest?';
        var dur = Math.max(15, HARVEST_BASE / 1000 - (difficulty - 1) * 2);
        resultText.textContent = 'Survive ' + dur + ' seconds near this tree to collect sap.\nEnoch will send his pieces. Tap them to survive.';
        resultBtns.innerHTML = '';
        var btn = document.createElement('button');
        btn.className = 'sap-result-btn continue';
        btn.textContent = 'Harvest!';
        btn.addEventListener('click', function () {
            resultBox.style.display = 'none';
            startHarvest(tx, ty);
        });
        resultBtns.appendChild(btn);
        var skip = document.createElement('button');
        skip.className = 'sap-result-btn cashout';
        skip.textContent = 'Not yet';
        skip.addEventListener('click', function () {
            resultBox.style.display = 'none';
            state = 'explore';
        });
        resultBtns.appendChild(skip);
        resultBox.style.display = 'flex';
    }

    // ── harvest mode ────────────────────────────────────
    function startHarvest(tx, ty) {
        state = 'harvest';
        harvestTarget = { x: tx, y: ty };
        enemies = [];
        harvestElapsed = 0;
        hasShield = playerAbilities.indexOf('bark_shield') >= 0;
        gridWrap.classList.add('storm');
        harvestBar.style.display = '';

        var harvestDuration = Math.max(15000, HARVEST_BASE - (difficulty - 1) * 2000);

        // check abilities
        if (playerAbilities.indexOf('quick_tap') >= 0) {
            harvestDuration -= 8000;
            removeAbility('quick_tap');
        }

        var enemySpeed = Math.max(400, 1200 - difficulty * 80);
        var spawnRate = Math.max(500, 2000 - difficulty * 150);

        renderScreen();

        // spawn enemies
        spawnInterval = setInterval(function () {
            spawnEnemy();
        }, spawnRate);

        // move enemies
        var slowMult = playerAbilities.indexOf('slow_sap') >= 0 ? 1.4 : 1;
        if (slowMult > 1) removeAbility('slow_sap');
        enemyInterval = setInterval(function () {
            moveEnemies();
        }, Math.round(enemySpeed * slowMult));

        // fury lines
        furyInterval = setInterval(function () {
            showFury();
        }, 2500);

        // lightning
        lightningInterval = setInterval(function () {
            flashLightning();
        }, rngInt(3000, 6000));

        // timer
        var startTime = Date.now();
        harvestTimer = setInterval(function () {
            harvestElapsed = Date.now() - startTime;
            var pct = Math.min(100, (harvestElapsed / harvestDuration) * 100);
            harvestFill.style.width = pct + '%';
            if (harvestElapsed >= harvestDuration) {
                harvestSuccess();
            }
        }, 100);

        // initial spawn burst
        for (var i = 0; i < 2 + difficulty; i++) spawnEnemy();
        showFury();
        flashLightning();
    }

    function spawnEnemy() {
        var edge = rngInt(0, 3);
        var x, y;
        if (edge === 0) { x = rngInt(0, GRID - 1); y = 0; }
        else if (edge === 1) { x = rngInt(0, GRID - 1); y = GRID - 1; }
        else if (edge === 2) { x = 0; y = rngInt(0, GRID - 1); }
        else { x = GRID - 1; y = rngInt(0, GRID - 1); }

        var charIdx = Math.min(Math.floor(difficulty / 3), ENEMY_POOL.length - 1);
        var char = ENEMY_POOL[rngInt(0, charIdx)];
        enemies.push({ x: x, y: y, char: char, hp: 1 });
        renderEnemies();
    }

    function moveEnemies() {
        var changed = false;
        for (var i = enemies.length - 1; i >= 0; i--) {
            var e = enemies[i];
            var dx = playerX - e.x, dy = playerY - e.y;
            var mx = dx === 0 ? 0 : (dx > 0 ? 1 : -1);
            var my = dy === 0 ? 0 : (dy > 0 ? 1 : -1);
            if (rng() < 0.3) { mx = dx === 0 ? (rng() < 0.5 ? -1 : 1) : mx; }
            e.x += mx;
            e.y += my;
            e.x = Math.max(0, Math.min(GRID - 1, e.x));
            e.y = Math.max(0, Math.min(GRID - 1, e.y));

            if (e.x === playerX && e.y === playerY) {
                if (hasShield) {
                    hasShield = false;
                    removeAbility('bark_shield');
                    enemies.splice(i, 1);
                    flashLightning();
                } else {
                    harvestFailure();
                    return;
                }
            }
            changed = true;
        }
        if (changed) renderEnemies();
    }

    function onTapEnemy(evt) {
        evt.preventDefault();
        evt.stopPropagation();
        var idx = parseInt(evt.currentTarget.dataset.eidx);
        if (isNaN(idx) || !enemies[idx]) return;

        var radius = playerAbilities.indexOf('blast_radius') >= 0 ? 2 : 0;
        if (radius > 0) {
            var cx = enemies[idx].x, cy = enemies[idx].y;
            for (var i = enemies.length - 1; i >= 0; i--) {
                if (Math.abs(enemies[i].x - cx) <= radius && Math.abs(enemies[i].y - cy) <= radius) {
                    enemies.splice(i, 1);
                }
            }
        } else {
            enemies.splice(idx, 1);
        }
        renderEnemies();
    }

    function showFury() {
        var line = HARVEST_FURY[Math.floor(Math.random() * HARVEST_FURY.length)];
        furyEl.textContent = line;
        furyEl.style.opacity = '1';
        sapPlayLine(line);
        setTimeout(function () { furyEl.style.opacity = '0'; }, 2000);
    }

    function flashLightning() {
        lightning.style.opacity = '0.8';
        setTimeout(function () { lightning.style.opacity = '0'; }, 80);
        setTimeout(function () {
            lightning.style.opacity = '0.4';
            setTimeout(function () { lightning.style.opacity = '0'; }, 60);
        }, 150);
    }

    function stopHarvestIntervals() {
        clearInterval(harvestTimer);
        clearInterval(enemyInterval);
        clearInterval(spawnInterval);
        clearInterval(furyInterval);
        clearInterval(lightningInterval);
        harvestTimer = null;
    }

    function harvestSuccess() {
        stopHarvestIntervals();
        enemies = [];
        gridWrap.classList.remove('storm');
        harvestBar.style.display = 'none';
        harvestFill.style.width = '0%';
        furyEl.style.opacity = '0';

        if (harvestTarget) harvestedSet[harvestTarget.x + ',' + harvestTarget.y] = true;
        harvestTarget = null;

        flashLightning();

        fetch('/sap/' + C.gameId + '/harvest', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                treesCount = d.trees;
                rating = d.total_rating;
                gold = d.total_gold || gold;
                difficulty = d.difficulty;
                updateHud();
                showPostHarvest(d);
            });
    }

    function harvestFailure() {
        stopHarvestIntervals();
        enemies = [];
        gridWrap.classList.remove('storm');
        harvestBar.style.display = 'none';
        harvestFill.style.width = '0%';
        furyEl.style.opacity = '0';
        harvestTarget = null;
        state = 'gameover';

        var line = HARVEST_DEFEATED[Math.floor(Math.random() * HARVEST_DEFEATED.length)];
        sapPlayLine(line);

        fetch('/sap/' + C.gameId + '/gameover', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                rating = d.total_rating;
                updateHud();
                resultTitle.textContent = '💀 Defeated';
                resultText.textContent = '"' + line + '"\n\nTrees harvested: ' + d.trees + '\nRating earned: +' + d.rating_earned + '\nGold earned: ' + d.gold_earned;
                resultBtns.innerHTML = '';
                var btn = document.createElement('button');
                btn.className = 'sap-result-btn cashout';
                btn.textContent = 'Return to Federation';
                btn.addEventListener('click', function () { window.location.href = '/'; });
                resultBtns.appendChild(btn);
                resultBox.style.display = 'flex';
            });
    }

    function showPostHarvest(data) {
        var line = HARVEST_SURVIVED[Math.floor(Math.random() * HARVEST_SURVIVED.length)];
        sapPlayLine(line);
        state = 'result';
        resultTitle.textContent = '🍁 Sap Collected!';
        resultText.textContent = '"' + line + '"\n\n+5 rating points!\nTrees: ' + data.trees + ' | Rating earned: +' + data.rating_earned + (data.gold_earned ? '\nGold earned: ' + data.gold_earned : '');
        resultBtns.innerHTML = '';

        var cont = document.createElement('button');
        cont.className = 'sap-result-btn continue';
        cont.textContent = 'Keep Going';
        cont.addEventListener('click', function () {
            resultBox.style.display = 'none';
            state = 'explore';
            renderScreen();
        });
        resultBtns.appendChild(cont);

        var cash = document.createElement('button');
        cash.className = 'sap-result-btn cashout';
        cash.textContent = 'Cash Out';
        cash.addEventListener('click', function () {
            fetch('/sap/' + C.gameId + '/cashout', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    resultTitle.textContent = '🏠 Safe Return';
                    resultText.textContent = 'You made it back to the cabin.\n\nTrees: ' + d.trees + '\nRating earned: +' + d.rating_earned + (d.gold_earned ? '\nGold: ' + d.gold_earned : '');
                    resultBtns.innerHTML = '';
                    var btn2 = document.createElement('button');
                    btn2.className = 'sap-result-btn cashout';
                    btn2.textContent = 'Return to Federation';
                    btn2.addEventListener('click', function () { window.location.href = '/'; });
                    resultBtns.appendChild(btn2);
                });
        });
        resultBtns.appendChild(cash);

        resultBox.style.display = 'flex';
    }

    // ── NPC dialogue ────────────────────────────────────
    function showNpcDialogue(mx, my) {
        state = 'dialogue';
        talkedSet[mx + ',' + my] = true;
        var idx = Math.abs((mx * 31 + my * 17) % NPC_ENCOUNTERS.length);
        var enc = NPC_ENCOUNTERS[idx];

        dialogueText.textContent = enc[0];
        dialogueBtnA.textContent = enc[1];
        dialogueBtnB.textContent = enc[2];

        var onA = function () {
            dialogueBtnA.removeEventListener('click', onA);
            dialogueBtnB.removeEventListener('click', onB);
            dialogueText.textContent = enc[3];
            showDismissBtn();
        };
        var onB = function () {
            dialogueBtnA.removeEventListener('click', onA);
            dialogueBtnB.removeEventListener('click', onB);
            dialogueText.textContent = enc[4];
            showDismissBtn();
        };
        dialogueBtnA.addEventListener('click', onA);
        dialogueBtnB.addEventListener('click', onB);
        dialogueBtnA.style.display = '';
        dialogueBtnB.style.display = '';
        dialogueBox.style.display = 'block';
    }

    function showDismissBtn() {
        dialogueBtnA.textContent = 'Continue';
        dialogueBtnA.style.display = '';
        dialogueBtnB.style.display = 'none';
        var dismiss = function () {
            dialogueBtnA.removeEventListener('click', dismiss);
            dialogueBox.style.display = 'none';
            state = 'explore';
            checkNearbyTree();
        };
        dialogueBtnA.addEventListener('click', dismiss);
    }

    // ── merchant ────────────────────────────────────────
    function showMerchant() {
        state = 'merchant';
        merchantItems.innerHTML = '';
        var catalog = C.abilitiesCatalog;
        Object.keys(catalog).forEach(function (key) {
            var ab = catalog[key];
            var div = document.createElement('div');
            div.className = 'sap-merchant-item';
            div.innerHTML = '<span class="mi-icon">' + ab.icon + '</span>' +
                '<div class="mi-info"><div class="mi-name">' + ab.name + '</div><div>' + ab.desc + '</div></div>' +
                '<span class="mi-cost">' + ab.cost + ' 🪙</span>';
            div.addEventListener('click', function () { buyAbility(key, ab); });
            merchantItems.appendChild(div);
        });
        merchantBox.style.display = 'flex';
    }

    function buyAbility(key, ab) {
        if (gold < ab.cost) {
            alert('Not enough Roman gold! Need ' + ab.cost);
            return;
        }
        fetch('/sap/' + C.gameId + '/buy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ability: key }),
        }).then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.error) { alert(d.error); return; }
            gold = d.gold;
            playerAbilities = d.abilities;
            updateHud();
            renderAbilities();
        });
    }

    merchantClose.addEventListener('click', function () {
        merchantBox.style.display = 'none';
        state = 'explore';
        checkNearbyTree();
    });

    // ── abilities bar ───────────────────────────────────
    function renderAbilities() {
        abilitiesBar.innerHTML = '';
        var catalog = C.abilitiesCatalog;
        playerAbilities.forEach(function (key, idx) {
            var ab = catalog[key];
            if (!ab) return;
            var sp = document.createElement('span');
            sp.className = 'sap-ability';
            sp.textContent = ab.icon;
            sp.title = ab.name + ': ' + ab.desc;

            if (key === 'root_freeze') {
                sp.addEventListener('click', function () {
                    if (state !== 'harvest') return;
                    clearInterval(enemyInterval);
                    removeAbility('root_freeze');
                    setTimeout(function () {
                        var speed = Math.max(400, 1200 - difficulty * 80);
                        enemyInterval = setInterval(moveEnemies, speed);
                    }, 4000);
                });
            }
            abilitiesBar.appendChild(sp);
        });
    }

    function removeAbility(key) {
        var idx = playerAbilities.indexOf(key);
        if (idx >= 0) playerAbilities.splice(idx, 1);
        renderAbilities();
    }

    // ── input handling ──────────────────────────────────
    grid.addEventListener('click', function (evt) {
        if (state !== 'explore') return;
        var cell = evt.target.closest('.sap-cell');
        if (!cell) return;
        var r = parseInt(cell.dataset.r), c = parseInt(cell.dataset.c);
        if (isNaN(r) || isNaN(c)) return;

        // allow stepping off screen edges
        if (r === 0 && playerY === 0 && screenY > 0) { movePlayer(-1, playerX); return; }
        if (r === GRID - 1 && playerY === GRID - 1 && screenY < SCREENS - 1) { movePlayer(GRID, playerX); return; }
        if (c === 0 && playerX === 0 && screenX > 0) { movePlayer(playerY, -1); return; }
        if (c === GRID - 1 && playerX === GRID - 1 && screenX < SCREENS - 1) { movePlayer(playerY, GRID); return; }

        if (!isQueenMove(r, c)) return;
        if (!canMoveTo(r, c)) return;
        movePlayer(r, c);
    });

    // ── start game ──────────────────────────────────────
    startBtn.addEventListener('click', function () {
        if (C.status === 'active' && C.trees > 0) {
            startOverlay.style.display = 'none';
            state = 'explore';
            treesCount = C.trees;
            updateHud();
            renderScreen();
            renderAbilities();
            return;
        }
        startOverlay.style.display = 'none';
        state = 'explore';
        treesCount = 0;
        updateHud();
        renderScreen();
        renderAbilities();
    });

    // ── init ────────────────────────────────────────────
    sapLoadManifest();
    generateMap();
    if (C.status !== 'active') {
        startOverlay.querySelector('h2').textContent = '🍁 Run Complete';
        startOverlay.querySelector('p').textContent = 'This run is over. Start a new one from the main page.';
        startBtn.textContent = 'Back to Federation';
        startBtn.addEventListener('click', function () { window.location.href = '/'; });
    }
    renderAbilities();
})();
