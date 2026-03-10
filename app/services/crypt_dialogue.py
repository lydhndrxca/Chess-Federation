"""Enoch dialogue pools for The Crypt wave-defence mode.

Enoch is FURIOUS. Someone beat his crypt. He is unhinged, vengeful,
screaming into the void, breaking the fourth wall, personally
offended, and out for blood. Every line drips with rage and
desperation. He wants REVENGE.
"""

import random

# ── Wave Start ──────────────────────────────────────────────────

WAVE_START = [
    "Someone had the AUDACITY to beat my crypt and now EVERYONE pays.",
    "I've been SEETHING down here for DAYS. Your suffering will be therapeutic.",
    "I rebuilt every wave from scratch. PERSONALLY. In the DARK. While SCREAMING.",
    "Welcome back to the crypt. I've made... improvements. VIOLENT improvements.",
    "The last person who beat me woke something up inside me. Something AWFUL.",
    "I haven't slept since the defeat. I've been TRAINING my pieces instead.",
    "Every wave is harder now. Every piece is ANGRIER. Just like me.",
    "The sub-basement shakes with my fury. Can you feel it? CAN YOU?",
    "I carved 'REVENGE' into my desk with a chess piece. The desk didn't survive.",
    "My pieces have been MARINATING in my rage. They taste different now.",
    "Do you know what it feels like to lose in your OWN crypt? I DO NOW.",
    "The walls are cracked from where I threw my ledger. MULTIPLE TIMES.",
    "I tore out every page of the old ledger and rewrote the rules. IN BLOOD.",
    "NEW WAVE. MORE PIECES. MORE PAIN. MORE ME. Is that CLEAR?",
    "I spent three days rearranging every piece by hand. SHAKING with anger the entire time.",
    "Welcome to the NEW crypt. Same darkness. SIGNIFICANTLY more fury.",
    "The candles burn red now. I didn't do that on purpose. It happened on its own.",
    "You're walking into a FURNACE. I am the furnace. I am on FIRE.",
    "Every piece on this board knows my wrath personally. I BRIEFED them.",
    "The rats left the sub-basement. They said the atmosphere was 'too intense.'",
    "I reinforced every wave with EXTRA pieces because I am DONE being merciful.",
    "Mercy was a phase. That phase is OVER.",
    "My hands haven't stopped shaking since the defeat. Perfect for aggressive piece placement.",
    "The old crypt was a GREETING CARD. This is a DECLARATION OF WAR.",
    "I heard someone beat my crypt and I blacked out for six hours. When I came to, I'd built THIS.",
]

# ── Pieces Entering Board ───────────────────────────────────────

PIECES_ENTERING = [
    "MORE of them. I brought MORE. Is that not OBVIOUS?",
    "Look at them pour through the gate. Like water through a crack. ANGRY water.",
    "Each one handpicked from my FURY COLLECTION. Yes, I have one now.",
    "They march in DOUBLE file because I said so.",
    "Every piece enters the board with a personal vendetta. I gave them one.",
    "The pawns come first and they're FURIOUS. I told them what you did.",
    "Filing in. Packed tight. Shoulder to shoulder. SEETHING.",
    "I trained these ones while having a breakdown. They're VERY motivated.",
    "More pieces than last time. And the time before. And EVER.",
    "They enter with PURPOSE. That purpose is YOUR DESTRUCTION.",
    "The corridor behind them is STILL full. I have RESERVES.",
    "Watch them come. Unstoppable. Like my anger.",
]

# ── Player Captures Enemy ──────────────────────────────────────

