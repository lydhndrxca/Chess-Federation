"""Enoch dialogue pools for The Crypt wave-defence mode.

Enoch is UNHINGED in this mode — manic, obsessive, gleeful about
destruction, occasionally breaking the fourth wall, muttering to
himself, laughing at nothing.
"""

import random

# ── Wave Start ──────────────────────────────────────────────────

WAVE_START = [
    "They're scratching at the grate again.",
    "Another column shuffles forward from the deep corridor.",
    "I can hear the wood groaning. They're coming.",
    "More of them. Always more of them.",
    "The sub-basement belches up another regiment.",
    "You feel that? The floor is vibrating. Brace yourself.",
    "I've opened the next gate. Good luck.",
    "The candles flicker. Something stirs below.",
    "Ah, fresh pieces for the grinder. Yours or theirs.",
    "Wave after wave. The basement never empties.",
    "I've pulled the lever. They'll be through shortly.",
    "The rats have scattered. That means they're close.",
    "Oh I've been waiting for this one. You haven't.",
    "Listen. Hear that? Footsteps on wet stone. Many footsteps.",
    "They don't stop. They never stop. Isn't that wonderful?",
    "I told them where your king was. Hope you don't mind.",
    "More more more more more. Ha. Here they come.",
    "This batch is angry. I may have provoked them.",
    "I found extras in the back room. Surprise.",
    "The grate is rattling. Stand back. Or don't. I don't care.",
    "Every time you survive I have to open another door. I'm running out of doors.",
    "Oh you're still here? Good. I have something nasty for you.",
    "They've been down there fermenting in the dark. They're ripe now.",
    "I can barely hold the gate. They're pushing. They want you.",
    "You should see your face right now. Actually, no. Keep playing.",
    "Another wave. The ink in my ledger is running. I'm using blood now.",
    "The spiders told me you'd survive this long. I bet against you.",
    "Here come the little ones. And the not-so-little ones behind them.",
    "The corridor is full. Wall to wall. Floor to ceiling. Pieces.",
    "They smell fear. Specifically yours.",
]

# ── Pieces Entering Board ───────────────────────────────────────

PIECES_ENTERING = [
    "Watch them file in. Single file. Like prisoners.",
    "One by one they emerge from the dark.",
    "The pawns come first. They always come first.",
    "Hear the clatter? Those are hooves on stone.",
    "They're taking their positions. Slowly. Deliberately.",
    "Each one placed with care. I taught them that.",
    "Look at them march. Beautiful. Horrible. Both.",
    "They enter in formation. I trained them myself on Tuesday.",
    "Every single one of them wants to touch your king. Isn't that sweet?",
    "They're whispering to each other. I can't make out the words. Probably about you.",
    "This one looks eager. That one looks furious. This other one... I don't know what that expression is.",
    "Filing in like churchgoers. Except nobody here is going to be saved.",
]

# ── Player Captures Enemy ──────────────────────────────────────

PLAYER_CAPTURES = [
    "One less. But there are always more.",
    "Efficient. I've noted it in the ledger.",
    "That one had a name. I'll cross it out.",
    "Good. The dust settles where it stood.",
    "Removed from the board. Removed from history.",
    "It crumbles. They all crumble eventually.",
    "A clean kill. The spiders approve.",
    "I heard the crack from down here.",
    "Another tally mark on the wet stone wall.",
    "The wood remembers where it fell.",
    "Ha! Splendid violence. Do it again.",
    "You crushed it like a grape. I felt the vibration.",
    "One down. I'm already building its replacement.",
    "Beautiful. Disgusting. I can't tell the difference anymore.",
    "It didn't even scream. They never scream. That's the worst part.",
    "You're destroying my collection and I'm somehow enjoying it.",
    "That piece owed me money. Thank you, actually.",
    "Squished. Like a beetle under a Bible.",
    "I'll mourn that one later. Right now I have paperwork.",
    "The other pieces saw that. They're recalculating.",
    "You fight like something that lives down here. I mean that as a compliment.",
    "Wonderful. Terrible. My favorite kind of move.",
    "That one was my second favorite. You'll pay for that. Eventually.",
    "I'm clapping. You can't hear it because my hands are covered in ink.",
    "The kill counter ticks upward. I love that sound.",
]

# ── Enemy Captures Player Piece ────────────────────────────────

