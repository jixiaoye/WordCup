"""成就 API"""
import json

from flask import Blueprint, request

from wxcloudrun.models import Match, MatchEvent, Team
from wxcloudrun.services.player_development import (
    get_all_achievements,
    get_unlocked_achievements,
    check_match_achievements,
    reset_all_state,
)
from wxcloudrun.response import success_response, error_response

bp = Blueprint("achievements", __name__, url_prefix="/api/v1/achievements")


@bp.get("")
def list_achievements():
    items = get_all_achievements()
    unlocked_count = sum(1 for a in items if a.get("unlocked"))
    return success_response({
        "items": items,
        "total": len(items),
        "unlocked_count": unlocked_count,
    })


@bp.post("/check")
def check_achievements():
    body = request.get_json(silent=True) or {}
    match_id = body.get("match_id")
    if not match_id:
        return error_response("缺少 match_id", status_code=400)

    match_record = Match.query.get(match_id)
    if not match_record:
        return error_response(f"比赛 {match_id} 不存在", status_code=404)

    events = MatchEvent.query.filter_by(match_id=match_id).order_by(MatchEvent.minute).all()
    home_team = Team.query.filter_by(id=match_record.team_home_id).first()
    away_team = Team.query.filter_by(id=match_record.team_away_id).first()
    home_tier = home_team.tier if home_team else 2
    away_tier = away_team.tier if away_team else 2

    match_report = {}
    if match_record.match_report:
        try:
            match_report = json.loads(match_record.match_report)
        except (json.JSONDecodeError, TypeError):
            pass

    event_list = [
        {
            "minute": e.minute,
            "type": e.type,
            "team_id": e.team_id,
            "player_name": e.player_name,
            "player_id": e.player_id,
            "detail": e.detail,
        }
        for e in events
    ]

    newly_unlocked = check_match_achievements(
        match_id=match_record.id,
        home_team_id=match_record.team_home_id,
        away_team_id=match_record.team_away_id,
        home_score=match_record.home_score,
        away_score=match_record.away_score,
        home_penalty=match_record.home_penalty,
        away_penalty=match_record.away_penalty,
        winner=match_record.winner,
        match_events=event_list,
        home_tier=home_tier,
        away_tier=away_tier,
        match_highlights=match_report.get("highlights", []),
    )

    return success_response({
        "newly_unlocked": newly_unlocked,
        "unlocked_count": sum(1 for a in get_all_achievements() if a.get("unlocked")),
    })


@bp.get("/unlocked")
def unlocked_achievements():
    items = get_unlocked_achievements()
    return success_response({"items": items, "total": len(items)})


@bp.post("/reset")
def reset_achievements():
    reset_all_state()
    return success_response({"message": "成就状态已重置"})