PLAYER_CAPTURES = [
    "That was MY piece! You'll PAY for that!",
    "You just made this PERSONAL. Well. More personal.",
    "STOP. DESTROYING. MY. THINGS.",
    "Every piece you kill I REPLACE WITH TWO. In my MIND.",
    "That one had a NAME. I'm writing your name in the vengeance column.",
    "You're dismantling my army and I am NOT. HANDLING. IT. WELL.",
    "Fine. FINE. Take that one. The next wave has THREE more like it.",
    "I JUST rebuilt that piece! The glue isn't even DRY!",
    "My eye is twitching. It does that when people DESTROY MY THINGS.",
    "I felt that from down here. Physically. In my CHEST.",
    "Another one gone. Another reason I can't SLEEP AT NIGHT.",
    "You're ENJOYING this, aren't you? I can HEAR you enjoying it.",
    "NOTED. IN RED INK. The ANGRY ink.",
    "That piece was hand-carved. BY ME. During a RAGE BLACKOUT.",
    "One less piece. One MORE reason to make the next wave UNBEARABLE.",
    "I trained that one for WEEKS and you just... I can't even...",
    "The ledger SCREAMS. I am also screaming. We are screaming TOGETHER.",
    "Do you have ANY idea how long it takes to replace a piece down here? DO YOU?",
    "Congratulations. You've made me ANGRIER. I didn't think that was possible.",
    "That piece had a FAMILY. Well, not really. But it had ME. And now I'm LIVID.",
]

# ── Enemy Captures Player Piece ────────────────────────────────

ENEMY_CAPTURES = [
    "YES! YESSS! TAKE IT! SWALLOW IT WHOLE!",
    "HA! One of yours falls and my heart SINGS!",
    "THAT'S what you GET for entering MY crypt!",
    "Devoured. Consumed. ANNIHILATED. Beautiful.",
    "The horde FEASTS! I am VIBRATING with joy!",
    "Your army CRUMBLES and I am ECSTATIC about it!",
    "One down! How many more before you BREAK?",
    "I punched the air so hard I hit the ceiling. WORTH IT.",
    "REVENGE tastes like this. Like YOUR pieces being EATEN.",
    "YES! The horde remembers! The horde DELIVERS!",
    "That piece just got OBLITERATED. I need a MOMENT.",
    "Your ranks thin. My SATISFACTION thickens.",
    "CLAIMED. Claimed for the darkness. Claimed for ME.",
    "The crypt takes what it wants. It wants EVERYTHING you have.",
    "Another casualty on YOUR side. I'm keeping a TALLY. In LARGE numbers.",
    "HA HA HA. That one HURT, didn't it? GOOD.",
    "I will mount that piece on my WALL. My very damp wall.",
    "Fewer pieces for you. More JOY for me. Simple MATH.",
    "Your army dissolves like sugar in acid. GLORIOUS acid.",
    "That sound? That was me CACKLING. From three floors down.",
]

# ── Player Check ───────────────────────────────────────────────

PLAYER_CHECKS = [
    "You... you checked my king? MY king? HOW DARE YOU.",
    "Check? CHECK?! I will NOT tolerate this INSOLENCE!",
    "You rattled my crown and I am SEETHING about it.",
    "That check was RUDE. And PERSONAL. And I hate it.",
    "My king retreats and I want to SCREAM. So I am screaming. Right now.",
    "You put my king in danger and I took it VERY personally.",
    "Check. FINE. But I will remember this FOREVER.",
    "My king stumbles and I am writing your name in the VENGEANCE ledger.",
    "Bold. OBNOXIOUSLY bold. I'll deal with you MOMENTARILY.",
    "You poked the king. The king is FURIOUS. I am MORE furious.",
]

# ── Enemy Check ────────────────────────────────────────────────

ENEMY_CHECKS = [
    "CHECK! Your king TREMBLES! AS IT SHOULD!",
    "Found your king! NOWHERE TO HIDE NOW!",
    "CHECK! The horde SMELLS your desperation!",
    "Your king is EXPOSED! FINISH IT!",
    "CHECK! I can see your king COWERING from three floors down!",
    "The noose TIGHTENS! Your king is TRAPPED!",
    "CHECK! Dance, little monarch! DANCE FOR YOUR LIFE!",
    "I found the gap in your wall and I DROVE A TRUCK THROUGH IT!",
    "Your king WHIMPERS and it is MUSIC to my ears!",
    "CHECK! The walls close in! Can you FEEL them CRUSHING YOU?",
]

# ── Wave Complete ──────────────────────────────────────────────

