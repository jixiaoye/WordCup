"""对战/房间 API"""
import json
import random
import string
from datetime import datetime, timezone

from flask import Blueprint, request

from wxcloudrun import db
from wxcloudrun.models import Team, Player, GameRoom, Match, MatchEvent, MatchTurn
from wxcloudrun.response import success_response, error_response

bp = Blueprint("game", __name__, url_prefix="/api/v1/game")


def _generate_room_code(length=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _resolve_turn_offline(attack_action, defense_action, attack_team_id, defense_team_id, home_team_id):
    BEATS = {
        "shoot": ["press"],
        "pass": ["dribble"],
        "dribble": ["retreat"],
        "retreat": ["shoot"],
        "press": ["pass"],
    }

    is_attacker_win = attack_action in BEATS and defense_action in BEATS.get(attack_action, [])
    is_defense_win = defense_action in BEATS and attack_action in BEATS.get(defense_action, [])

    if is_attacker_win:
        if random.random() < 0.35:
            return {"type": "goal", "team_id": attack_team_id, "detail": "进攻成功，破门得分！"}
        return {"type": "near_miss", "team_id": attack_team_id, "detail": "进攻成功，但射门被化解"}
    elif is_defense_win:
        return {"type": "defense_win", "team_id": defense_team_id, "detail": "防守成功，夺回球权！"}
    else:
        r = random.random()
        if r < 0.15:
            return {"type": "goal", "team_id": attack_team_id, "detail": "混战中破门得分！"}
        elif r < 0.40:
            return {"type": "near_miss", "team_id": attack_team_id, "detail": "射门被挡出"}
        return {"type": "neutral", "detail": "球被解围，进攻结束"}


@bp.post("/rooms")
def create_room():
    body = request.get_json(silent=True) or {}
    host_player = body.get("host_player", "")
    host_team_id = body.get("host_team_id", "").upper()

    if not Team.query.filter_by(id=host_team_id).first():
        return error_response(f"球队 {host_team_id} 不存在", status_code=404)

    code = None
    for _ in range(10):
        candidate = _generate_room_code()
        if not GameRoom.query.filter_by(code=candidate).first():
            code = candidate
            break
    if not code:
        return error_response("无法生成房间码，请重试", status_code=500)

    room = GameRoom(
        code=code,
        host_player=host_player,
        host_team_id=host_team_id,
        status="waiting",
    )
    db.session.add(room)
    db.session.commit()

    return success_response({
        "id": room.id,
        "code": room.code,
        "host_player": room.host_player,
        "host_team_id": room.host_team_id,
        "status": room.status,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    })


@bp.post("/rooms/<code>/join")
def join_room(code):
    body = request.get_json(silent=True) or {}
    code = code.upper()
    guest_player = body.get("guest_player", "")
    guest_team_id = body.get("guest_team_id", "").upper()

    room = GameRoom.query.filter_by(code=code).first()
    if not room:
        return error_response("房间不存在", status_code=404)
    if room.status != "waiting":
        return error_response("房间已不可加入", status_code=400)
    if not Team.query.filter_by(id=guest_team_id).first():
        return error_response(f"球队 {guest_team_id} 不存在", status_code=404)
    if guest_team_id == room.host_team_id:
        return error_response("客队不能选择与房主相同的球队", status_code=400)

    room.guest_player = guest_player
    room.guest_team_id = guest_team_id
    room.status = "ready"
    db.session.commit()

    return success_response({
        "id": room.id,
        "code": room.code,
        "host_player": room.host_player,
        "host_team_id": room.host_team_id,
        "guest_player": room.guest_player,
        "guest_team_id": room.guest_team_id,
        "status": room.status,
    })


@bp.get("/rooms/<code>")
def get_room(code):
    code = code.upper()
    room = GameRoom.query.filter_by(code=code).first()
    if not room:
        return error_response("房间不存在", status_code=404)

    match_info = None
    if room.current_match_id:
        match_record = Match.query.get(room.current_match_id)
        if match_record:
            match_info = {
                "id": match_record.id,
                "home_score": match_record.home_score,
                "away_score": match_record.away_score,
                "home_penalty": match_record.home_penalty,
                "away_penalty": match_record.away_penalty,
                "winner": match_record.winner,
                "status": match_record.status,
            }

    return success_response({
        "id": room.id,
        "code": room.code,
        "host_player": room.host_player,
        "host_team_id": room.host_team_id,
        "guest_player": room.guest_player,
        "guest_team_id": room.guest_team_id,
        "status": room.status,
        "current_match": match_info,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    })


@bp.post("/rooms/<code>/start")
def start_match(code):
    code = code.upper()
    room = GameRoom.query.filter_by(code=code).first()
    if not room:
        return error_response("房间不存在", status_code=404)
    if room.status not in ("ready", "live"):
        return error_response("房间状态不满足开始条件", status_code=400)

    home_team = Team.query.filter_by(id=room.host_team_id).first()
    away_team = Team.query.filter_by(id=room.guest_team_id).first()
    if not home_team or not away_team:
        return error_response("球队数据错误", status_code=500)

    room.status = "live"

    if room.current_match_id:
        existing = Match.query.get(room.current_match_id)
        if existing and existing.status == "live":
            return success_response({"match_id": existing.id, "status": "live"})

    attacking = "home" if random.random() < 0.5 else "away"
    match_record = Match(
        room_id=room.id,
        team_home_id=room.host_team_id,
        team_away_id=room.guest_team_id,
        home_score=0,
        away_score=0,
        status="live",
        current_turn=1,
        turn_phase="waiting_attack",
        attacking_team=attacking,
        home_player=room.host_player,
        away_player=room.guest_player,
    )
    db.session.add(match_record)
    db.session.flush()

    turn = MatchTurn(
        match_id=match_record.id,
        turn_number=1,
        attacking_team=attacking,
        defensing_team="away" if attacking == "home" else "home",
        zone=random.choice(["left", "center", "right"]),
        status="waiting_attack",
    )
    db.session.add(turn)
    room.current_match_id = match_record.id
    db.session.commit()

    return success_response({
        "match_id": match_record.id,
        "status": "live",
        "current_turn": 1,
        "turn_phase": "waiting_attack",
        "attacking_team": attacking,
        "home_team_id": room.host_team_id,
        "away_team_id": room.guest_team_id,
        "home_player": room.host_player,
        "away_player": room.guest_player,
    })


@bp.get("/matches/<int:match_id>/state")
def get_match_state(match_id):
    match_record = Match.query.get(match_id)
    if not match_record:
        return error_response("比赛不存在", status_code=404)

    current_turn = None
    if match_record.status == "live":
        turn = MatchTurn.query.filter_by(
            match_id=match_id, turn_number=match_record.current_turn
        ).first()
        if turn:
            current_turn = {
                "turn_number": turn.turn_number,
                "attacking_team": turn.attacking_team,
                "defensing_team": turn.defensing_team,
                "zone": turn.zone,
                "status": turn.status,
                "attack_action": turn.attack_action,
                "defense_action": turn.defense_action,
                "result": json.loads(turn.result) if turn.result else None,
            }

    events = MatchEvent.query.filter_by(match_id=match_id).order_by(
        MatchEvent.minute, MatchEvent.id
    ).all()

    home_team = Team.query.filter_by(id=match_record.team_home_id).first()
    away_team = Team.query.filter_by(id=match_record.team_away_id).first()

    return success_response({
        "match_id": match_record.id,
        "status": match_record.status,
        "turn_phase": match_record.turn_phase,
        "current_turn": match_record.current_turn,
        "attacking_team": match_record.attacking_team,
        "home_team_id": match_record.team_home_id,
        "away_team_id": match_record.team_away_id,
        "home_team_name": home_team.name_cn if home_team else "主队",
        "away_team_name": away_team.name_cn if away_team else "客队",
        "home_team_flag": home_team.flag_emoji if home_team else "🏳️",
        "away_team_flag": away_team.flag_emoji if away_team else "🏳️",
        "home_score": match_record.home_score,
        "away_score": match_record.away_score,
        "home_player": match_record.home_player,
        "away_player": match_record.away_player,
        "winner": match_record.winner,
        "current_turn_info": current_turn,
        "events": [
            {
                "id": e.id,
                "minute": e.minute,
                "type": e.type,
                "team_id": e.team_id,
                "player_name": e.player_name,
                "detail": e.detail,
                "turn_number": e.turn_number,
            }
            for e in events
        ],
    })


@bp.post("/matches/<int:match_id>/action")
def submit_action(match_id):
    match_record = Match.query.get(match_id)
    if not match_record:
        return error_response("比赛不存在", status_code=404)
    if match_record.status != "live":
        return error_response("比赛已结束", status_code=400)

    body = request.get_json(silent=True) or {}
    team_id = body.get("team_id", "")
    action = body.get("action", "")
    if not team_id or not action:
        return error_response("缺少 team_id 或 action", status_code=400)

    valid_actions = {"shoot", "pass", "dribble", "tackle", "press", "retreat"}
    if action not in valid_actions:
        return error_response(f"无效动作: {action}", status_code=400)

    turn = MatchTurn.query.filter_by(
        match_id=match_id, turn_number=match_record.current_turn
    ).first()
    if not turn:
        return error_response("回合不存在", status_code=500)

    is_attacker = (
        (team_id == match_record.team_home_id and turn.attacking_team == "home")
        or (team_id == match_record.team_away_id and turn.attacking_team == "away")
    )

    if is_attacker:
        if turn.status != "waiting_attack":
            return error_response("当前不是进攻阶段", status_code=400)
        turn.attack_action = action
        turn.status = "waiting_defense"
        match_record.turn_phase = "waiting_defense"
        db.session.commit()
        return success_response({"status": "waiting_defense", "message": "进攻动作已提交，等待防守方"})

    if turn.status != "waiting_defense":
        return error_response("当前不是防守阶段", status_code=400)
    if not turn.attack_action:
        return error_response("进攻方尚未提交动作", status_code=400)

    turn.defense_action = action
    turn.status = "completed"

    atk_team_id = (
        match_record.team_home_id if turn.attacking_team == "home"
        else match_record.team_away_id
    )
    def_team_id = (
        match_record.team_away_id if turn.attacking_team == "home"
        else match_record.team_home_id
    )
    result = _resolve_turn_offline(
        turn.attack_action, turn.defense_action,
        atk_team_id, def_team_id,
        match_record.team_home_id,
    )
    turn.result = json.dumps(result, ensure_ascii=False)

    minute = match_record.current_turn * 3
    db.session.add(MatchEvent(
        match_id=match_id,
        minute=minute,
        type=result["type"],
        team_id=result.get("team_id", ""),
        detail=result.get("detail", ""),
        turn_number=match_record.current_turn,
    ))

    if result["type"] == "goal":
        if team_id == match_record.team_home_id:
            match_record.home_score += 1
        else:
            match_record.away_score += 1

    if match_record.current_turn >= 30:
        match_record.turn_phase = "finished"
        match_record.status = "finished"
        if match_record.home_score > match_record.away_score:
            match_record.winner = match_record.team_home_id
        elif match_record.away_score > match_record.home_score:
            match_record.winner = match_record.team_away_id
        match_record.finished_at = datetime.now(timezone.utc)
        room = GameRoom.query.get(match_record.room_id)
        if room:
            room.status = "finished"
        db.session.commit()
        return success_response({
            "status": "finished",
            "result": result,
            "home_score": match_record.home_score,
            "away_score": match_record.away_score,
            "winner": match_record.winner,
            "match_id": match_id,
        })

    next_turn_num = match_record.current_turn + 1
    next_attacker = "away" if turn.attacking_team == "home" else "home"
    db.session.add(MatchTurn(
        match_id=match_id,
        turn_number=next_turn_num,
        attacking_team=next_attacker,
        defensing_team="home" if next_attacker == "away" else "away",
        zone=random.choice(["left", "center", "right"]),
        status="waiting_attack",
    ))
    match_record.current_turn = next_turn_num
    match_record.attacking_team = next_attacker
    match_record.turn_phase = "waiting_attack"
    db.session.commit()

    return success_response({
        "status": "result",
        "result": result,
        "next_turn": next_turn_num,
        "next_attacker": next_attacker,
        "home_score": match_record.home_score,
        "away_score": match_record.away_score,
        "match_id": match_id,
    })


@bp.get("/rooms")
def list_rooms():
    status = request.args.get("status", "waiting")
    rooms = GameRoom.query.filter_by(status=status).order_by(
        GameRoom.created_at.desc()
    ).limit(50).all()

    return success_response([
        {
            "id": r.id,
            "code": r.code,
            "host_player": r.host_player,
            "host_team_id": r.host_team_id,
            "guest_player": r.guest_player,
            "guest_team_id": r.guest_team_id,
            "status": r.status,
            "current_match_id": r.current_match_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rooms
    ])
