"""Per-player daily login greetings spoken by Enoch."""

import random

PLAYER_GREETINGS = {
    'BundaBomber69': [
        "Ah… BundaBomber69. A name that makes the ink in my ledger curdle. Welcome back to the damp.",
        "The floorboards groan under the weight of that ridiculous name. BundaBomber69 has returned.",
        "I wrote your name in the ledger once. The quill snapped. I blame you entirely, BundaBomber69.",
        "BundaBomber69. You left no biography. An empty page. I stared at it for hours. It was the most honest thing in the archive.",
        "The spiders scattered when they heard you were coming. Even they have standards, BundaBomber69.",
    ],
    'andrewmuckerofstalls': [
        "The stable boy returns. I can smell the hay and horse sweat from down here, andrewmuckerofstalls.",
        "Ah, the mucker of stalls. You tend the knight stables above while I tend the records below. We are both servants of the filth.",
        "andrewmuckerofstalls. An honest title. The bishops' vestments will not clean themselves, and neither will this board.",
        "I see the ordained laborer has left his pitchfork by the door. Welcome back to a different kind of muck.",
        "You reek of the stables, andrewmuckerofstalls. Down here, we only reek of ink and regret. Sit. Play.",
    ],
    'defenderofknight': [
        "The knight's champion returns. Your treasonous little biography still keeps me up at night, defenderofknight.",
        "Ah, defenderofknight. Still dreaming of bishops bending knees and knights rising above their station. Dangerous words in these vaults.",
        "I read your manifesto again last night. The Lord of Schools bending his knee… the very thought made my candle flicker, defenderofknight.",
        "The defender of knights has arrived. The pawns in your little revolution will not protect themselves. Sit down.",
        "defenderofknight. You speak of restoring order, but I have seen your games. You cannot even restore your own back rank.",
    ],
}


def get_login_greeting(username):
    """Return a random greeting for this player, or None if no custom lines."""
    lines = PLAYER_GREETINGS.get(username)
    if not lines:
        return None
    return random.choice(lines)