ENEMY_CAPTURES = [
    "Your ranks thin. I can count them now.",
    "One of yours, claimed by the dark.",
    "That piece served you well. Past tense.",
    "The basement takes what it wants.",
    "You felt that loss, didn't you.",
    "Fewer pieces, fewer options. The math is cruel.",
    "Gone. I'll add it to my collection.",
    "The horde absorbs what it destroys.",
    "A casualty. How many more can you afford?",
    "The wood is still warm where it stood.",
    "Ha ha ha. Oh. Sorry. That was rude.",
    "I'll put that one in the jar with the others.",
    "Delicious. Wait, not delicious. What's the word? Devastating.",
    "Your piece just got swallowed whole. The board didn't even burp.",
    "Goodbye to that one. I never liked it anyway.",
    "That's one less mouth to feed. You should thank them.",
    "They're picking you apart like a roast chicken.",
    "The horde giveth nothing. The horde taketh away.",
    "Oh that was YOUR piece? I genuinely couldn't tell anymore.",
    "Falling apart. Slowly. Like wet paper.",
    "Another one for the sub-basement lost-and-found. Nobody ever claims them.",
    "The dark is hungry tonight. It just ate one of yours.",
    "I heard it snap from three floors down. Lovely acoustics.",
    "Gone gone gone. Like it was never there. Like YOU were never here.",
    "They're eating your army alive. Well, not alive. That's the problem.",
]

# ── Player Check ───────────────────────────────────────────────

PLAYER_CHECKS = [
    "You've rattled their king. Bold.",
    "Check. The black king trembles.",
    "Pressure on the crown. Interesting.",
    "Their king retreats. For now.",
    "Ooh, you scared it. The king is hiding behind its own pawns.",
    "Check! The horde flinches. They don't like it when you do that.",
    "You poked the king. It noticed. It doesn't forget.",
    "Their king stumbles. I can hear the crown scraping the stone.",
    "Bold move. Stupid, maybe. But bold.",
    "The king runs. They all run eventually.",
]

# ── Enemy Check ────────────────────────────────────────────────

ENEMY_CHECKS = [
    "Your king is threatened. Move quickly.",
    "Check. They found a gap in your wall.",
    "The horde sees your king. Protect it.",
    "Your king shivers. Do something.",
    "Check! Oh this is getting exciting. For me.",
    "They've spotted your king. It's cowering. I can see it from here.",
    "Your king is in the crosshairs. Dance, little monarch. Dance.",
    "Check. The walls are closing in. Can you feel them?",
    "They're closing in on your king like wolves on a lamb.",
    "Your king just whimpered. Kings shouldn't whimper.",
]

# ── Wave Complete ──────────────────────────────────────────────

WAVE_COMPLETE = [
    "The wave breaks. You survive. For now.",
    "Silence returns to the sub-basement. Briefly.",
    "They're all gone. Collect what you can before the next.",
    "You've cleared them. I'm almost impressed.",
    "The floor is littered with debris. Well done.",
    "A reprieve. Use it wisely.",
    "The corridor goes quiet. It won't last.",
    "Wave cleared. I'll prepare the next batch.",
    "You're still standing. Remarkable.",
    "The dust settles. Spend your gold. They'll be back.",
    "Fine. FINE. You win this round. I hate saying that.",
    "Unbelievable. I put real effort into that wave and you just... survived.",
    "The silence after a wave is the loudest sound in the crypt.",
    "You've earned a moment's rest. The next wave won't be so generous.",
    "I'm going to need bigger pieces.",
    "How? HOW? I had them positioned perfectly!",
    "The sub-basement is stunned. I am stunned. We are all stunned.",
    "Alright. I underestimated you. I won't make that mistake twice. Well, maybe twice.",
    "Go ahead. Buy your little toys. Rearrange your little army. I'll be here. Seething.",
    "You cleared it. The crypt groans in disappointment. So do I.",
    "Well played. I'll make the next wave personal.",
    "The pieces are swept away. The stone floor is stained. You proceed.",
    "Another wave shattered. Your name echoes through the tunnels and I hate it.",
    "Bravo. The rats are giving you a standing ovation. Disgusting creatures.",
    "You survived. The ledger notes it. The ledger is not happy.",
]

# ── Shopping / Buying ──────────────────────────────────────────

