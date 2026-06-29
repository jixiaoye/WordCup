"""球队 API"""
from flask import Blueprint, request

from wxcloudrun.models import Team, Player
from wxcloudrun.response import success_response, error_response

bp = Blueprint("teams", __name__, url_prefix="/api/v1/teams")


def _player_dict(p):
    return {
        "id": p.id,
        "name_cn": p.name_cn,
        "name_en": p.name_en,
        "position": p.position,
        "number": p.number,
        "pace": p.pace,
        "shooting": p.shooting,
        "passing": p.passing,
        "defense": p.defense,
        "stamina": p.stamina,
        "physical": p.physical,
        "overall": p.overall,
    }


@bp.get("")
def list_teams():
    tier = request.args.get("tier", type=int)
    query = Team.query.order_by(Team.tier, Team.name_cn)
    if tier is not None:
        query = query.filter_by(tier=tier)
    teams = query.all()
    items = [
        {
            "id": t.id,
            "name_cn": t.name_cn,
            "name_en": t.name_en,
            "flag_emoji": t.flag_emoji,
            "continent": t.continent,
            "tier": t.tier,
            "overall": t.overall,
            "color_primary": t.color_primary,
            "color_secondary": t.color_secondary,
        }
        for t in teams
    ]
    return success_response({"items": items, "total": len(items)})


@bp.get("/<team_id>")
def get_team(team_id):
    team = Team.query.filter_by(id=team_id.upper()).first()
    if not team:
        return error_response(f"球队 {team_id} 不存在", status_code=404)

    players = Player.query.filter_by(team_id=team.id).order_by(
        Player.position, Player.number
    ).all()

    return success_response({
        "id": team.id,
        "name_cn": team.name_cn,
        "name_en": team.name_en,
        "flag_emoji": team.flag_emoji,
        "continent": team.continent,
        "tier": team.tier,
        "overall": team.overall,
        "color_primary": team.color_primary,
        "color_secondary": team.color_secondary,
        "players": [_player_dict(p) for p in players],
    })


@bp.get("/<team_id>/players")
def get_team_players(team_id):
    team = Team.query.filter_by(id=team_id.upper()).first()
    if not team:
        return error_response(f"球队 {team_id} 不存在", status_code=404)

    players = Player.query.filter_by(team_id=team.id).order_by(
        Player.position, Player.number
    ).all()
    return success_response([_player_dict(p) for p in players])