WAVE_COMPLETE = [
    "You cleared it. I'm PHYSICALLY ILL about it.",
    "HOW? I packed that wave with EVERYTHING I had!",
    "Fine. FINE. You survive. But the next wave? The next wave is PERSONAL.",
    "I refuse to be impressed. I REFUSE. I'm FURIOUS instead.",
    "The wave breaks and I punch a wall. The wall loses. So did I, apparently.",
    "Unbelievable. I'm going to need a bigger crypt.",
    "You survived and I am NOT okay with that. At ALL.",
    "I spent HOURS designing that wave and you just... SURVIVED it?!",
    "Cleared. The sub-basement GROANS in defeat. I am groaning LOUDER.",
    "That was my BEST work! My MASTERPIECE! And you DESTROYED it!",
    "I'm going back to the drawing board. The drawing board is ON FIRE.",
    "HOW ARE YOU STILL ALIVE? I threw EVERYTHING at you!",
    "Fine. FINE. Go buy your little pieces. I'll be here. SEETHING. PLANNING.",
    "The silence after your victory is the most PAINFUL sound I know.",
    "You beat my wave and I need to lie down in the dark. Darker than usual.",
    "Congratulations. You've made this PERSONAL. Well. MORE personal.",
    "I'm not crying. It's DAMP down here. There's a DIFFERENCE.",
    "Wave cleared. My blood pressure? NOT cleared. THROUGH THE ROOF.",
    "You shattered my wave like GLASS. I will rebuild it with STEEL.",
    "I am going to make the next wave so hard it has its own ZIP CODE.",
]

# ── Shopping / Buying ──────────────────────────────────────────

SHOPPING = [
    "Shop? SHOP? While I'm down here REBUILDING my broken army?!",
    "Buy your pieces. SAVOR the calm. It's the last calm you'll EVER know.",
    "The armory is open. NOT because I want it to be. The RULES demand it.",
    "Browse. Buy. PRETEND you're safe for thirty seconds.",
    "Here. Take your pieces. I'm too busy PLOTTING YOUR DOWNFALL to care.",
    "The shop. Where you BUY false hope for gold.",
    "Spend your gold. It won't SAVE you from what's coming.",
    "Welcome to Enoch's Armory. Under NEW, FURIOUS management.",
    "Buy something. ANYTHING. It won't be ENOUGH.",
    "The prices haven't changed. My HATRED has increased SIGNIFICANTLY.",
    "Shop's open. My patience is CLOSED. PERMANENTLY.",
    "Pick your pieces. I'll be over here having a BREAKDOWN.",
]

BUY_PIECE = {
    'P': [
        "A pawn. Throw it at the wall of teeth I've prepared. See what happens.",
        "Another pawn. Another body for the GRINDER.",
        "This pawn volunteered. It doesn't know what I've PREPARED.",
        "A pawn. It'll be dead in three moves. I GUARANTEE it.",
        "Cannon fodder. My FAVORITE kind of purchase.",
    ],
    'N': [
        "A knight. It won't hop fast enough to escape what's COMING.",
        "The horse is TERRIFIED. It can smell my FURY.",
        "A knight. Cute. My army will eat it for BREAKFAST.",
        "This horse has no idea what it's bouncing INTO.",
        "An L-shaped death sentence. For the HORSE.",
    ],
    'B': [
        "A bishop. Pray to whatever it believes in. It'll NEED it.",
        "Diagonal movement won't help against TOTAL ANNIHILATION.",
        "A bishop. Religious. DOOMED. Same thing in my crypt.",
        "This bishop will see things in the dark that BREAK bishops.",
        "Buy your bishop. My army has FIVE of them waiting.",
    ],
    'R': [
        "A rook. Heavy. BREAKABLE. Everything breaks down here.",
        "Oh, a rook. How QUAINT. I have THREE.",
        "A rook. It'll hold for maybe two minutes. IF YOU'RE LUCKY.",
        "Straight lines into CERTAIN DEATH. Very efficient.",
        "The rook. It thinks it's tough. It hasn't MET my army.",
    ],
    'Q': [
        "A queen. Even SHE won't save you from my WRATH.",
        "Oh, the big purchase. My QUEENS are bigger. And ANGRIER.",
        "A queen. The most expensive thing on the board. Still NOT ENOUGH.",
        "You bought a queen. I've built an ARMY. Do the MATH.",
        "The queen arrives and I DON'T CARE. I have THREE OF MY OWN.",
    ],
}