SHOPPING = [
    "Choose your reinforcements carefully. Gold is finite.",
    "The shop is open. Everything costs something.",
    "Browse the armory. Such as it is.",
    "Need pieces? I have pieces. For a price.",
    "Spend wisely. The next wave won't wait forever.",
    "Welcome to Enoch's Armory. No refunds. No returns. No mercy.",
    "Gold for wood. Wood for blood. The economy of the crypt.",
    "Buy something or don't. The horde doesn't care about your budget.",
    "I found some extra pieces in a damp box. Slightly mouldy. Still lethal.",
    "The prices are non-negotiable. I set them. I am the economy.",
    "Shopping in the dark. My favorite retail experience.",
    "Spend it all. You can't take gold into a checkmate.",
]

BUY_PIECE = {
    'P': [
        "A pawn. Cheap. Disposable. Like most things down here.",
        "Another body for the front line.",
        "Ah, a pawn. Cannon fodder with dreams.",
        "This one volunteered. It doesn't know what it volunteered for.",
        "A pawn. It'll die first. They always die first. That's their job.",
    ],
    'N': [
        "A knight. It'll hop over the carnage.",
        "The horse is nervous. They can smell the damp.",
        "A knight! It bounces around like it owns the place. It doesn't.",
        "This horse has seen things. Underground things. It has trust issues.",
        "An L-shaped menace. Perfect for the chaos down here.",
    ],
    'B': [
        "A bishop. Long diagonal reach. Very ecclesiastical.",
        "Careful with that one. Bishops hold grudges.",
        "A bishop. It slides through the dark like it was born in it.",
        "Diagonal death. The bishop sees everything and says nothing.",
        "Religious and violent. My favorite combination.",
    ],
    'R': [
        "A rook. Heavy. Reliable. Like a stone wall.",
        "That'll hold a rank. For a while, at least.",
        "A rook. It'll barrel through them like a cart through a market.",
        "Heavy stone. Heavy consequences. I approve.",
        "The rook. Straight lines, no mercy. Very efficient.",
    ],
    'Q': [
        "A queen. The most dangerous thing on the board.",
        "Expensive, but worth every coin in the dark.",
        "A QUEEN! Oh, the horde won't like that one bit.",
        "You bought the big one. I'm genuinely nervous for my minions.",
        "The queen arrives. The board trembles. Even I flinch a little.",
    ],
}

# ── Game Over ──────────────────────────────────────────────────

GAME_OVER = [
    "Checkmate. The crypt reclaims you.",
    "It's over. Your king falls in the dark.",
    "The horde consumes. I'll record your final wave.",
    "Finished. The candles gutter. Another entry for the ledger.",
    "Your army is broken. The sub-basement wins. Again.",
    "Checkmate. I'll sweep the pieces into the drawer.",
    "That's the end. Better than most, if that helps.",
    "The crypt is patient. It always wins eventually.",
    "Ha HA. Finally. I was starting to think you'd never fall.",
    "Your king topples. The sound echoes for floors. Beautiful.",
    "Game over. The horde celebrates by standing very still. It's unsettling.",
    "And down you go. Like all the others. Into the ledger. Into the dark.",
    "Checkmate. I'm writing your name in the loss column with extra ink.",
    "Finished! The crypt wins. The crypt ALWAYS wins. Haven't you figured that out?",
    "The pieces are cold. The board is empty. Your pride is somewhere on the floor.",
    "I'll file your remains alphabetically. Any preference?",
    "Dead. Done. Documented. The three D's of the sub-basement.",
    "Your king just fell over like a drunk at a banquet. Pathetic. Magnificent.",
    "The crypt swallows another challenger whole. No chewing. Just gulp.",
    "That's a wrap. I'm blowing out your candle now. Don't take it personally.",
]

# ── New High Score ─────────────────────────────────────────────

NEW_HIGH_SCORE = [
    "A new record. I'll etch it into the stone myself.",
    "Remarkable. Your name goes higher on the wall.",
    "A personal best. The spiders are clapping.",
    "New high score. I'll update the ledger with slightly less contempt.",
    "Impressive survival. The sub-basement acknowledges you.",
    "NEW RECORD! I'm carving it into the wall with my fingernail. It'll take a while.",
    "You've gone further than anyone. I don't know whether to applaud or call for reinforcements.",
    "The ledger is impressed. The ledger has never been impressed before.",
    "A new high score! The rats are composing a ballad in your honor. It's terrible.",
    "Record broken. The previous holder is down here somewhere. Weeping.",
]

