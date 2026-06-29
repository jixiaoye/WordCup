"""锦标赛 API"""
import json
import random
from datetime import datetime, timezone

from flask import Blueprint, request

from wxcloudrun import db
from wxcloudrun.models import Team, Player, Match, Tournament, TournamentMatch
from wxcloudrun.services.match_engine import MatchEngine
from wxcloudrun.services.player_development import check_match_achievements, apply_match_xp
from wxcloudrun.response import success_response, error_response

bp = Blueprint("tournament", __name__, url_prefix="/api/v1/tournament")

ROUND_NAMES = {1: "16强", 2: "8强", 3: "4强", 4: "决赛"}
TOURNAMENT_TEAM_COUNT = 16


def _load_team_players(team_id):
    team = Team.query.filter_by(id=team_id).first()
    if not team:
        return None
    players = Player.query.filter_by(team_id=team_id).all()
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


def _simulate_tournament_match(tmatch):
    home_dict = _load_team_players(tmatch.team_home_id)
    away_dict = _load_team_players(tmatch.team_away_id)
    engine = MatchEngine(home_dict, away_dict)
    report = engine.simulate()

    match_record = Match(
        team_home_id=tmatch.team_home_id,
        team_away_id=tmatch.team_away_id,
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

    tmatch.home_score = report["home_score"]
    tmatch.away_score = report["away_score"]
    tmatch.home_penalty = report["home_penalty"]
    tmatch.away_penalty = report["away_penalty"]
    tmatch.winner = report["winner"]
    tmatch.status = "finished"
    tmatch.match_id = match_record.id
    tmatch.match_report_json = json.dumps(report, ensure_ascii=False)

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
    home_team_obj = Team.query.filter_by(id=tmatch.team_home_id).first()
    away_team_obj = Team.query.filter_by(id=tmatch.team_away_id).first()

    check_match_achievements(
        match_id=match_record.id,
        home_team_id=tmatch.team_home_id,
        away_team_id=tmatch.team_away_id,
        home_score=report["home_score"],
        away_score=report["away_score"],
        home_penalty=report.get("home_penalty"),
        away_penalty=report.get("away_penalty"),
        winner=report["winner"],
        match_events=event_list,
        home_tier=home_team_obj.tier if home_team_obj else 2,
        away_tier=away_team_obj.tier if away_team_obj else 2,
        match_highlights=report.get("highlights", []),
    )

    winner = report.get("winner")
    if winner:
        winner_players = Player.query.filter_by(team_id=winner).all()
        if winner_players:
            apply_match_xp(
                winner,
                [p.id for p in winner_players],
                {p.id: p.position for p in winner_players},
            )

    return {
        "match_id": match_record.id,
        "team_home_id": tmatch.team_home_id,
        "team_away_id": tmatch.team_away_id,
        "home_score": report["home_score"],
        "away_score": report["away_score"],
        "home_penalty": report["home_penalty"],
        "away_penalty": report["away_penalty"],
        "winner": report["winner"],
        "duration": report["duration"],
        "events": report["events"],
        "player_ratings": report.get("player_ratings", {}),
    }


def _update_bracket_json(tournament):
    all_tms = TournamentMatch.query.filter_by(
        tournament_id=tournament.id
    ).order_by(TournamentMatch.round_number, TournamentMatch.match_order).all()

    bracket = []
    for rnd in range(1, 5):
        rnd_matches = [tm for tm in all_tms if tm.round_number == rnd]
        bracket.append({
            "round_number": rnd,
            "round_name": ROUND_NAMES.get(rnd, ""),
            "matches": [
                {
                    "id": tm.id,
                    "round_number": tm.round_number,
                    "match_order": tm.match_order,
                    "team_home_id": tm.team_home_id,
                    "team_away_id": tm.team_away_id,
                    "home_score": tm.home_score,
                    "away_score": tm.away_score,
                    "home_penalty": tm.home_penalty,
                    "away_penalty": tm.away_penalty,
                    "winner": tm.winner,
                    "status": tm.status,
                    "match_id": tm.match_id,
                }
                for tm in rnd_matches
            ],
        })
    tournament.bracket_json = json.dumps(bracket, ensure_ascii=False)


@bp.post("/create")
def create_tournament():
    body = request.get_json(silent=True) or {}
    all_teams = Team.query.order_by(Team.id).all()

    if len(all_teams) < TOURNAMENT_TEAM_COUNT:
        return error_response(
            f"球队数量不足，需要{TOURNAMENT_TEAM_COUNT}支，当前有{len(all_teams)}支",
            status_code=400,
        )

    selected_teams = random.sample(all_teams, TOURNAMENT_TEAM_COUNT)
    team_ids = [t.id for t in selected_teams]

    name = body.get(
        "name",
        f"世界杯淘汰赛 #{datetime.now(timezone.utc).strftime('%m%d%H%M')}",
    )
    tournament = Tournament(
        name=name,
        status="draw",
        round_name="16强",
        current_round=1,
        teams_json=json.dumps(team_ids, ensure_ascii=False),
        bracket_json=json.dumps([], ensure_ascii=False),
    )
    db.session.add(tournament)
    db.session.flush()

    random.shuffle(team_ids)
    bracket = []
    round_matches = []

    for i in range(0, TOURNAMENT_TEAM_COUNT, 2):
        match_order = i // 2
        tm = TournamentMatch(
            tournament_id=tournament.id,
            round_number=1,
            match_order=match_order,
            team_home_id=team_ids[i],
            team_away_id=team_ids[i + 1],
            status="pending",
        )
        db.session.add(tm)
        db.session.flush()
        round_matches.append({
            "id": tm.id,
            "round_number": 1,
            "match_order": match_order,
            "team_home_id": team_ids[i],
            "team_away_id": team_ids[i + 1],
            "home_score": 0,
            "away_score": 0,
            "home_penalty": None,
            "away_penalty": None,
            "winner": None,
            "status": "pending",
            "match_id": None,
        })

    bracket.append({
        "round_number": 1,
        "round_name": "16强",
        "matches": round_matches,
    })

    for rnd in [2, 3, 4]:
        match_count = TOURNAMENT_TEAM_COUNT // (2 ** rnd)
        round_matches = []
        for order in range(match_count):
            tm = TournamentMatch(
                tournament_id=tournament.id,
                round_number=rnd,
                match_order=order,
                team_home_id=None,
                team_away_id=None,
                status="pending",
            )
            db.session.add(tm)
            db.session.flush()
            round_matches.append({
                "id": tm.id,
                "round_number": rnd,
                "match_order": order,
                "team_home_id": None,
                "team_away_id": None,
                "home_score": 0,
                "away_score": 0,
                "home_penalty": None,
                "away_penalty": None,
                "winner": None,
                "status": "pending",
                "match_id": None,
            })
        bracket.append({
            "round_number": rnd,
            "round_name": ROUND_NAMES.get(rnd, ""),
            "matches": round_matches,
        })

    tournament.bracket_json = json.dumps(bracket, ensure_ascii=False)
    db.session.commit()

    return success_response({
        "id": tournament.id,
        "name": tournament.name,
        "status": tournament.status,
        "round_name": tournament.round_name,
        "current_round": tournament.current_round,
        "teams": team_ids,
        "bracket": bracket,
        "created_at": tournament.created_at.isoformat() if tournament.created_at else None,
    })


@bp.get("/<int:tournament_id>")
def get_tournament(tournament_id):
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return error_response("锦标赛不存在", status_code=404)

    bracket = json.loads(tournament.bracket_json or "[]")
    teams_ids = json.loads(tournament.teams_json or "[]")
    teams_info = {}
    for tid in teams_ids:
        team = Team.query.filter_by(id=tid).first()
        if team:
            teams_info[tid] = {
                "id": team.id,
                "name_cn": team.name_cn,
                "name_en": team.name_en,
                "flag_emoji": team.flag_emoji,
            }

    return success_response({
        "id": tournament.id,
        "name": tournament.name,
        "status": tournament.status,
        "round_name": tournament.round_name,
        "current_round": tournament.current_round,
        "teams": teams_info,
        "winner": tournament.winner,
        "top_scorer": tournament.top_scorer,
        "mvp": tournament.mvp,
        "bracket": bracket,
        "created_at": tournament.created_at.isoformat() if tournament.created_at else None,
    })


@bp.post("/<int:tournament_id>/simulate_round")
def simulate_round(tournament_id):
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return error_response("锦标赛不存在", status_code=404)
    if tournament.status == "completed":
        return error_response("锦标赛已结束", status_code=400)

    current_round = tournament.current_round
    if current_round > 4:
        return error_response("所有轮次已结束", status_code=400)

    pending_matches = TournamentMatch.query.filter(
        TournamentMatch.tournament_id == tournament_id,
        TournamentMatch.round_number == current_round,
        TournamentMatch.status == "pending",
        TournamentMatch.team_home_id.isnot(None),
        TournamentMatch.team_away_id.isnot(None),
    ).order_by(TournamentMatch.match_order).all()

    if not pending_matches:
        return error_response(
            f"当前轮次({ROUND_NAMES[current_round]})没有待进行的比赛",
            status_code=400,
        )

    results = []
    winners = []
    for tm in pending_matches:
        match_result = _simulate_tournament_match(tm)
        results.append(match_result)
        winners.append(tm.winner)

    if current_round == 4:
        tournament.status = "completed"
        tournament.winner = winners[0] if winners else None
    else:
        next_round = current_round + 1
        tournament.current_round = next_round
        tournament.round_name = ROUND_NAMES.get(next_round, "")
        next_matches = TournamentMatch.query.filter_by(
            tournament_id=tournament_id, round_number=next_round
        ).order_by(TournamentMatch.match_order).all()
        for i, next_tm in enumerate(next_matches):
            if i * 2 < len(winners):
                next_tm.team_home_id = winners[i * 2] if (i * 2) < len(winners) else None
                next_tm.team_away_id = winners[i * 2 + 1] if (i * 2 + 1) < len(winners) else None

    if tournament.status == "draw":
        tournament.status = "in_progress"

    _update_bracket_json(tournament)
    db.session.commit()

    return success_response({
        "round_number": current_round,
        "round_name": ROUND_NAMES.get(current_round, ""),
        "results": results,
        "winners": winners,
        "next_round": ROUND_NAMES.get(current_round + 1, "") if current_round < 4 else None,
        "tournament_status": tournament.status,
    })


@bp.post("/<int:tournament_id>/simulate_all")
def simulate_all(tournament_id):
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return error_response("锦标赛不存在", status_code=404)
    if tournament.status == "completed":
        return error_response("锦标赛已结束", status_code=400)

    all_rounds = []
    while tournament.current_round <= 4 and tournament.status != "completed":
        current_round = tournament.current_round
        pending_matches = TournamentMatch.query.filter(
            TournamentMatch.tournament_id == tournament_id,
            TournamentMatch.round_number == current_round,
            TournamentMatch.status == "pending",
            TournamentMatch.team_home_id.isnot(None),
            TournamentMatch.team_away_id.isnot(None),
        ).order_by(TournamentMatch.match_order).all()

        if not pending_matches:
            break

        results = []
        winners = []
        for tm in pending_matches:
            match_result = _simulate_tournament_match(tm)
            results.append(match_result)
            winners.append(tm.winner)

        all_rounds.append({
            "round_number": current_round,
            "round_name": ROUND_NAMES.get(current_round, ""),
            "results": results,
            "winners": winners,
        })

        if current_round == 4:
            tournament.status = "completed"
            tournament.winner = winners[0] if winners else None
        else:
            next_round = current_round + 1
            tournament.current_round = next_round
            tournament.round_name = ROUND_NAMES.get(next_round, "")
            next_matches = TournamentMatch.query.filter_by(
                tournament_id=tournament_id, round_number=next_round
            ).order_by(TournamentMatch.match_order).all()
            for i, next_tm in enumerate(next_matches):
                if i * 2 < len(winners):
                    next_tm.team_home_id = winners[i * 2] if (i * 2) < len(winners) else None
                    next_tm.team_away_id = winners[i * 2 + 1] if (i * 2 + 1) < len(winners) else None

        if tournament.status == "draw":
            tournament.status = "in_progress"

    _update_bracket_json(tournament)
    db.session.commit()

    bracket = json.loads(tournament.bracket_json or "[]")
    return success_response({
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "winner": tournament.winner,
        "rounds": all_rounds,
        "bracket": bracket,
    })