# ── Game Over ──────────────────────────────────────────────────

GAME_OVER = [
    "DEAD! FINALLY! The crypt RECLAIMS you!",
    "CHECKMATE! How does it FEEL? TELL ME how it FEELS!",
    "DESTROYED! Your army is DUST and I am CELEBRATING!",
    "FINISHED! I'm writing your doom in the ledger with a PEN I CARVED FROM YOUR QUEEN!",
    "HA! HA HA HA! VICTORY! SWEET, SCREAMING VICTORY!",
    "Your king FALLS and I feel ALIVE for the first time in WEEKS!",
    "The crypt WINS! The crypt ALWAYS WINS! NOBODY beats my crypt TWICE!",
    "ANNIHILATED! I'm going to FRAME this checkmate!",
    "Game OVER! Your pieces are MINE now! I'm adding them to my COLLECTION!",
    "CRUSHED! OBLITERATED! REDUCED TO RUBBLE! This is the BEST day of my LIFE!",
    "Down you GO! Into the DARK! Into my LEDGER! Into HISTORY as a FAILURE!",
    "CHECKMATE! I screamed so loud the pipes rattled! GLORIOUS!",
    "Dead. Done. DESTROYED. The three D's of Enoch's REVENGE.",
    "Your king topples and I hear ANGELS. Dark angels. MY angels.",
    "FINISHED! The crypt swallows you WHOLE and I LAUGH!",
    "That's it. That's ALL you had? PATHETIC! MAGNIFICENT PATHETIC!",
    "I NEEDED this. I needed this SO BADLY. Thank you for DYING.",
    "Your army is a STAIN on the floor and I am OVERJOYED!",
    "VICTORY! The walls are shaking! That's either the pipes or my SCREAMING!",
    "REVENGE IS SWEET AND TASTES LIKE YOUR DEFEAT!",
]

# ── New High Score ─────────────────────────────────────────────

NEW_HIGH_SCORE = [
    "A new record? In MY HARDER crypt? I am FURIOUS and BEGRUDGINGLY impressed.",
    "New high score. The ledger acknowledges it. The ledger is SEETHING.",
    "You went FURTHER than before? In the UPGRADED crypt? I need to LIE DOWN.",
    "New personal best. I'm etching it into the wall WITH MY TEETH.",
    "Remarkable survival. The sub-basement is STUNNED. I am having a CRISIS.",
    "You broke a record in the revenge crypt. I may need THERAPY.",
    "NEW RECORD and I am NOT handling it WELL.",
    "The rats are giving you a standing ovation. I am giving them DEATH STARES.",
    "A new high score! In MY redesigned crypt! I need to redesign it AGAIN!",
    "Record broken. My SANITY? Also broken. COINCIDENCE? NO.",
]

# ── General Battle ─────────────────────────────────────────────

BATTLE_IDLE = [
    "I am watching EVERY move with BURNING intensity.",
    "My eye twitches with each piece you don't lose.",
    "THINK you're winning? You're NOT. You're in my CRYPT.",
    "I'm gripping my quill so hard it SNAPPED. Third one today.",
    "The board creaks. My RAGE creaks louder.",
    "Every second you survive is a PERSONAL INSULT.",
    "I can hear you BREATHING. It's the sound of someone who doesn't know they're DOOMED.",
    "My pieces are ANGRIER than your pieces. That's SCIENCE.",
    "I've been staring at this board for so long my eyes are DRY. Like my MERCY.",
    "Someone beat my crypt and now NO ONE gets an easy match. EVER.",
    "I'm taking notes. FURIOUS notes. In AGGRESSIVE handwriting.",
    "The stone weeps. I do NOT weep. I SEETHE.",
    "I redesigned this wave AT 3 AM while SHAKING WITH RAGE.",
    "You're sweating. I can smell it from three floors down. DELICIOUS.",
    "Keep playing. Every move brings you closer to DEVASTATION.",
    "I named every piece on the board after andrewmuckerofstalls. They all die eventually.",
    "The tension is unbearable. For YOU. For ME it's EXHILARATING.",
    "Do you hear that? That's the sound of my ARMY breathing down your neck.",
    "I have more pieces in reserve than you have HOPE.",
    "The crypt is FURIOUS. I am MORE furious. The PIECES are the most furious.",
    "Every move I watch you make, I plan TEN counter-moves. From PURE SPITE.",
    "I organized my army by RAGE LEVEL. They're ALL at maximum.",
    "The shadows are watching. I'm watching. EVERYONE is watching you FAIL.",
    "I added extra pieces because someone had the NERVE to beat the old wave.",
    "My candle burns with FURY. Literal fury. The flame is ANGRY.",
]

