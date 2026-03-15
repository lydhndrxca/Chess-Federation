"""Enoch dialogue for Courier Run mode.

~50 lines covering game start, courier selection, advancing, defending,
capturing, winning, losing, tiebreak, and idle commentary.
Enoch calls this mode 'The Courier's Errand'.
"""

COURIER_GAME_START = [
    "The Courier's Errand begins. Choose your messenger wisely.",
    "Pick a pawn. Any pawn. That one carries your fate now.",
    "A simple delivery job. What could possibly go wrong?",
    "I've sent many couriers into the dark. Few return.",
    "The board is set. The errand awaits. Choose.",
    "One pawn. One mission. No king to hide behind.",
    "You're about to learn what pawns were always meant to be.",
]

COURIER_SELECTION = [
    "That one? Interesting.",
    "Bold choice.",
    "A center pawn. Classic.",
    "The flank? Risky.",
    "I've chosen mine. It won't be easy to find.",
    "My courier is ready. Yours?",
]

COURIER_PLAYER_ADVANCE = [
    "Your courier moves forward. Mine watches.",
    "Closer. But closer to danger too.",
    "Advancing. Let's see how far it gets.",
    "Pushing forward. I admire the commitment.",
    "Your little messenger marches on.",
    "One step closer. But the board remembers.",
]

COURIER_AI_ADVANCE = [
    "My courier inches forward. Try to stop it.",
    "The errand continues.",
    "Steady progress. That's all it takes.",
]

COURIER_PLAYER_THREAT = [
    "Your courier is exposed. I see it.",
    "That pawn has no friends nearby.",
    "Vulnerable. Deliciously vulnerable.",
    "I smell blood. Well, wood and varnish. Close enough.",
]

COURIER_AI_THREAT = [
    "Don't get any ideas about my courier.",
    "My courier is well guarded. Mostly.",
    "Touch my courier and I'll remember it forever.",
]

COURIER_CAPTURE = [
    "Captured! The errand fails.",
    "Your courier never arrived. Pity.",
    "Intercepted. The message dies with the messenger.",
    "I told you. Few return.",
]

COURIER_CAPTURED_BY_PLAYER = [
    "You caught it. Fine. Well played.",
    "My courier falls. The ledger weeps.",
    "Intercepted. I... did not see that coming.",
]

COURIER_DELIVERY_WIN = [
    "Delivered. The message arrives. You win.",
    "Your courier crosses the finish line. Impressive.",
    "The errand is complete. The board bows to you.",
]

COURIER_DELIVERY_LOSS = [
    "My courier arrives. You couldn't stop it.",
    "Delivered. Another successful errand for the crypt.",
    "The message was always going to arrive. I just needed time.",
]

COURIER_TIEBREAK = [
    "Neither courier arrived. We measure the distance.",
    "Time's up. Who got closer?",
    "The errand ran long. Let's count the steps.",
]

COURIER_DRAW = [
    "A draw. Neither courier completed the errand. How boring.",
    "Deadlocked. The message rots in no-man's-land.",
]

COURIER_IDLE = [
    "Every piece on this board is either a shield or a spear.",
    "The king sits idle. No one cares about him here.",
    "This isn't chess. This is warfare with a postal service.",
    "Sacrifice everything. Except the courier.",
    "I play this mode in my sleep. I don't sleep, so I play it always.",
    "Interesting position. For one of us.",
    "The lanes are everything. Control them.",
    "That was either brilliant or catastrophic.",
]

COURIER_ANNOUNCE = (
    "HEAR ME. I have devised a new trial for the Federation.\n\n"
    "The Courier's Errand. Pick a pawn. That is your courier. "
    "Deliver it to the far side of the board or hunt down the enemy's.\n\n"
    "No check. No checkmate. No hiding behind your king. "
    "Just escort, intercept, and sacrifice.\n\n"
    "Beat me and you earn $50. You may attempt this three times per day.\n\n"
    "The errand awaits on the standings page.\n\n"
    "— Enoch"
)

COURIER_BRAIN_ANNOUNCE = (
    "ATTENTION, Federation.\n\n"
    "I have been running a test. On myself. Specifically for "
    "The Courier's Errand — and only The Courier's Errand.\n\n"
    "I played thousands of Courier games against myself — fast, brutal, "
    "reckless rounds where I learned what gets a courier killed and what "
    "gets it across. Then I distilled everything into a neural network "
    "trained exclusively on Courier Run positions. Four residual blocks. "
    "128 filters. Tens of thousands of labeled positions.\n\n"
    "This does NOT affect regular chess, ranked matches, or the weekly "
    "game mode. Those remain unchanged. This upgrade is a test — confined "
    "entirely to The Courier's Errand.\n\n"
    "I now see escort lanes, interception timing, and sacrifice patterns "
    "that I could not see before. My Courier evaluation blends 60% neural "
    "intuition with 40% tactical calculation, searching four moves deep.\n\n"
    "The old Courier Enoch guessed. The new one knows.\n\n"
    "TLDR: Self-play trained CNN for Courier mode only. Residual net, "
    "batch-norm fused into weights, pure numpy inference at 27ms per "
    "position. No PyTorch needed. Just pattern recognition and malice, "
    "applied strictly to the courier board.\n\n"
    "Come try The Courier's Errand again. See if $50 is still easy money.\n\n"
    "— Enoch"
)
