"""
球员养成 + 成就系统 核心逻辑
全部基于内存模拟，无需数据库持久化
"""
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# 成就系统 - 预置成就定义
# ============================================================
ACHIEVEMENT_DEFS = [
    {
        "id": "first_win",
        "name": "首胜！",
        "description": "赢得第一场比赛",
        "icon": "🏆",
        "condition_type": "win_count",
        "condition_value": 1,
    },
    {
        "id": "win_5",
        "name": "五连胜",
        "description": "赢得5场比赛",
        "icon": "🏆",
        "condition_type": "win_count",
        "condition_value": 5,
    },
    {
        "id": "win_10",
        "name": "十胜王",
        "description": "赢得10场比赛",
        "icon": "🏆",
        "condition_type": "win_count",
        "condition_value": 10,
    },
    {
        "id": "hat_trick",
        "name": "帽子戏法",
        "description": "单场比赛一位球员进3球",
        "icon": "🎩",
        "condition_type": "goal_count",
        "condition_value": 3,
    },
    {
        "id": "clean_sheet",
        "name": "零封",
        "description": "不失球赢得比赛",
        "icon": "🧤",
        "condition_type": "clean_sheet",
        "condition_value": 1,
    },
    {
        "id": "comeback",
        "name": "惊天逆转",
        "description": "落后2球后逆转获胜",
        "icon": "🔄",
        "condition_type": "comeback_win",
        "condition_value": 2,
    },
    {
        "id": "underdog",
        "name": "以下克上",
        "description": "低档队伍（tier 3/4）击败高档队伍（tier 1）",
        "icon": "💪",
        "condition_type": "upset_win",
        "condition_value": 1,
    },
    {
        "id": "no_loss_5",
        "name": "不败金身",
        "description": "连续5场比赛不败",
        "icon": "🛡️",
        "condition_type": "no_loss_count",
        "condition_value": 5,
    },
    {
        "id": "goal_fest",
        "name": "进球盛宴",
        "description": "单场比赛一方进5球或以上",
        "icon": "🌮",
        "condition_type": "goal_fest",
        "condition_value": 5,
    },
    {
        "id": "penalty_win",
        "name": "点球决胜",
        "description": "通过点球大战获胜",
        "icon": "⚽",
        "condition_type": "penalty_win",
        "condition_value": 1,
    },
    {
        "id": "one_nil",
        "name": "经济实惠",
        "description": "1-0赢得比赛",
        "icon": "💰",
        "condition_type": "one_nil",
        "condition_value": 1,
    },
]

# ============================================================
# 成就系统 - 运行时状态（内存）
# ============================================================
# 记录已解锁的成就 ID
_unlocked_achievements: set = set()
# 记录每个成就是由哪个 match_id 触发的
_achievement_match_map: dict = {}

# 计数器（用于 win_count, no_loss_count 等条件）
_win_counter: int = 0          # 总胜场
_no_loss_counter: int = 0      # 当前连续不败
_loss_counter: int = 0         # 总负场


def _get_achievement_def(achievement_id: str) -> Optional[dict]:
    """按 ID 查找成就定义"""
    for a in ACHIEVEMENT_DEFS:
        if a["id"] == achievement_id:
            return a
    return None


# ============================================================
# 球员养成 - 运行时状态（内存）
# ============================================================
# player_id -> {"xp": int, "level": int, "boosts": {"shooting": 0, "passing": 0, "defense": 0}}
_player_xp: dict = {}


def get_player_dev_state(player_id: int) -> dict:
    """获取单球员养成状态，不存在则初始化"""
    if player_id not in _player_xp:
        _player_xp[player_id] = {
            "xp": 0,
            "level": 0,
            "boosts": {"shooting": 0, "passing": 0, "defense": 0},
        }
    return _player_xp[player_id]


def _xp_for_next_level(level: int) -> int:
    """升级所需经验：每级 + 50"""
    return (level + 1) * 50


def _get_boost_attr(position: str) -> str:
    """根据位置决定升级加什么属性"""
    # 门将 -> defense
    GK_POS = {"GK"}
    # 前锋 -> shooting
    FWD_POS = {"ST", "LW", "RW", "CF", "LF", "RF"}
    # 中场 -> passing
    MID_POS = {"CAM", "CM", "CDM", "LM", "RM"}
    # 后卫 -> defense
    DEF_POS = {"CB", "LB", "RB", "LWB", "RWB", "SW"}
    # 门将
    if position.upper() in GK_POS:
        return "defense"
    # 前锋
    if position.upper() in FWD_POS:
        return "shooting"
    # 中场
    if position.upper() in MID_POS:
        return "passing"
    # 后卫
    if position.upper() in DEF_POS:
        return "defense"
    return "passing"  # 默认


# ============================================================
# 成就检查逻辑
# ============================================================