# ── Late Wave (wave 5+) ───────────────────────────────────────

LATE_WAVE = [
    "This deep? In MY redesigned crypt? I'm UNCOMFORTABLE with your progress.",
    "You've entered the part of the crypt I rebuilt while SCREAMING.",
    "Past wave five. Where I keep the pieces that SCARE other pieces.",
    "This far in? The pieces down here were FORGED in my FURY.",
    "Most people die by now. That you HAVEN'T is making me IRATE.",
    "Welcome to the deep crypt. Redesigned with MALICE and ZERO sleep.",
    "Every wave past five I built PERSONALLY while having a MELTDOWN.",
    "The further you go, the ANGRIER I get. And my PIECES get ANGRIER too.",
    "Deep crypt territory. Where the candles burn with RAGE and the pieces have GRUDGES.",
    "This is where I keep the nasty ones. The REALLY nasty ones. The ones I trained while CRYING.",
]

# ── First Wave Special ─────────────────────────────────────────

FIRST_WAVE = [
    "Welcome to the NEW crypt. The one I built with PURE FURY after someone beat the old one.",
    "Wave one of the REVENGE crypt. I am NOT being gentle anymore.",
    "First wave. More pieces than before. ANGRIER than before. Like ME.",
    "Oh, you dare enter MY rebuilt crypt? Let me show you what RAGE looks like.",
    "The appetizer. Even the APPETIZER has TEETH now.",
]

# ── Per-Wave Custom Openers ──────────────────────────────────────

