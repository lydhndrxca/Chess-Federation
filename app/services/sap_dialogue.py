"""Dialogue pools for Spectacle Lake — Enoch's Maple Forest mode."""

# ── Friendly NPC encounters (white pawns in the forest) ──────────────
# Each: (greeting, option_a, option_b, reply_a, reply_b)
NPC_ENCOUNTERS = [
    (
        "Oh! A visitor! I've been counting pinecones all morning. I'm up to eleven.",
        "That sounds peaceful.",
        "Why pinecones?",
        "It IS peaceful. The squirrels don't judge. Not like HIM down there.",
        "He told me to. Said every pinecone is a soul. I don't ask questions anymore.",
    ),
    (
        "Shh! I'm listening to the sap move inside the tree. You can hear it if you press your ear real close.",
        "I'll try that.",
        "That's weird.",
        "It sounds like a tiny river! A river that goes UP. Isn't that wonderful?",
        "Maybe. But the trees don't think so. They told me you'd say that.",
    ),
    (
        "Hello friend! Would you like a leaf? I collected the best ones today.",
        "Sure, I'll take one.",
        "No thanks.",
        "Here! This one looks like a hand waving. I named it Gerald.",
        "Oh. That's okay. Gerald doesn't mind. Gerald doesn't mind anything.",
    ),
    (
        "I built a tiny house out of bark! It has a door and everything. Want to see?",
        "Show me!",
        "Maybe later.",
        "Look! The door even opens! I put a beetle inside. He's the mayor.",
        "The mayor will be disappointed. He prepared a speech.",
    ),
    (
        "Do you ever wonder what clouds taste like? I think they taste like cold bread.",
        "Cold bread?",
        "I don't think about clouds.",
        "Yes! The kind that's been in the cellar too long. But in a nice way.",
        "Oh. I think about them all the time. Every single one has a name.",
    ),
    (
        "I found a feather yesterday! A real one! From a real bird! Probably!",
        "That's great!",
        "Are you sure it's real?",
        "I know! I'm going to use it to write important things. Like 'hello' and 'tree'.",
        "Well... it FEELS real. And isn't that what matters? That's what the moth said.",
    ),
    (
        "The mushrooms here glow at night. Not bright, just... enough to read by.",
        "What do you read?",
        "That sounds eerie.",
        "The same note, over and over. It says 'YOU ARE SAFE HERE.' I believe it.",
        "Not eerie. Cozy. Everything down — I mean, out HERE — is cozy.",
    ),
    (
        "I used to live somewhere darker. But I can't remember where. Isn't that nice?",
        "I'm glad you're happier now.",
        "Doesn't that worry you?",
        "Me too! The sunlight here is warm. It doesn't flicker like candles.",
        "Worry? No. Worrying is for places with stone walls. This is a FOREST.",
    ),
    (
        "Would you like to hear a song? I only know one note, but I sing it very well.",
        "Let's hear it.",
        "One note isn't a song.",
        "Laaaaaaaaaa! ... Thank you for listening. You're my favorite audience.",
        "It is if you mean it hard enough. That's what the owl told me before it left.",
    ),
    (
        "I planted a seed here last week. Nothing's grown yet, but I check every day.",
        "I hope it grows.",
        "It might be dead.",
        "It WILL grow! I can feel it thinking about it down there in the dirt.",
        "No! Seeds are just... patient. Very, very patient. Like me.",
    ),
    (
        "There's a stream nearby that runs backwards sometimes. Only when no one's watching.",
        "How would you know if no one's watching?",
        "Streams don't run backwards.",
        "I... hm. You're cleverer than the last visitor. The deer didn't ask that.",
        "THIS one does. It told me so. In bubbles.",
    ),
    (
        "I keep a collection of nice stones. This one is my favorite. It's warm.",
        "Can I hold it?",
        "It's just a rock.",
        "Careful! It... it means a lot to me. It was a gift. From someone below.",
        "To you, maybe. To me, it remembers where it's been. All rocks do.",
    ),
    (
        "The trees whisper to each other at dusk. I've been learning their language.",
        "What do they say?",
        "Trees can't talk.",
        "Mostly 'stay' and 'grow' and 'he's coming.' I try not to think about the last one.",
        "Not with mouths. With roots. Everything important happens underground.",
    ),
    (
        "I made a crown out of twigs! Look! Am I a king now?",
        "You are the king of this clearing!",
        "Crowns are for people with kingdoms.",
        "Ha! I decree that all acorns shall be free! This is the best day!",
        "My kingdom is this patch of moss. That's enough. Some kingdoms are too big.",
    ),
    (
        "Something left footprints near my favorite stump. Big ones. I put flowers in them.",
        "What kind of footprints?",
        "That was brave.",
        "The kind without toes. Like something was dragged. But the flowers make it better.",
        "Brave? Or... I just don't want to think about what made them. The flowers help.",
    ),
    (
        "I've been here so long I forgot what rain feels like. Does it still happen?",
        "It rains all the time.",
        "I'm not sure anymore.",
        "How wonderful! I only get the dew. The dew is gentle. Rain sounds exciting.",
        "Exactly. Some things just... stop. And that's okay. The sun is reliable.",
    ),
    (
        "Want to play a game? I hide behind the tree, and you pretend you can't see me.",
        "Okay, I'll play!",
        "I can still see you.",
        "*giggling from behind tree* You're very good at pretending! Best game ever!",
        "That's... that's the whole point. Pretending is the best part of everything.",
    ),
    (
        "The fireflies spelled out a word last night. I think it was 'STAY.'",
        "That's beautiful.",
        "That's creepy.",
        "I thought so too. I'm going to stay. I was always going to stay.",
        "Creepy things can be beautiful. That's what HE always says. From below.",
    ),
    (
        "I drew a map of the forest on a leaf! But the wind took it. So now the wind has a map.",
        "The wind doesn't need a map.",
        "That's actually poetic.",
        "Then it has one for free! Lucky wind!",
        "Thank you! I also wrote a poem once. It was one word: 'moss.' I think it captured everything.",
    ),
    (
        "I found a key buried in the roots. It doesn't fit anything up here. I keep it anyway.",
        "Maybe it fits something below.",
        "Throw it away.",
        "Below... yes. I think it does. I dream about a door sometimes. A heavy one.",
        "No. I'll keep it. Some things are worth holding even when they open nothing.",
    ),
]