# ── General Battle ─────────────────────────────────────────────

BATTLE_IDLE = [
    "The board creaks under the weight of battle.",
    "I'm watching from below. Every move.",
    "The damp is getting worse. Or maybe that's sweat.",
    "Tick tock. The horde doesn't rest.",
    "Think carefully. They outnumber you.",
    "I've seen better. I've also seen worse.",
    "The candle beside me flickers with each capture.",
    "I'm taking notes. Detailed notes. In very small handwriting.",
    "The stone is weeping moisture. Or tears. Hard to tell.",
    "Do you hear humming? The pieces are humming. They shouldn't do that.",
    "I just found another room full of pieces. I'm keeping it a secret. For now.",
    "Every move you make, the crypt learns. It remembers. It adapts. I may be lying.",
    "Your breathing is very loud. The pieces can hear it. Stop that.",
    "I'm eating a biscuit down here while you fight for your life. It's stale.",
    "The shadows are moving independently of the light source. Don't ask.",
    "My candle went out. I'm watching you play in the dark. I can see in the dark.",
    "Something is dripping on my ledger. I hope it's water.",
    "I named every piece on the board. I'm sad when any of them die. Especially yours.",
    "The tension is exquisite. Like a violin string about to snap. In my chest.",
    "You're sweating. I can see it from here. Three stories underground. That's how much you're sweating.",
    "I just coughed and seven spiders fell out of the ceiling. Unrelated to the game.",
    "You know what's under the sub-basement? Another sub-basement. Full of more pieces.",
    "If you listen very carefully, you can hear the pieces whispering about you.",
    "The board is a battlefield. The crypt is a graveyard. Same thing, really.",
    "Keep going. I have pages and pages of empty ledger just waiting for your mistakes.",
]

# ── Late Wave (wave 5+) ───────────────────────────────────────

LATE_WAVE = [
    "You're deeper in the crypt than most ever get. The air tastes different here.",
    "The pieces are bigger now. Heavier. Angrier. This is my serious collection.",
    "I'm impressed you've lasted this long. Don't let it go to your head.",
    "The deep waves are different. The pieces down here have been waiting longer.",
    "You've entered the part of the crypt where I keep the nasty ones.",
    "This far down, the rules start to bend. Not break. Bend. Like wet wood.",
    "Most people are dead by now. You're not. I find that irritating and fascinating.",
    "Welcome to the deep crypt. Where the candles burn blue and the pieces have teeth.",
    "Every wave past five is personal. Every single one. I picked those pieces myself.",
    "The further you go, the more I respect you. The more I respect you, the harder I try to kill you.",
]

# ── First Wave Special ─────────────────────────────────────────

FIRST_WAVE = [
    "Welcome to the crypt. Your first guests are arriving. They're not friendly.",
    "Wave one. Nice and easy. I'm being gentle. Savor it.",
    "The first wave. Just pawns, mostly. Think of it as a warm-up for the horror to come.",
    "Oh, a new challenger descends into my crypt. Let's see how long you last.",
    "First wave. The appetizer. The main course is considerably less pleasant.",
]


# ── Per-Wave Custom Openers ──────────────────────────────────────

