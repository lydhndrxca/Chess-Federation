import json
import os
import copy

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "players.json")

_RANK_NAMES = {
    10: "Lord of Schools",
    9: "Keeper of the Light of the Lord of Schools",
    8: "Most Esteemed Subordinate to the Keeper of the Light of the Lord of Schools",
    7: "Esteemed Supreme Grandmaster \u2013 Level 3",
    6: "Esteemed Supreme Grandmaster \u2013 Level 2",
    5: "Esteemed Supreme Grandmaster \u2013 Level 1",
    4: "Living Bishop with Holiness",
    3: "Most Delicate Acolyte to the Bishop with Holiness",
    2: "Most Subordinate to the Relative Command of the Bishop with Holiness",
    1: "Ordained Laborer of the Stables and Bishop\u2019s Vestments",
}

_RANK_DESCRIPTIONS = {
    10: "Supreme authority of the federation and final arbiter of all games, ranks, and ordinations.",
    9: "Guardian of the authority and illumination that flows from the Lord of Schools.",
    8: "Direct adjutant serving the Keeper of the Light.",
    7: "Unknown.",
    6: "Unknown.",
    5: "Unknown.",
    4: "A consecrated station marking passage into the higher order of the federation, signifying recognition with ceremonial dignity and spiritual authority within the structure.",
    3: "Serves beneath the Living Bishop with Holiness with careful obedience and ceremonial sensitivity.",
    2: "Operates under the direction of the delicate acolyte order.",
    1: "Performs the physical duties of tending the knight stables and maintaining the vestments and equipment of the bishops.",
}


def rank_name(rank_number: int) -> str:
    return _RANK_NAMES.get(rank_number, "Unknown Rank")


def rank_description(rank_number: int) -> str:
    return _RANK_DESCRIPTIONS.get(rank_number, "")


def all_ranks():
    return [
        {"number": n, "name": _RANK_NAMES[n], "description": _RANK_DESCRIPTIONS[n]}
        for n in range(10, 0, -1)
    ]


def load_data() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_players() -> list:
    data = load_data()
    players = copy.deepcopy(data.get("players", []))
    for p in players:
        p["rank_name"] = rank_name(p["rank"])
    return players


def get_player(player_id: str) -> dict | None:
    for p in get_players():
        if p["id"] == player_id:
            return p
    return None


def get_games() -> list:
    return load_data().get("games", [])


def get_player_games(player_id: str) -> list:
    return [g for g in get_games() if player_id in (g["white"], g["black"])]


def record_match(winner_id: str, loser_id: str, pgn: str = ""):
    data = load_data()
    players = data["players"]
    games = data.setdefault("games", [])

    winner = next((p for p in players if p["id"] == winner_id), None)
    loser = next((p for p in players if p["id"] == loser_id), None)
    if not winner or not loser:
        raise ValueError("Player not found")

    winner["wins"] = winner.get("wins", 0) + 1
    winner["rank"] = min(winner.get("rank", 1) + 1, 10)

    loser["losses"] = loser.get("losses", 0) + 1
    loser["rank"] = max(loser.get("rank", 1) - 1, 1)

    game_id = f"game-{len(games) + 1:03d}"
    result = "1-0" if winner_id == winner_id else "0-1"
    games.append({
        "id": game_id,
        "white": winner_id,
        "black": loser_id,
        "result": "1-0",
        "pgn": pgn,
        "lore_title": "",
        "lore_description": "",
    })

    save_data(data)


def add_player(player_id: str, name: str, title: str = "", bio: str = ""):
    data = load_data()
    if any(p["id"] == player_id for p in data["players"]):
        raise ValueError("Player already exists")

    data["players"].append({
        "id": player_id,
        "name": name,
        "title": title,
        "rank": 1,
        "wins": 0,
        "losses": 0,
        "bio": bio,
        "status": "member",
        "portrait": "",
    })
    save_data(data)


def remove_player(player_id: str):
    data = load_data()
    data["players"] = [p for p in data["players"] if p["id"] != player_id]
    save_data(data)


def update_player(player_id: str, fields: dict):
    data = load_data()
    for p in data["players"]:
        if p["id"] == player_id:
            for key in ("name", "title", "bio", "status", "rank"):
                if key in fields:
                    p[key] = fields[key]
            break
    save_data(data)
