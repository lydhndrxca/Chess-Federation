from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from . import data as db
from .auth import login_required, check_password

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    players = db.get_players()
    return render_template("index.html", players=players)


@bp.route("/hierarchy")
def hierarchy():
    ranks = db.all_ranks()
    players = db.get_players()
    players_by_rank: dict[int, list] = {}
    for p in players:
        players_by_rank.setdefault(p["rank"], []).append(p)
    return render_template("hierarchy.html", ranks=ranks, players_by_rank=players_by_rank)


@bp.route("/players")
def players():
    return render_template("players.html", players=db.get_players())


@bp.route("/player/<player_id>")
def player_detail(player_id):
    player = db.get_player(player_id)
    if not player:
        return "Player not found", 404
    games = db.get_player_games(player_id)
    all_players = {p["id"]: p["name"] for p in db.get_players()}
    return render_template(
        "player_detail.html",
        player=player,
        games=games,
        all_players=all_players,
        rank_name=db.rank_name,
    )


@bp.route("/chronicles")
def chronicles():
    return render_template("chronicles.html")


# --- Admin routes ---

@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if check_password(request.form.get("password", "")):
            session["admin"] = True
            return redirect(url_for("main.admin"))
        flash("Incorrect password.")
    return render_template("admin_login.html")


@bp.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("main.index"))


@bp.route("/admin")
@login_required
def admin():
    players = db.get_players()
    return render_template("admin.html", players=players)


@bp.route("/admin/record-match", methods=["POST"])
@login_required
def record_match():
    winner = request.form["winner"]
    loser = request.form["loser"]
    pgn = request.form.get("pgn", "")
    if winner == loser:
        flash("Winner and loser must be different players.")
        return redirect(url_for("main.admin"))
    try:
        db.record_match(winner, loser, pgn)
        flash("Match recorded.")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for("main.admin"))


@bp.route("/admin/add-player", methods=["POST"])
@login_required
def add_player():
    pid = request.form["id"].strip().lower().replace(" ", "-")
    name = request.form["name"].strip()
    title = request.form.get("title", "").strip()
    bio = request.form.get("bio", "").strip()
    if not pid or not name:
        flash("ID and Name are required.")
        return redirect(url_for("main.admin"))
    try:
        db.add_player(pid, name, title, bio)
        flash(f"Player '{name}' added.")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for("main.admin"))


@bp.route("/admin/remove-player/<player_id>", methods=["POST"])
@login_required
def remove_player(player_id):
    db.remove_player(player_id)
    flash("Player removed.")
    return redirect(url_for("main.admin"))


@bp.route("/admin/edit-player/<player_id>", methods=["POST"])
@login_required
def edit_player(player_id):
    fields = {}
    for key in ("name", "title", "bio", "status"):
        val = request.form.get(key)
        if val is not None:
            fields[key] = val.strip()
    rank_val = request.form.get("rank")
    if rank_val is not None:
        try:
            fields["rank"] = max(1, min(10, int(rank_val)))
        except ValueError:
            pass
    db.update_player(player_id, fields)
    flash("Player updated.")
    return redirect(url_for("main.admin"))