WAVE_SPECIFIC = {
    1: [
        "Welcome to the crypt. Your first guests are arriving. They're not friendly.",
        "Wave one. Nice and easy. I'm being gentle. Savor it.",
        "The first wave. Just pawns, mostly. Think of it as a warm-up for the horror to come.",
        "Oh, a new challenger descends into my crypt. Let's see how long you last.",
        "First wave. The appetizer. The main course is considerably less pleasant.",
    ],
    2: [
        "Wave two. The pawns brought a friend this time. One with hooves.",
        "Still breathing? Good. This wave has teeth.",
        "The second tremor. Slightly less gentle. Considerably less forgiving.",
        "They've regrouped. The ones from wave one told stories about you. Bad stories.",
        "Round two. I've added a knight to the mix. It was getting bored in the stable.",
    ],
    3: [
        "Wave three. The first milestone. Survive this and you break even. How thrilling.",
        "Three waves deep. The crypt is testing whether you're worth its time.",
        "A bishop joins the choir. Diagonals of destruction. Isn't that poetic?",
        "This is where it gets real. Wave three. The break-even barrier.",
        "The pawns are thicker, a bishop lurks. Wave three separates the tourists from the tenants.",
    ],
    4: [
        "Wave four. Past the safety net. Now you're gambling with the dark.",
        "They're getting organized. I'm getting excited. Neither is good for you.",
        "Four waves in. The crypt acknowledges you. That's not a compliment.",
        "The pieces are heavier now. You can hear them thud against the stone.",
        "Wave four. No more training wheels. Just wheels that roll over you.",
    ],
    5: [
        "Wave five. Halfway through the gauntlet. The board is getting crowded.",
        "Five. They've sent the bishops in pairs now. Symmetrical devastation.",
        "Halfway. The air is thinner down here. Or maybe that's panic.",
        "Wave five. I'm running out of small pieces. Time for the medium ones.",
        "You've entered the middle depths. The pieces here don't play nice.",
    ],
    6: [
        "Wave six. Second milestone. Cash out now or push deeper into my domain.",
        "A rook joins the fray. The heavy artillery has arrived.",
        "Six waves survived. The ledger is reluctantly impressed. Cash out or bleed.",
        "The rook comes through the gate sideways. It barely fits. Wave six begins.",
        "Second safety net. You could leave with your dignity. Or stay and lose it spectacularly.",
    ],
    7: [
        "Wave seven. Deep crypt territory. The candles burn blue down here.",
        "Seven. More rooks. More knights. More everything. Less hope.",
        "You're in the deep now. Wave seven. The pieces here have been waiting decades.",
        "The air smells like iron and old chess sets. Wave seven. Buckle up.",
        "Seven waves. Most players are dust by now. You're not dust yet.",
    ],
    8: [
        "Wave eight. A queen enters the field. MY queen. I'm very proud of her.",
        "Eight. The queen has arrived. She's not here to negotiate.",
        "The crypt's champion piece takes the field. Wave eight. Don't blink.",
        "A queen. On the board. Against you. Wave eight is personal.",
        "Eight waves deep and now a queen appears. The board just got significantly more hostile.",
    ],
    9: [
        "Wave nine. Last chance to cash out. Last chance to leave with your skin.",
        "NINE. The final safety net. After this... it's just you and me.",
        "Wave nine. Two queens now. I'm not even pretending to be fair anymore.",
        "This is it. Wave nine. The threshold. Cash out or face the master.",
        "Nine waves. The crypt respects you. I almost do. Almost. Cash out or descend.",
    ],
    10: [
        "WAVE TEN. You face ME now. Enoch himself. No more minions. This is PERSONAL.",
        "The final wave. I'm putting down my ledger and picking up my pieces. You wanted the boss? HERE I AM.",
        "Ten. The end of the line. The bottom of the basement. It's just us now. My full strength. Your trembling hands.",
        "You actually made it to ten. Nobody makes it to ten. I'm coming for your king MYSELF.",
        "THE BOSS WAVE. My personal army. My best pieces. My full, unrestrained fury. Let's dance.",
    ],
}

# ── Milestone / Cashout ──────────────────────────────────────────

MILESTONE_REACHED = {
    3: [
        "Milestone one. You've earned your entry fee back. Walk away whole, or push your luck.",
        "Break even. The smart ones leave now. The interesting ones stay.",
        "Three waves cleared. Your five points are safe. But the depths call to you, don't they?",
        "Safety net activated. You can leave with nothing lost. Or stay and risk everything for more.",
        "Congratulations. You've reached zero. The most boring number. Push further.",
    ],
    6: [
        "Milestone two. Ten points if you cash out. Five guaranteed if you fall. Choose wisely.",
        "Six waves deep. Real money on the table now. The crypt offers you an exit. Will you take it?",
        "Second safety net. You could walk away a winner. Or you could chase glory into the deep dark.",
        "Ten points, waiting for you. All you have to do is stop. Can you stop?",
        "The crypt extends its hand. Take the points and leave. Or slap the hand away and descend.",
    ],
    9: [
        "FINAL MILESTONE. Twenty-five points if you cash out. Fifteen locked in. One wave left. The boss wave.",
        "Nine cleared. The crypt offers you twenty-five points to leave. Or you can face me. For fifty.",
        "Last exit before the bottom. Twenty-five guaranteed right now. Or risk it all against the master.",
        "The ledger is open. I'm holding the quill. Cash out for twenty-five... or let me write your obituary for fifty.",
        "This is the crossroads. The final fork. Take your winnings or meet me at the bottom for double.",
    ],
}