def check_match_achievements(
    match_id: int,
    home_team_id: str,
    away_team_id: str,
    home_score: int,
    away_score: int,
    home_penalty: Optional[int],
    away_penalty: Optional[int],
    winner: Optional[str],
    match_events: list,
    home_tier: int,
    away_tier: int,
    match_highlights: list,
) -> list[dict]:
    """
    根据一场比赛的结果，检查哪些成就应被解锁。
    返回本次新解锁的成就列表。
    """
    global _win_counter, _no_loss_counter

    newly_unlocked = []
    winner_tier = home_tier if winner == home_team_id else away_tier
    loser_tier = away_tier if winner == home_team_id else home_tier

    # --- 统计事件 ---
    win_count = _win_counter
    no_loss_count = _no_loss_counter

    # 统计本场比赛信息
    is_home_win = winner == home_team_id
    is_away_win = winner == away_team_id
    is_home_draw = not winner

    # 主队进/失球
    home_goals_for = home_score
    away_goals_for = away_score
    max_home_goals = home_score
    max_away_goals = away_score

    # 球员进球统计
    player_goals_home: dict = {}
    player_goals_away: dict = {}
    for evt in match_events:
        if evt.get("type") == "goal":
            p_name = evt.get("player_name", "")
            t_id = evt.get("team_id", "")
            if t_id == home_team_id:
                player_goals_home[p_name] = player_goals_home.get(p_name, 0) + 1
            else:
                player_goals_away[p_name] = player_goals_away.get(p_name, 0) + 1

    # 先更新连续性计数器
    if winner:
        _win_counter += 1
        _no_loss_counter += 1
        win_count_result = _win_counter
        no_loss_count_result = _no_loss_counter
    else:
        # 平局也算不败
        _no_loss_counter += 1
        no_loss_count_result = _no_loss_counter
        win_count_result = _win_counter  # 平局不算胜

    # 如果输了（对方赢了），重置不败计数
    if not winner:
        pass  # 平局，不败继续
    elif winner != home_team_id and winner != away_team_id:
        pass  # 双方都没赢（平局），不败继续
    else:
        # 产生了胜者，但只有败方reset
        pass

    # --- 逐项检查成就 ---

    # 1. first_win - 赢得第1场比赛
    if "first_win" not in _unlocked_achievements:
        if winner and _win_counter >= 1:
            _unlocked_achievements.add("first_win")
            _achievement_match_map["first_win"] = match_id
            newly_unlocked.append(_get_achievement_def("first_win"))

    # 2. win_5 - 赢5场
    if "win_5" not in _unlocked_achievements:
        if winner and _win_counter >= 5:
            _unlocked_achievements.add("win_5")
            _achievement_match_map["win_5"] = match_id
            newly_unlocked.append(_get_achievement_def("win_5"))

    # 3. win_10 - 赢10场
    if "win_10" not in _unlocked_achievements:
        if winner and _win_counter >= 10:
            _unlocked_achievements.add("win_10")
            _achievement_match_map["win_10"] = match_id
            newly_unlocked.append(_get_achievement_def("win_10"))

    # 4. hat_trick - 单场进3球
    if "hat_trick" not in _unlocked_achievements:
        has_hat_trick = any(
            g >= 3 for g in list(player_goals_home.values()) + list(player_goals_away.values())
        )
        if has_hat_trick:
            _unlocked_achievements.add("hat_trick")
            _achievement_match_map["hat_trick"] = match_id
            newly_unlocked.append(_get_achievement_def("hat_trick"))

    # 5. clean_sheet - 不失球赢球
    if "clean_sheet" not in _unlocked_achievements:
        clean_home = is_home_win and away_score == 0
        clean_away = is_away_win and home_score == 0
        if clean_home or clean_away:
            _unlocked_achievements.add("clean_sheet")
            _achievement_match_map["clean_sheet"] = match_id
            newly_unlocked.append(_get_achievement_def("clean_sheet"))

    # 6. comeback - 落后2球逆转
    if "comeback" not in _unlocked_achievements:
        # 通过highlights判断 - 但match_events主要记录最终比分
        # 简单判断：查看events中是否有落后的时间线
        # 这里简化判断：如果有比分变化，看是否曾落后2球
        goal_events = [e for e in match_events if e.get("type") == "goal"]
        temp_h = 0
        temp_a = 0
        max_lead = 0
        for evt in goal_events:
            t_id = evt.get("team_id", "")
            if t_id == home_team_id:
                temp_h += 1
            else:
                temp_a += 1
            if t_id == winner:
                deficit = abs(temp_h - temp_a)
                if deficit > max_lead:
                    max_lead = deficit
        # 如果胜方一度落后2球+
        if max_lead >= 2 and winner:
            _unlocked_achievements.add("comeback")
            _achievement_match_map["comeback"] = match_id
            newly_unlocked.append(_get_achievement_def("comeback"))

    # 7. underdog - 低档队伍赢高档队伍
    if "underdog" not in _unlocked_achievements:
        if winner:
            # 低档(tier 3/4) 赢 高档(tier 1)
            if (winner_tier in (3, 4)) and loser_tier == 1:
                _unlocked_achievements.add("underdog")
                _achievement_match_map["underdog"] = match_id
                newly_unlocked.append(_get_achievement_def("underdog"))

    # 8. no_loss_5 - 连续5场不败
    if "no_loss_5" not in _unlocked_achievements:
        if _no_loss_counter >= 5:
            _unlocked_achievements.add("no_loss_5")
            _achievement_match_map["no_loss_5"] = match_id
            newly_unlocked.append(_get_achievement_def("no_loss_5"))

    # 9. goal_fest - 单场进5球
    if "goal_fest" not in _unlocked_achievements:
        if home_score >= 5 or away_score >= 5:
            _unlocked_achievements.add("goal_fest")
            _achievement_match_map["goal_fest"] = match_id
            newly_unlocked.append(_get_achievement_def("goal_fest"))

    # 10. penalty_win - 点球赢球
    if "penalty_win" not in _unlocked_achievements:
        if home_penalty is not None and away_penalty is not None:
            # 有点球数据说明经过点球
            _unlocked_achievements.add("penalty_win")
            _achievement_match_map["penalty_win"] = match_id
            newly_unlocked.append(_get_achievement_def("penalty_win"))

    # 11. one_nil - 1-0赢球
    if "one_nil" not in _unlocked_achievements:
        if (is_home_win and home_score == 1 and away_score == 0) or \
           (is_away_win and away_score == 1 and home_score == 0):
            _unlocked_achievements.add("one_nil")
            _achievement_match_map["one_nil"] = match_id
            newly_unlocked.append(_get_achievement_def("one_nil"))

    return newly_unlocked


