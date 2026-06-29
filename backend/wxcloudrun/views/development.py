"""球员养成 API"""
from flask import Blueprint, request

from wxcloudrun.models import Match, Player
from wxcloudrun.services.player_development import (
    get_all_player_dev_state,
    get_player_dev_state,
    apply_match_xp,
    reset_all_state,
)
from wxcloudrun.response import success_response, error_response

bp = Blueprint("development", __name__, url_prefix="/api/v1/development")


@bp.post("/apply-match")
def apply_match():
    body = request.get_json(silent=True) or {}
    match_id = body.get("match_id")
    if not match_id:
        return error_response("缺少 match_id", status_code=400)

    match_record = Match.query.get(match_id)
    if not match_record:
        return error_response(f"比赛 {match_id} 不存在", status_code=404)

    winner = match_record.winner
    if not winner:
        return success_response({"message": "平局，无经验分配", "gains": []})

    players = Player.query.filter_by(team_id=winner).all()
    if not players:
        return error_response(f"球队 {winner} 没有球员数据", status_code=404)

    player_ids = [p.id for p in players]
    player_positions = {p.id: p.position for p in players}
    gains = apply_match_xp(winner, player_ids, player_positions)

    return success_response({
        "match_id": match_id,
        "winner": winner,
        "player_count": len(players),
        "awarded_count": len(gains),
        "gains": gains,
    })


@bp.get("/players")
def list_player_dev():
    team_id = request.args.get("team_id")
    query = Player.query
    if team_id:
        query = query.filter_by(team_id=team_id.upper())
    players = query.all()

    items = []
    for p in players:
        state = get_player_dev_state(p.id)
        items.append({
            "player_id": p.id,
            "name_cn": p.name_cn,
            "name_en": p.name_en,
            "position": p.position,
            "team_id": p.team_id,
            "overall": p.overall,
            "xp": state["xp"],
            "level": state["level"],
            "boosts": state["boosts"],
        })

    return success_response({"items": items, "total": len(items)})


@bp.get("/players/<int:player_id>")
def get_player_dev(player_id):
    player = Player.query.get(player_id)
    if not player:
        return error_response(f"球员 {player_id} 不存在", status_code=404)

    state = get_player_dev_state(player.id)
    return success_response({
        "player_id": player.id,
        "name_cn": player.name_cn,
        "name_en": player.name_en,
        "position": player.position,
        "team_id": player.team_id,
        "overall": player.overall,
        "pace": player.pace,
        "shooting": player.shooting,
        "passing": player.passing,
        "defense": player.defense,
        "stamina": player.stamina,
        "physical": player.physical,
        "xp": state["xp"],
        "level": state["level"],
        "boosts": state["boosts"],
    })


@bp.post("/reset")
def reset_development():
    reset_all_state()
    return success_response({"message": "养成状态已重置"})