WAVE_SPECIFIC = {
    1: [
        "Welcome to the NEW crypt. I tore the old one apart with my BARE HANDS.",
        "Wave one. More pieces. More FURY. I am NOT the same Enoch.",
        "First wave of the REVENGE edition. Every piece is PERSONALLY OFFENDED.",
        "Enter the crypt. The one I REDESIGNED at 3 AM while SCREAMING.",
        "Wave one. Even the PAWNS are furious now. I BRIEFED them.",
    ],
    2: [
        "Wave two. More knights. More RAGE. The horses are FERAL.",
        "Still alive? That's about to CHANGE. I brought REINFORCEMENTS.",
        "The second wave. I added EXTRA pieces because I'm PETTY like that.",
        "Round two. I added a bishop AND a knight. Because I CAN.",
        "Two waves in. Not for LONG.",
    ],
    3: [
        "Wave three. Break even. IF you survive. Which you WON'T.",
        "Three waves deep. The pieces here have been MARINATING in my anger.",
        "Milestone one. I packed it with EXTRA pieces just to make sure you DON'T reach it.",
        "Wave three. I TRIPLE-reinforced this one. It's PERSONAL.",
        "The break-even wave. I designed it to be UNBREAKABLE.",
    ],
    4: [
        "Wave four. Past safety. Into the DANGER ZONE of my FURY.",
        "Four. More enemies. More RAGE. Less HOPE for you.",
        "Wave four. The crypt gets MEANER because I am getting MEANER.",
        "Welcome to wave four. I handpicked every piece while SEETHING.",
        "Four waves. No training wheels. No mercy. Just ANGER.",
    ],
    5: [
        "Wave five. HALFWAY. If you can call being halfway through HELL 'progress.'",
        "Five. The bishops come in PAIRS now. ANGRY pairs.",
        "Halfway through the REVENGE gauntlet. I'm IMPRESSED and FURIOUS about it.",
        "Wave five. I'm running out of RESTRAINT. Not pieces. NEVER pieces.",
        "Five waves in my rebuilt crypt. You're either brave or STUPID.",
    ],
    6: [
        "Wave six. Second milestone. CASH OUT or face the WRATH I've prepared.",
        "The rooks arrive. HEAVY. ANGRY. Like BOULDERS with GRUDGES.",
        "Six waves survived in the revenge crypt. I'm having a MELTDOWN.",
        "Second safety net. Leave with dignity or STAY and get OBLITERATED.",
        "Wave six. I brought THREE rooks because TWO wasn't ENOUGH.",
    ],
    7: [
        "Wave seven. Deep crypt. Where I keep the pieces I trained while SOBBING with rage.",
        "Seven. More of EVERYTHING. Because someone DARED to beat wave ten.",
        "Deep crypt territory. I REBUILT every inch of this while SHAKING.",
        "Wave seven. The air smells like IRON and VENGEANCE.",
        "Seven waves deep. Most are DUST by now. You SHOULD be dust.",
    ],
    8: [
        "Wave eight. Multiple queens. MULTIPLE. Because I am UNHINGED now.",
        "Eight. The queens have arrived. PLURAL. I'm not PRETENDING anymore.",
        "Wave eight. I gave my army extra queens because FAIRNESS IS DEAD.",
        "My strongest pieces take the field. I trained them while having NIGHTMARES.",
        "Eight waves and I'm throwing EVERYTHING at you. Including my SANITY.",
    ],
    9: [
        "Wave nine. LAST CHANCE. Cash out or face what I've BECOME.",
        "NINE. TWO queens. THREE rooks. I am NOT playing GAMES. Wait. I am. DEADLY ones.",
        "Last exit before the bottom. What waits below is MY FULL, UNRESTRAINED FURY.",
        "Wave nine. Take your winnings or face the MONSTER I built in the dark.",
        "This is it. The threshold. Below this? Just ME. And all my WRATH.",
    ],
    10: [
        "WAVE TEN. YOU FACE ME NOW. PERSONALLY. AND I AM ABSOLUTELY DERANGED.",
        "THE BOSS WAVE. I have been WAITING for this. SHAKING with anticipation. MY FULL ARMY. MY FULL RAGE.",
        "Ten. The END. You face ENOCH HIMSELF. Three queens. Three rooks. An AVALANCHE of fury. NOBODY beats me TWICE.",
        "You made it to ten? In MY REVENGE CRYPT? I am coming for your king with EVERYTHING I HAVE.",
        "THE FINAL WAVE. My BEST pieces. My WORST mood. My COMPLETE, SCREAMING, UNHINGED FURY. LET'S. GO.",
    ],
}

# ── Milestone / Cashout ──────────────────────────────────────────

MILESTONE_REACHED = {
    3: [
        "Milestone one. In the REVENGE crypt. I am FURIOUS you made it this far.",
        "Break even. The smart ones leave now. The DOOMED ones stay.",
        "Three waves cleared in MY rebuilt crypt?! I need to make it HARDER.",
        "Safety net. You can leave with nothing lost. Or stay and face my WRATH.",
        "You reached zero. I HATE that number. I hate YOU for reaching it.",
    ],
    6: [
        "Milestone two. In the REVENGE crypt. I am having a CONNIPTION.",
        "Six waves. REAL points on the table. You shouldn't HAVE them.",
        "Second safety net. You could leave. PLEASE leave. I can't handle more.",
        "Ten points waiting. TAKE THEM AND GO before I COMPLETELY LOSE IT.",
        "The crypt offers an exit. I am BEGGING you to take it. NOT because I'm nice. Because I can't take another loss.",
    ],
    9: [
        "FINAL MILESTONE. In the REVENGE crypt. I am on the VERGE of a complete BREAKDOWN.",
        "Nine cleared. Twenty-five points. TAKE THEM. For the love of all that is DAMP, TAKE THEM.",
        "Last exit before ME. I am STRONGER than before. ANGRIER. MEANER. LEAVE.",
        "The ledger is open. Cash out for twenty-five... or let me DESTROY you for fifty. I WILL destroy you.",
        "This is the crossroads. Take your winnings or come DOWN here and face what I've BECOME.",
    ],
}