# ============================================================
# 球员经验分配逻辑
# ============================================================

def apply_match_xp(
    winner: Optional[str],
    winners_player_ids: list[int],
    winners_player_positions: dict[int, str],
) -> list[dict]:
    """
    赢球后，随机2-3名球员获得经验。
    winners_player_ids: 赢家球队的球员ID列表
    winners_player_positions: {player_id: position_str}

    返回本次获得的经验记录列表。
    """
    if not winner or not winners_player_ids:
        return []

    # 随机选择2-3名球员
    count = min(random.randint(2, 3), len(winners_player_ids))
    lucky_players = random.sample(winners_player_ids, count)

    gains = []
    for pid in lucky_players:
        state = get_player_dev_state(pid)
        xp_gain = random.randint(10, 25)
        state["xp"] += xp_gain

        # 检查升级
        leveled_up = False
        while state["xp"] >= _xp_for_next_level(state["level"]):
            state["xp"] -= _xp_for_next_level(state["level"])
            state["level"] += 1
            # 决定加点属性
            pos = winners_player_positions.get(pid, "CM")
            attr = _get_boost_attr(pos)
            state["boosts"][attr] = state["boosts"].get(attr, 0) + 1
            leveled_up = True

        gains.append({
            "player_id": pid,
            "xp_gain": xp_gain,
            "total_xp": state["xp"],
            "level": state["level"],
            "boosts": dict(state["boosts"]),
            "leveled_up": leveled_up,
        })

    return gains


# ============================================================
# 查询接口
# ============================================================

def get_all_achievements() -> list[dict]:
    """获取所有成就定义及解锁状态"""
    result = []
    for a in ACHIEVEMENT_DEFS:
        aid = a["id"]
        unlocked = aid in _unlocked_achievements
        entry = dict(a)
        entry["unlocked"] = unlocked
        entry["unlocked_match_id"] = _achievement_match_map.get(aid)
        result.append(entry)
    return result


def get_unlocked_achievements() -> list[dict]:
    """获取已解锁成就"""
    result = []
    for a in ACHIEVEMENT_DEFS:
        if a["id"] in _unlocked_achievements:
            entry = dict(a)
            entry["unlocked_match_id"] = _achievement_match_map.get(a["id"])
            result.append(entry)
    return result


def get_all_player_dev_state(player_ids: list[int] = None) -> dict:
    """
    获取所有球员养成状态
    如果 player_ids 提供则过滤
    """
    if player_ids:
        return {str(pid): get_player_dev_state(pid) for pid in player_ids}
    return {str(k): v for k, v in _player_xp.items()}


def reset_all_state():
    """重置所有内存状态（用于测试）"""
    global _unlocked_achievements, _achievement_match_map
    global _win_counter, _no_loss_counter, _loss_counter, _player_xp
    _unlocked_achievements = set()
    _achievement_match_map = {}
    _win_counter = 0
    _no_loss_counter = 0
    _loss_counter = 0
    _player_xp = {}