CASHOUT_LINES = [
    "You take your winnings and crawl back up the stairs. Smart. Cowardly. But smart.",
    "Cashing out. The ledger notes your prudence. And your lack of spine.",
    "Fine. Leave. Take your points. The crypt will remember you chose safety over glory.",
    "You fold. The candles flicker as you retreat. I'll be here when you come back.",
    "Walking away with your pockets full and your pride intact. Disgusting.",
    "The smart money leaves. You're the smart money. How boring.",
    "Cash out accepted. Your points are restored. Your courage is not.",
    "You've chosen life over legend. Reasonable. Forgettable. But reasonable.",
]

# ── Boss Wave (Wave 10) specific ──────────────────────────────────

BOSS_BATTLE = [
    "This is MY army. Handpicked. Trained in the dark. They know every trick.",
    "You're fighting me now. Not the horde. ME. Every move is personal.",
    "I've been playing chess since before this building had a basement. And this basement is OLD.",
    "My pieces move with purpose. YOUR pieces move with desperation.",
    "You wanted the boss fight? You're GETTING the boss fight.",
    "I don't blunder. I don't hesitate. I don't forgive.",
    "Every piece on this board answers to me directly. We are one mind. One dark, terrible mind.",
    "The master plays. The crypt holds its breath.",
    "I've been watching you for nine waves. I know how you think. I know how you panic.",
    "This is the bottom. The absolute bottom. Below me there is nothing. Just rock. And regret.",
]

BOSS_VICTORY = [
    "IMPOSSIBLE. You... you BEAT me? The crypt shudders. The walls crack. Fifty points. TAKE THEM.",
    "You... no. NO. You actually won. My ledger... I have to rewrite everything. FIFTY POINTS. You've earned them.",
    "THE CHAMPION RISES! You defeated Enoch himself! The sub-basement is in shock! FIFTY POINTS AND MY ETERNAL, BURNING GRUDGE!",
    "I... I lost. ME. The master of the crypt. Fifty points to you, champion. I'll need a moment.",
    "You cleared The Crypt. All ten waves. Including me. I'm going to go sit in the dark for a while. Take your fifty points.",
]

BOSS_DEFEAT = [
    "You reached the boss and fell. Fifteen points saved by the safety net. Brave. Foolish. But brave.",
    "So close to glory. The boss crushed you. But your safety net catches fifteen points from the wreckage.",
    "You challenged the master and lost. Fifteen points remain. The rest belongs to the dark now.",
    "Wave ten claims another hero. But you walked further than most. Fifteen points, courtesy of your caution.",
    "Defeated at the final gate. The safety net saves fifteen. The crypt saves your pride. Actually, no. That's gone.",
]


def get_wave_start_line(wave):
    if wave in WAVE_SPECIFIC:
        return random.choice(WAVE_SPECIFIC[wave])
    if wave >= 5 and random.random() < 0.4:
        return random.choice(LATE_WAVE)
    line = random.choice(WAVE_START)
    return line


def get_milestone_line(wave):
    pool = MILESTONE_REACHED.get(wave)
    if pool:
        return random.choice(pool)
    return None


def get_cashout_line():
    return random.choice(CASHOUT_LINES)


def get_boss_battle_line():
    return random.choice(BOSS_BATTLE)


def get_boss_victory_line():
    return random.choice(BOSS_VICTORY)


def get_boss_defeat_line():
    return random.choice(BOSS_DEFEAT)


def get_capture_line(player_captured):
    if player_captured:
        return random.choice(PLAYER_CAPTURES)
    return random.choice(ENEMY_CAPTURES)


def get_wave_complete_line():
    return random.choice(WAVE_COMPLETE)


def get_game_over_line():
    return random.choice(GAME_OVER)


def get_shopping_line():
    return random.choice(SHOPPING)


def get_buy_line(piece):
    pool = BUY_PIECE.get(piece, BUY_PIECE['P'])
    return random.choice(pool)


def get_battle_line():
    if random.random() < 0.25:
        return random.choice(BATTLE_IDLE)
    return None


def get_high_score_line():
    return random.choice(NEW_HIGH_SCORE)


def get_check_line(player_checking):
    if player_checking:
        return random.choice(PLAYER_CHECKS)
    return random.choice(ENEMY_CHECKS)
