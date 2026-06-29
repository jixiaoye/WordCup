"""萌宠 API"""
from flask import Blueprint, request

from wxcloudrun.models import Mascot
from wxcloudrun.response import success_response, error_response

bp = Blueprint("mascots", __name__, url_prefix="/api/v1/mascots")


def _mascot_dict(m):
    return {
        "team_id": m.team_id,
        "name": m.name,
        "name_en": m.name_en,
        "icon": m.icon,
        "element": m.element,
        "rarity": m.rarity,
        "boost_attack": m.boost_attack,
        "boost_defense": m.boost_defense,
        "boost_speed": m.boost_speed,
        "boost_spirit": m.boost_spirit,
        "description": m.description,
        "description_en": m.description_en,
    }


@bp.get("")
def list_mascots():
    team_id = request.args.get("team_id")
    query = Mascot.query
    if team_id:
        query = query.filter_by(team_id=team_id.upper())
    mascots = query.all()
    items = [_mascot_dict(m) for m in mascots]
    return success_response({"items": items, "total": len(items)})


@bp.get("/<team_id>")
def get_mascot(team_id):
    mascot = Mascot.query.filter_by(team_id=team_id.upper()).first()
    if not mascot:
        return error_response(f"球队 {team_id} 的萌宠不存在", status_code=404)
    return success_response(_mascot_dict(mascot))