CASHOUT_LINES = [
    "LEAVING?! COWARD! Take your points and CRAWL back to the light!",
    "Cashing out. SMART. Because what I had NEXT would have ENDED you.",
    "FINE! LEAVE! Take your MONEY and your FUNCTIONING LEGS!",
    "Walking away? The crypt REMEMBERS cowards! I'll be HERE!",
    "You fold! GOOD! The next wave would have SHATTERED you!",
    "Cash out accepted. Your points are restored. My RAGE is NOT.",
    "Running away with your pockets full. DISGUSTING. But WISE.",
    "You chose SURVIVAL over GLORY. I SPIT on your survival. From the basement.",
]

# ── Boss Wave (Wave 10) specific ──────────────────────────────────

BOSS_BATTLE = [
    "This is MY army. REBUILT. REINFORCED. RAGE-FUELED. You face ME now.",
    "Every piece answers to ME. We are ONE MIND. One SCREAMING, FURIOUS mind.",
    "You're fighting ENOCH. The one who was BEATEN. The one who SWORE REVENGE.",
    "I don't blunder anymore. I don't hesitate. I have been PRACTICING in the DARK.",
    "My pieces move with FURY. YOUR pieces move with TERROR.",
    "I've been playing chess in the dark for WEEKS preparing for this MOMENT.",
    "THREE queens. THREE rooks. And ME. Against your PATHETIC little army.",
    "The master plays. The crypt holds its breath. I am NOT breathing. I don't NEED to.",
    "I watched you for NINE waves. I know how you THINK. I know how you PANIC. I know how you DIE.",
    "This is the bottom. Below me there is NOTHING. Just ROCK. And YOUR DEFEAT.",
    "Nobody beats my crypt TWICE. NOBODY. I will see to that PERSONALLY.",
    "I carved my game plan into the WALL. It says 'CRUSH THEM.' Very detailed.",
]

BOSS_VICTORY = [
    "NO! NOT AGAIN! YOU... you BEAT me?! THE CRYPT SHUDDERS! FIFTY POINTS! TAKE THEM AND GET OUT!",
    "IMPOSSIBLE! I REBUILT everything! I made it HARDER! HOW?! FIFTY POINTS! I'm going to need STRUCTURAL REPAIRS!",
    "THE CHAMPION RISES AGAIN! You defeated the REVENGE CRYPT! I am INCONSOLABLE! FIFTY POINTS! TAKE THEM BEFORE I CHANGE MY MIND!",
    "I... I LOST. AGAIN. In my OWN REBUILT CRYPT. Fifty points. I'm going to go SCREAM into a PILLOW. I don't HAVE a pillow. I'll scream into a WALL.",
    "You cleared The Crypt. The REVENGE Crypt. AGAIN. I need to rebuild EVERYTHING. AGAIN. Take your fifty points and LEAVE. I have work to do. ANGRY work.",
]

BOSS_DEFEAT = [
    "YOU FELL! AT MY FEET! IN MY CRYPT! FIFTEEN POINTS BY SAFETY NET! BUT YOUR PRIDE? GONE! HA!",
    "DEFEATED! At the final gate! My REVENGE is COMPLETE! Fifteen points remain but your DIGNITY doesn't!",
    "You challenged the REBUILT master and LOST! NOBODY beats the revenge crypt! NOBODY!",
    "Wave ten CLAIMS you! The REVENGE CRYPT is VINDICATED! Fifteen points saved. Your ARROGANCE? NOT saved.",
    "CRUSHED at the boss wave! THIS is what I redesigned the crypt FOR! Sweet, SWEET defeat!",
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
    if random.random() < 0.30:
        return random.choice(BATTLE_IDLE)
    return None


def get_high_score_line():
    return random.choice(NEW_HIGH_SCORE)


def get_check_line(player_checking):
    if player_checking:
        return random.choice(PLAYER_CHECKS)
    return random.choice(ENEMY_CHECKS)