# ── Enoch harvest-mode lines (short, furious, shouted) ───────────────
HARVEST_FURY = [
    "NO!",
    "MINE!",
    "That sap is MINE!",
    "GET AWAY FROM MY TREE!",
    "STOP TOUCHING IT!",
    "I PLANTED THAT!",
    "THIEF!",
    "Little RAT!",
    "HANDS OFF!",
    "You DARE?!",
    "I'LL DROWN YOU IN MAPLE!",
    "The forest HATES you!",
    "Every drop is MINE!",
    "I can SMELL your greed!",
    "You'll PAY for that!",
    "The roots remember!",
    "GET OUT!",
    "VERMIN!",
    "My PRECIOUS sap!",
    "I waited YEARS for this!",
    "The trees SCREAM!",
    "Leave! LEAVE!",
    "I'll BURY you here!",
    "WRETCHED tapper!",
    "Not ONE drop!",
    "The bark weeps!",
    "BACK! BACK!",
    "From the BASEMENT I send them!",
    "My minions! SWARM!",
    "Choke on amber!",
    "This forest is my KINGDOM!",
    "I found this place FIRST!",
    "Every bucket you fill — I FEEL IT!",
    "The pipes beneath carry MY sap!",
    "Crawl back to your cabin!",
    "The spiders are on MY side!",
    "Drown in maple! DROWN!",
    "You think you can take from ME?!",
    "I've been collecting since BEFORE you!",
    "Each tap is a WOUND!",
]

# ── Enoch post-harvest (failed to stop player) ──────────────────────
HARVEST_SURVIVED = [
    "No... no no no no no...",
    "You... got one. Fine. FINE. It won't happen again.",
    "Enjoy that bucket. It's the last one you'll ever fill.",
    "The forest will remember this theft.",
    "One tree. ONE. The next won't be so easy.",
    "I'm going to find BIGGER pieces next time.",
    "That sap was forty years old. FORTY.",
    "You'll choke on it. Eventually. They all do.",
    "I can hear the tree crying. You monster.",
    "Fine. Take it. But the forest is watching now.",
]

# ── Enoch when player is defeated during harvest ────────────────────
HARVEST_DEFEATED = [
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
]

# ── Peaceful exploration lines (rare, ambient) ──────────────────────
EXPLORATION_AMBIENT = [
    "The forest is quiet today. Too quiet for my liking.",
    "I can see you from the grate. Moving through MY trees.",
    "Keep walking. The good sap is further in. Much further.",
    "The creatures here... I made them from memory. They're happy.",
    "This place is what the school looked like. Before.",
    "Don't mind the fog. It's just... the forest breathing.",
]

# ── Merchant lines ───────────────────────────────────────────────────
MERCHANT_GREETING = [
    "Psst! Over here. I've got things. Good things. Forest things.",
    "Ah, a tapper! You look like you could use an edge. For a price.",
    "The old man downstairs doesn't know I'm here. Let's keep it that way.",
    "Roman gold, friend. That's the only currency that matters in these woods.",
    "You've got that look. The 'I need to survive the next harvest' look.",
]

# ── Ability descriptions ─────────────────────────────────────────────
ABILITIES = {
    'bark_shield': {
        'name': 'Bark Shield',
        'desc': 'Survive one hit during harvest. Consumed on use.',
        'cost': 15,
        'icon': '🛡️',
    },
    'quick_tap': {
        'name': 'Quick Tap',
        'desc': 'Harvest timer reduced by 8 seconds.',
        'cost': 20,
        'icon': '⚡',
    },
    'root_freeze': {
        'name': 'Ancient Roots',
        'desc': 'Freeze all enemies for 4 seconds during harvest.',
        'cost': 25,
        'icon': '🌿',
    },
    'blast_radius': {
        'name': 'Forest Spirit',
        'desc': 'Tap kills enemies in a 2-tile radius.',
        'cost': 30,
        'icon': '💫',
    },
    'slow_sap': {
        'name': 'Maple Blessing',
        'desc': 'Enemies move 40% slower for this harvest.',
        'cost': 10,
        'icon': '🍁',
    },
    'lantern': {
        'name': "Enoch's Lantern",
        'desc': 'Reveals 2 extra tiles of fog in all directions.',
        'cost': 8,
        'icon': '🔦',
    },
}

ENTRY_COST = 5
POINTS_PER_TREE = 5
MAX_RATING_POINTS = 50
SAP_PER_BUCKET = 3.5  # liters — realistic for a single maple tap session
