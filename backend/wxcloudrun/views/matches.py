"""比赛 API"""
import json
from datetime import datetime, timezone

from flask import Blueprint, request

from wxcloudrun import db
from wxcloudrun.models import Team, Player, Match, MatchEvent, Mascot
from wxcloudrun.services.match_engine import MatchEngine
from wxcloudrun.services.player_development import check_match_achievements, apply_match_xp
from wxcloudrun.response import success_response, error_response

bp = Blueprint("matches", __name__, url_prefix="/api/v1/matches")


def _make_team_dict(team, players):
    return {
        "team_id": team.id,
        "name": team.name_en,
        "players": [
            {
                "id": p.id,
                "name": p.name_en,
                "name_cn": p.name_cn,
                "position": p.position,
                "pace": p.pace,
                "shooting": p.shooting,
                "passing": p.passing,
                "defense": p.defense,
                "stamina": p.stamina,
                "physical": p.physical,
            }
            for p in players
        ],
    }


@bp.post("/simulate")
def simulate_match():
    body = request.get_json(silent=True) or {}
    home_id = body.get("team_home_id", "").upper()
    away_id = body.get("team_away_id", "").upper()
    formation_home = body.get("formation_home", "4-4-2")
    formation_away = body.get("formation_away", "4-4-2")
    weather = body.get("weather", "sunny")

    home_team = Team.query.filter_by(id=home_id).first()
    away_team = Team.query.filter_by(id=away_id).first()
    if not home_team:
        return error_response(f"主队 {home_id} 不存在", status_code=404)
    if not away_team:
        return error_response(f"客队 {away_id} 不存在", status_code=404)

    all_players = Player.query.filter(Player.team_id.in_([home_id, away_id])).all()
    home_players = [p for p in all_players if p.team_id == home_id]
    away_players = [p for p in all_players if p.team_id == away_id]

    mascot_boosts = {}
    for mid in [body.get("mascot_team_home_id"), body.get("mascot_team_away_id")]:
        if mid:
            mascot = Mascot.query.filter_by(team_id=mid.upper()).first()
            if mascot:
                boosts = {}
                if mascot.boost_attack:
                    boosts["attack"] = mascot.boost_attack
                if mascot.boost_defense:
                    boosts["defense"] = mascot.boost_defense
                if mascot.boost_speed:
                    boosts["speed"] = mascot.boost_speed
                if mascot.boost_spirit:
                    boosts["spirit"] = mascot.boost_spirit
                mascot_boosts[mascot.team_id] = boosts

    engine = MatchEngine(
        _make_team_dict(home_team, home_players),
        _make_team_dict(away_team, away_players),
        mascot_boosts=mascot_boosts or None,
        formation_home=formation_home,
        formation_away=formation_away,
        weather=weather,
    )
    report = engine.simulate()

    match_record = Match(
        team_home_id=home_id,
        team_away_id=away_id,
        home_score=report["home_score"],
        away_score=report["away_score"],
        home_penalty=report["home_penalty"],
        away_penalty=report["away_penalty"],
        status="finished",
        winner=report["winner"],
        match_report=json.dumps(report, ensure_ascii=False),
        finished_at=datetime.now(timezone.utc),
    )
    db.session.add(match_record)
    db.session.flush()

    for evt in report["events"]:
        db.session.add(MatchEvent(
            match_id=match_record.id,
            minute=evt["minute"],
            type=evt["type"],
            team_id=evt["team_id"],
            player_id=evt.get("player_id"),
            player_name=evt.get("player_name"),
            detail=evt.get("detail"),
        ))

    db.session.flush()

    event_list = [
        {
            "minute": e.get("minute"),
            "type": e.get("type"),
            "team_id": e.get("team_id"),
            "player_name": e.get("player_name"),
            "player_id": e.get("player_id"),
            "detail": e.get("detail"),
        }
        for e in report.get("events", [])
    ]
    newly_unlocked = check_match_achievements(
        match_id=match_record.id,
        home_team_id=home_id,
        away_team_id=away_id,
        home_score=report["home_score"],
        away_score=report["away_score"],
        home_penalty=report.get("home_penalty"),
        away_penalty=report.get("away_penalty"),
        winner=report["winner"],
        match_events=event_list,
        home_tier=home_team.tier,
        away_tier=away_team.tier,
        match_highlights=report.get("highlights", []),
    )

    xp_gains = []
    winner = report.get("winner")
    if winner:
        winner_players = Player.query.filter_by(team_id=winner).all()
        if winner_players:
            winner_ids = [p.id for p in winner_players]
            winner_positions = {p.id: p.position for p in winner_players}
            xp_gains = apply_match_xp(winner, winner_ids, winner_positions)

    db.session.commit()

    return success_response({
        "id": match_record.id,
        "team_home_id": home_id,
        "team_away_id": away_id,
        "home_score": report["home_score"],
        "away_score": report["away_score"],
        "winner": report["winner"],
        "duration": report["duration"],
        "events": report["events"],
        "player_ratings": report["player_ratings"],
        "highlights": report.get("highlights", []),
        "achievements": newly_unlocked,
        "xp_gains": xp_gains,
    })


@bp.get("/<int:match_id>")
def get_match(match_id):
    match = Match.query.get(match_id)
    if not match:
        return error_response("比赛不存在", status_code=404)

    events = MatchEvent.query.filter_by(match_id=match_id).order_by(MatchEvent.minute).all()
    report = json.loads(match.match_report) if match.match_report else {}

    return success_response({
        "id": match.id,
        "team_home_id": match.team_home_id,
        "team_away_id": match.team_away_id,
        "home_score": match.home_score,
        "away_score": match.away_score,
        "home_penalty": match.home_penalty,
        "away_penalty": match.away_penalty,
        "winner": match.winner,
        "status": match.status,
        "events": [
            {
                "minute": e.minute,
                "type": e.type,
                "team_id": e.team_id,
                "player_name": e.player_name,
                "detail": e.detail,
            }
            for e in events
        ],
        "player_ratings": report.get("player_ratings", {}),
        "highlights": report.get("highlights", []),
        "match_report": report,
        "formation_home": report.get("formation_home", ""),
        "formation_away": report.get("formation_away", ""),
        "weather": report.get("weather", ""),
        "substitutions_home": report.get("substitutions_home", 0),
        "substitutions_away": report.get("substitutions_away", 0),
        "created_at": match.created_at.isoformat() if match.created_at else None,
    })


@bp.get("")
def list_matches():
    limit = min(max(request.args.get("limit", 20, type=int), 1), 100)
    offset = max(request.args.get("offset", 0, type=int), 0)
    matches = Match.query.order_by(Match.created_at.desc()).offset(offset).limit(limit).all()

    return success_response([
        {
            "id": m.id,
            "team_home_id": m.team_home_id,
            "team_away_id": m.team_away_id,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "winner": m.winner,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in matches
    ])
