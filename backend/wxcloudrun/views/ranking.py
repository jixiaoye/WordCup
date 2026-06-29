"""排行榜 API"""
from flask import Blueprint, request

from wxcloudrun.models import GameRoom, Match
from wxcloudrun.response import success_response

bp = Blueprint("ranking", __name__, url_prefix="/api/v1/ranking")


@bp.get("")
def get_ranking():
    limit = min(max(request.args.get("limit", 20, type=int), 1), 100)

    game_records = GameRoom.query.filter(
        GameRoom.status == "finished",
        GameRoom.current_match_id.isnot(None),
    ).all()

    match_ids = [r.current_match_id for r in game_records if r.current_match_id]
    if not match_ids:
        return success_response([])

    matches = {m.id: m for m in Match.query.filter(Match.id.in_(match_ids)).all()}
    player_stats = {}

    for record in game_records:
        match = matches.get(record.current_match_id)
        if not match:
            continue

        host_player = record.host_player
        guest_player = record.guest_player
        winner = match.winner

        if winner is None:
            for player in [host_player, guest_player]:
                if player not in player_stats:
                    player_stats[player] = {"wins": 0, "losses": 0, "draws": 0, "total": 0}
                player_stats[player]["draws"] = player_stats[player].get("draws", 0) + 1
                player_stats[player]["total"] += 1
            continue

        host_won = winner == match.team_home_id
        for player, is_host in [(host_player, True), (guest_player, False)]:
            if player not in player_stats:
                player_stats[player] = {"wins": 0, "losses": 0, "draws": 0, "total": 0}
            player_stats[player]["total"] += 1
            if (is_host and host_won) or (not is_host and not host_won):
                player_stats[player]["wins"] += 1
            else:
                player_stats[player]["losses"] += 1

    rankings = []
    for player_name, stats in player_stats.items():
        win_rate = round(stats["wins"] / max(stats["total"], 1) * 100, 1)
        rankings.append({
            "player_name": player_name,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "draws": stats.get("draws", 0),
            "total": stats["total"],
            "win_rate": win_rate,
        })

    rankings.sort(key=lambda r: (-r["win_rate"], -r["wins"]))
    return success_response(rankings[:limit])
