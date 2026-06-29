"""
世界杯比赛模拟引擎
"""
import math
import random
from typing import Any, Optional


# 位置分组
FORWARD_POSITIONS = {"ST", "LW", "RW", "CF", "LF", "RF"}
MIDFIELDER_POSITIONS = {"CAM", "CM", "CDM", "LM", "RM"}
DEFENDER_POSITIONS = {"CB", "LB", "RB", "LWB", "RWB", "SW"}
GOALKEEPER_POSITIONS = {"GK"}

# ========== 阵型加成系统 ==========
FORMATION_BONUSES = {
    "4-4-2":   {"attack": 0.00, "defense": 0.00, "midfield": 0.00},   # 均衡，无加成
    "4-3-3":   {"attack": 0.10, "defense": -0.05, "midfield": 0.00},  # 攻击+10%，防守-5%
    "3-5-2":   {"attack": 0.00, "defense": -0.08, "midfield": 0.10},  # 中场+10%，防守-8%
    "5-3-2":   {"attack": -0.08, "defense": 0.10, "midfield": 0.00},  # 防守+10%，攻击-8%
    "4-2-3-1": {"attack": 0.03, "defense": 0.05, "midfield": 0.00},   # 防守+5%，攻击+3%
}

# ========== 天气系统 ==========
WEATHER_EFFECTS = {
    "sunny":  {"shooting_mod": 0.00, "speed_mod": 0.00, "foul_mod": 0.00, "long_pass_mod": 0.00},
    "rainy":  {"shooting_mod": -0.05, "speed_mod": 0.00, "foul_mod": 0.10, "long_pass_mod": 0.00},
    "snowy":  {"shooting_mod": -0.10, "speed_mod": -0.10, "foul_mod": 0.00, "long_pass_mod": 0.00},
    "windy":  {"shooting_mod": -0.08, "speed_mod": 0.00, "foul_mod": 0.00, "long_pass_mod": 0.05},
}

# ========== 其他常量 ==========
SUBSTITUTIONS_PER_TEAM = 3  # 每队换人次数

# 比赛事件描述库
GOAL_DETAILS = [
    "禁区外远射破门",
    "禁区内劲射得分",
    "头球攻门得手",
    "门前补射入网",
    "单刀赴会破门",
    "任意球直接得分",
    "角球配合头球破门",
    "倒钩射门得分",
    "凌空抽射破门",
    "小角度推射入网",
    "点球命中",
    "门前抢点得分",
    "远距离吊射破门",
    "快速反击推射得分",
    "边路传中头球破门",
]

YELLOW_CARD_DETAILS = [
    "背后铲球犯规",
    "战术犯规阻止反击",
    "手球犯规",
    "危险动作",
    "拖延比赛时间",
    "争执判罚",
    "拉人犯规",
    "铲球动作过大",
]

RED_CARD_DETAILS = [
    "严重铲球犯规",
    "暴力行为",
    "恶劣犯规",
    "两黄变一红",
    "故意手球破坏必进球",
]

SUBSTITUTION_DETAILS = [
    "战术换人",
    "体能下降被换下",
    "受伤无法坚持",
    "加强进攻",
    "加强防守",
]

# 精彩瞬间叙述库
GOAL_NARRATIVES = {
    "远射破门": [
        "{player} 在禁区弧顶接到{assist}的传球",
        "调整一步，抬头观察球门",
        "起脚大力抽射！！！",
        "⚽ 球像炮弹一样飞入球网！",
        "比分变为 {score}！{player} 疯狂庆祝！",
    ],
    "劲射得分": [
        "{player} 在禁区内接到{assist}的精妙传球",
        "顺势转身，摆脱防守球员",
        "一脚劲射！角度刁钻！",
        "⚽ 球应声入网！",
        "比分改写为 {score}！全队拥抱庆祝！",
    ],
    "头球攻门": [
        "{assist} 在边路起脚传中！",
        "{player} 在禁区内高高跃起！",
        "一记有力的头球！！",
        "⚽ 头球破门！门将毫无办法！",
        "比分变为 {score}！{player} 落地怒吼！",
    ],
    "补射入网": [
        "{player} 在禁区内寻找机会",
        "第一脚射门被门将扑出！",
        "{player} 快速跟上补射！！",
        "⚽ 补射命中！",
        "比分改写为 {score}！{player} 兴奋地跑向角旗区！",
    ],
    "单刀赴会": [
        "{assist} 送出一记精妙直塞！",
        "{player} 反越位成功，形成单刀！",
        "面对出击的门将，冷静推射远角！！",
        "⚽ 球进了！单刀赴会！",
        "比分变为 {score}！经典的快速反击配合！",
    ],
    "任意球直接": [
        "{player} 站在球前，深吸一口气",
        "助跑...",
        "一脚弧线球绕过人墙！！！",
        "⚽ 球划出美妙的弧线直挂死角！",
        "比分 {score}！世界波！",
    ],
    "点球命中": [
        "裁判指向十二码点！点球！",
        "{player} 站在点球点前，全场屏息",
        "助跑... 射门！",
        "⚽ 点球命中！门将判断错了方向！",
        "比分变为 {score}！{player} 握拳庆祝！",
    ],
    "倒钩射门": [
        "传中球飞到禁区，{player} 背对球门",
        "腾空而起！",
        "一记精彩的倒钩射门！！！",
        "⚽ 世界级进球！全场起立欢呼！",
        "比分 {score}！这球必将是赛季最佳候选！",
    ],
    "凌空抽射": [
        "球从空中飞来，{player} 不等球落地",
        "侧身凌空抽射！",
    "一脚势大力沉的凌空斩！！！",
        "⚽ 球像流星一样飞入球网！",
        "比分改写为 {score}！技惊四座！",
    ],
    "小角度推射": [
        "{player} 在角度极小的情况下拿球",
        "看似没有射门角度...",
        "突然一脚推射远角！！！",
        "⚽ 球从门将指尖划过滚入网窝！",
        "比分 {score}！难以置信的角度！",
    ],
    "抢点得分": [
        "{player} 敏锐地出现在最危险的位置",
        "{assist} 的传球穿越了整条防线",
        "{player} 伸脚一捅！！",
        "⚽ 门前抢点得分！",
        "比分变为 {score}！真正的机会主义者！",
    ],
    "吊射破门": [
        "{player} 观察到门将站位靠前",
        "轻轻一挑...",
        "一记精准的吊射！！！",
        "⚽ 球越过门将头顶落入球网！",
        "比分 {score}！天才般的灵感！",
    ],
    "反击推射": [
        "{player} 接到{assist}的传球发动快速反击",
        "以速度摆脱防守球员！",
        "面对门将冷静推射！！",
        "⚽ 快速反击得手！",
        "比分改写为 {score}！闪电般的反击！",
    ],
    "角球配合": [
        "{assist} 开出角球！",
        "球划出一道弧线飞向禁区！",
        "{player} 在前点甩头攻门！！！",
        "⚽ 头球破门！角球战术成功！",
        "比分 {score}！定位球再显神威！",
    ],
    "传中头球": [
        "{assist} 在边路突破后精准传中",
        "{player} 在中路包抄到位",
    "迎球一记有力的头球！！！",
        "⚽ 头球破门！经典的下底传中战术！",
        "比分变为 {score}！完美的配合！",
    ],
}

GOAL_CELEBRATIONS = [
    "双手指天，感谢上天赐予的进球",
    "滑跪庆祝，激情四射！",
    "跑向角旗区，跳起标志性庆祝动作",
    "张开双臂，迎接队友的拥抱",
    "亲吻队徽，向球迷致意",
    "原地空翻，引爆全场！",
    "双手放在耳边，聆听球迷的欢呼声",
    "做出心形手势，献给看台上的家人",
]

SAVE_NARRATIVES = [
    [
        "对方前锋获得绝佳机会！",
        "一脚势大力沉的射门！",
        "{goalkeeper} 飞身扑出！精彩扑救！",
    ],
    [
        "对方打出精妙配合，形成单刀！",
        "前锋起脚射门！",
        "{goalkeeper} 迅速出击，用腿挡出！世界级扑救！",
    ],
    [
        "任意球直接攻门！",
        "球绕过人墙飞向球门死角！",
        "{goalkeeper} 飞身鱼跃，指尖将球托出横梁！",
    ],
    [
        "近距离头球攻门！",
        "力量极大，直奔球门左下角！",
        "{goalkeeper} 反应神速，倒地扑出！",
    ],
    [
        "禁区外突施冷箭！",
        "球带着强烈的旋转飞向球门",
        "{goalkeeper} 做出关键扑救，力保城门不失！",
    ],
]

NEAR_MISS_NARRATIVES = [
    [
        "{player} 起脚射门！",
        "球稍稍偏出立柱！",
    ],
    [
        "{player} 大力抽射！",
        "球击中横梁弹出！",
    ],
    [
        "{player} 获得绝佳机会，起脚打门！",
        "球擦着立柱滚出底线！",
    ],
    [
        "{player} 的射门直奔死角！",
        "门将指尖碰了一下，球击中门柱弹出！",
    ],
]

RED_CARD_NARRATIVES = [
    [
        "{player} 背后铲球，动作危险！",
        "裁判毫不犹豫出示红牌！🟥",
        "{player} 被罚下场，{team} 十人应战！",
    ],
    [
        "{player} 与对方球员发生冲突",
        "有挥肘动作！裁判出示红牌！🟥",
        "{team} 不得不在剩余时间少一人作战！",
    ],
    [
        "{player} 故意手球破坏必进球机会！",
        "裁判直接出示红牌将其罚下！🟥",
        "{team} 陷入人数劣势！",
    ],
    [
        "{player} 飞铲铲倒对方球员",
        "这是一个极其危险的动作！红牌！🟥",
        "{team} 雪上加霜，被罚下一人！",
    ],
]




# ========== 解说话术系统 ==========
COMMENTARY_PHRASES = {
    "goal": [
        "球进了！精彩的进球！",
        "GOALLLLL！球迷们沸腾了！",
        "漂亮的配合！干净利落的进球！",
        "世界波！这脚射门太精彩了！",
        "门前抢点得分！完美的跑位！",
        "远射破门！守门员毫无办法！",
        "点球命中！稳稳罚进！",
        "头球攻门！势大力沉！",
        "单刀赴会！冷静推射破门！",
        "任意球直接得分！圆月弯刀！",
        "补射命中！门将扑球脱手了！",
        "凌空抽射！打出一脚世界波！",
        "倒挂金钩！神仙球！",
        "门前混战！球进了！",
        "快速反击！三传两倒就打穿了防线！",
    ],
    "save": [
        "精彩的扑救！门将立功了！",
        "神级扑救！拒绝了对方的射门！",
        "门将飞身扑出！力保球门不失！",
        "指尖碰了一下！球擦着立柱飞出！",
        "门将做出关键扑救！",
    ],
    "near_miss": [
        "射门偏出！差了一点点！",
        "球擦着立柱飞出底线！好险！",
        "打高了！这球不应该啊！",
        "太可惜了！绝佳机会没能把握住！",
        "门柱拒绝了这次射门！",
        "横梁！运气不在进攻方这边！",
    ],
    "yellow_card": [
        "犯规！裁判出示黄牌警告！",
        "这个铲球太冒失了！黄牌！",
        "战术犯规，吃到一张黄牌！",
        "背后拉扯，黄牌没问题！",
        "抗议判罚！黄牌！",
    ],
    "red_card": [
        "红牌！直接被罚下场！",
        "严重犯规！裁判出示红牌！",
        "两黄变一红！被罚下场了！",
        "这个动作太危险了！红牌符合规则！",
    ],
    "kickoff": [
        "比赛开始！双方球员进入状态！",
        "随着裁判一声哨响，比赛正式打响！",
        "开场哨响！大战一触即发！",
    ],
    "halftime": [
        "上半场比赛结束！暂时休息15分钟！",
        "半场结束！双方球员回到更衣室！",
        "中场哨响！我们稍事休息！",
    ],
    "fulltime": [
        "全场比赛结束！恭喜获胜的球队！",
        "比赛结束！这是一场精彩的对决！",
        "终场哨响！比赛落下帷幕！",
    ],
    "substitution": [
        "换人调整！球队准备改变战术！",
        "替补球员上场！生力军来了！",
        "换人！希望能改变场上局面！",
    ],
    "foul": [
        "犯规了！裁判吹停比赛！",
        "这个动作被判犯规！",
        "中场拼抢犯规！",
    ],
    "corner": [
        "角球！看看这次机会能不能把握住！",
        "获得角球机会！",
    ],
    "freekick": [
        "任意球！射门还是传球？",
        "前场任意球！直接射门的机会！",
    ],
}

def get_commentary(event_type: str) -> str:
    """根据事件类型随机返回一条解说"""
    import random
    phrases = COMMENTARY_PHRASES.get(event_type, [])
    if not phrases:
        return ""
    return random.choice(phrases)


class MatchEngine:
    """比赛模拟引擎"""

    def __init__(self, team_home: dict, team_away: dict, mascot_boosts: dict = None,
                 formation_home: str = "4-4-2", formation_away: str = "4-4-2",
                 weather: str = "sunny"):
        """
        team_home/team_away 格式:
        {
            "team_id": "BRA",
            "name": "Brazil",
            "players": [
                {"id": 1, "name": "Neymar", "position": "LW",
                 "pace": 90, "shooting": 85, "passing": 82,
                 "defense": 30, "stamina": 78, "physical": 65},
                ...
            ]
        }

        mascot_boosts 格式:
        {
            "BRA": {"attack": 3, "speed": 2},
            "FRA": {"defense": 2, "spirit": 1},
        }
        萌宠加成临时应用在比赛模拟中，不修改数据库。

        formation_home/formation_away: 阵型，"4-4-2"/"4-3-3"/"3-5-2"/"5-3-2"/"4-2-3-1"

        weather: 天气，"sunny"/"rainy"/"snowy"/"windy"
        """
        self.home = team_home
        self.away = team_away
        self.mascot_boosts = mascot_boosts or {}

        # 阵型
        self.formation_home = formation_home if formation_home in FORMATION_BONUSES else "4-4-2"
        self.formation_away = formation_away if formation_away in FORMATION_BONUSES else "4-4-2"

        # 天气
        self.weather = weather if weather in WEATHER_EFFECTS else "sunny"

        # 整理位置分组
        self._categorize_players()

        # 应用萌宠加成
        self._apply_mascot_boosts()

        # 初始球员场上状态 (first 11 人首发，rest 是替补)
        self._setup_lineups()

        # 比赛状态
        self.home_score = 0
        self.away_score = 0
        self.home_penalty = None
        self.away_penalty = None
        self.events = []
        self.minute = 0
        self.duration = "regular"  # regular / extra / penalty
        self.yellow_cards = {}  # player_id -> count (跨队)

        # 精彩瞬间记录
        self._highlights = []

        # 体力衰减跟踪
        self._stamina = {}

    def _categorize_players(self):
        """将球员按位置分组"""
        for side, team_key in [("home", "home"), ("away", "away")]:
            team = getattr(self, team_key)
            team["_forwards"] = [p for p in team["players"] if p.get("position", "") in FORWARD_POSITIONS]
            team["_midfielders"] = [p for p in team["players"] if p.get("position", "") in MIDFIELDER_POSITIONS]
            team["_defenders"] = [p for p in team["players"] if p.get("position", "") in DEFENDER_POSITIONS]
            team["_goalkeepers"] = [p for p in team["players"] if p.get("position", "") in GOALKEEPER_POSITIONS]

    def _setup_lineups(self):
        """设置首发阵容和替补名单"""
        for side, team_key in [("home", "home"), ("away", "away")]:
            team = getattr(self, team_key)
            players = team["players"]

            # 按位置分组排序: GK优先，然后DEF，MID，FWD
            pos_order = {"GK": 0, "CB": 1, "LB": 2, "RB": 2, "LWB": 2, "RWB": 2, "SW": 1,
                         "CDM": 3, "CM": 3, "CAM": 3, "LM": 3, "RM": 3,
                         "LW": 4, "RW": 4, "ST": 4, "CF": 4, "LF": 4, "RF": 4, "SS": 4}

            def sort_key(p):
                return (pos_order.get(p.get("position", ""), 99), -(p.get("overall", 0) or p.get("shooting", 50) + p.get("passing", 50)))

            sorted_players = sorted(players, key=sort_key)

            # 标记首发和替补
            for i, p in enumerate(sorted_players):
                p["_on_field"] = i < 11  # 前11人首发
                p["_is_substitute"] = i >= len(sorted_players) - 3  # 后3人是替补

            team["_sorted_players"] = sorted_players
            team["_substitutions_left"] = SUBSTITUTIONS_PER_TEAM

    def _apply_formation_bonus(self, team: dict) -> dict:
        """计算阵型加成因子"""
        team_id = team["team_id"]
        formation = self.formation_home if team_id == self.home["team_id"] else self.formation_away
        return FORMATION_BONUSES.get(formation, FORMATION_BONUSES["4-4-2"])

    def _get_weather_mods(self) -> dict:
        """获取天气影响"""
        return WEATHER_EFFECTS.get(self.weather, WEATHER_EFFECTS["sunny"])

    def _apply_mascot_boosts(self):
        """将萌宠加成临时应用到球员能力值上"""
        if not self.mascot_boosts:
            return

        for team in [self.home, self.away]:
            team_id = team["team_id"]
            boosts = self.mascot_boosts.get(team_id)
            if not boosts:
                continue

            attack_boost = boosts.get("attack", 0) / 2.0
            defense_boost = boosts.get("defense", 0) / 2.0
            speed_boost = boosts.get("speed", 0) / 2.0
            spirit_boost = boosts.get("spirit", 0) / 2.0

            for player in team["players"]:
                pos = player.get("position", "")

                # 速度加成 → 所有球员的 pace
                if speed_boost:
                    player["pace"] = player.get("pace", 50) + speed_boost

                # 精神加成 → 所有球员的 stamina
                if spirit_boost:
                    player["stamina"] = player.get("stamina", 50) + spirit_boost

                # 攻击加成 → 前锋（LW/RW/ST/CF）的 shooting
                if attack_boost and pos in FORWARD_POSITIONS:
                    player["shooting"] = player.get("shooting", 50) + attack_boost

                # 防御加成 → 后卫（CB/LB/RB/CDM）的 defense
                if defense_boost and pos in DEFENDER_POSITIONS:
                    player["defense"] = player.get("defense", 50) + defense_boost

    def _calc_attack_strength(self, team: dict) -> float:
        """计算球队攻击力（含阵型和天气加成）"""
        forwards = team.get("_forwards", [])
        midfielders = team.get("_midfielders", [])

        # 只计算在场上(on_field)的球员
        on_field_f = [p for p in forwards if p.get("_on_field", True)]
        on_field_m = [p for p in midfielders if p.get("_on_field", True)]

        f_strength = sum(
            (p.get("shooting", 50) * 0.5 + p.get("pace", 50) * 0.25 + p.get("passing", 50) * 0.25) * (p.get("stamina", 50) / 100.0)
            for p in on_field_f
        ) if on_field_f else 0

        m_strength = sum(
            (p.get("passing", 50) * 0.4 + p.get("shooting", 50) * 0.3 + p.get("pace", 50) * 0.3) * (p.get("stamina", 50) / 100.0)
            for p in on_field_m
        ) if on_field_m else 0

        strength = f_strength * 1.2 + m_strength * 0.6

        # 阵型加成
        bonus = self._apply_formation_bonus(team)
        atk_mod = bonus.get("attack", 0)
        mid_mod = bonus.get("midfield", 0)
        strength *= (1 + atk_mod + mid_mod * 0.5)  # midfield bonus also slightly helps attack

        # 天气速度影响
        weather_mods = self._get_weather_mods()
        speed_mod = weather_mods.get("speed_mod", 0)
        if speed_mod:
            strength *= (1 + speed_mod)

        return strength

    def _calc_defense_strength(self, team: dict) -> float:
        """计算球队防守力（含阵型加成）"""
        defenders = team.get("_defenders", [])
        goalkeepers = team.get("_goalkeepers", [])

        # 只计算在场上(on_field)的球员
        on_field_d = [p for p in defenders if p.get("_on_field", True)]
        on_field_g = [p for p in goalkeepers if p.get("_on_field", True)]

        d_strength = sum(
            (p.get("defense", 50) * 0.6 + p.get("physical", 50) * 0.2 + p.get("pace", 50) * 0.2) * (p.get("stamina", 50) / 100.0)
            for p in on_field_d
        ) if on_field_d else 0

        g_strength = sum(
            (p.get("defense", 50) * 0.6 + p.get("physical", 50) * 0.4)
            for p in on_field_g
        ) if on_field_g else 0

        strength = d_strength * 0.7 + g_strength * 1.5

        # 阵型加成
        bonus = self._apply_formation_bonus(team)
        def_mod = bonus.get("defense", 0)
        mid_mod = bonus.get("midfield", 0)
        strength *= (1 + def_mod + mid_mod * 0.3)  # midfield bonus slightly helps defense too

        return strength

    def _pick_on_field_player(self, team: dict, position_bias: list = None) -> dict:
        """从一个在场上场球员中选一个"""
        candidates = [p for p in team["players"] if p.get("_on_field", True)]
        if position_bias:
            biased = [p for p in candidates if p.get("position", "") in position_bias]
            if biased and random.random() < 0.6:
                return random.choice(biased)
        if candidates:
            return random.choice(candidates)
        return random.choice(team["players"])

    def _pick_scorer(self, team: dict) -> dict:
        """选一个进球球员（前锋优先，仅在场上球员中选）"""
        on_field_f = [p for p in team.get("_forwards", []) if p.get("_on_field", True)]
        on_field_m = [p for p in team.get("_midfielders", []) if p.get("_on_field", True)]
        on_field_d = [p for p in team.get("_defenders", []) if p.get("_on_field", True)]

        candidates = []
        # 前锋 60%
        for p in on_field_f:
            candidates.append((p, 60))
        # 中场 30%
        for p in on_field_m:
            candidates.append((p, 30))
        # 后卫 9%
        for p in on_field_d:
            candidates.append((p, 9))
        # 门将 1%
        for p in team.get("_goalkeepers", []):
            if p.get("_on_field", True):
                candidates.append((p, 1))

        if not candidates:
            on_field_all = [p for p in team["players"] if p.get("_on_field", True)]
            if on_field_all:
                return random.choice(on_field_all)
            return random.choice(team["players"])

        # 按shooting加权
        weighted = []
        for p, base_weight in candidates:
            shooting_w = p.get("shooting", 50) / 100.0
            weighted.append((p, base_weight * (0.5 + 0.5 * shooting_w)))

        total_w = sum(w for _, w in weighted)
        r = random.random() * total_w
        cumulative = 0
        for p, w in weighted:
            cumulative += w
            if r <= cumulative:
                return p
        return weighted[-1][0]

    def _pick_assist(self, team: dict, scorer_id: int = None) -> Optional[dict]:
        """选助攻球员"""
        on_field_m = [p for p in team.get("_midfielders", []) if p.get("_on_field", True)]
        on_field_f = [p for p in team.get("_forwards", []) if p.get("_on_field", True)]
        candidates = on_field_m + on_field_f
        if scorer_id:
            candidates = [p for p in candidates if p.get("id") != scorer_id]
        if not candidates:
            all_on_field = [p for p in team["players"] if p.get("_on_field", True)]
            candidates = [p for p in all_on_field if p.get("id") != scorer_id]

        if candidates and random.random() < 0.65:  # 65%概率有助攻
            return random.choice(candidates)
        return None

    def _pick_card_player(self, team: dict, position_bias: list = None) -> dict:
        """选一个吃牌的球员（优先场上球员）"""
        on_field = [p for p in team["players"] if p.get("_on_field", True)]
        if position_bias:
            biased = [p for p in on_field if p.get("position", "") in position_bias]
            if biased and random.random() < 0.6:
                return random.choice(biased)
        if on_field:
            return random.choice(on_field)
        return random.choice(team["players"])

    def _perform_substitution(self, minute: int, team: dict):
        """执行一次换人"""
        team_id = team["team_id"]

        # 找出场上非门将球员（门将不能轻易被换）
        on_field_non_gk = [p for p in team["players"]
                           if p.get("_on_field", True) and p.get("position", "") not in GOALKEEPER_POSITIONS]

        # 找出替补席上的球员（后3名且不在场上的）
        bench = [p for p in team.get("_sorted_players", team["players"])
                 if not p.get("_on_field", True) and p.get("_is_substitute", False)]

        if not on_field_non_gk or not bench:
            return False

        # 选一个场上球员换下（优先选体能低的）
        on_field_non_gk.sort(key=lambda p: p.get("stamina", 50))
        player_out = on_field_non_gk[0]

        # 选一个替补上场（优先选总评高的）
        bench.sort(key=lambda p: -(p.get("overall", 0) or p.get("shooting", 50) + p.get("defense", 50)))
        player_in = bench[0]

        out_name = player_out.get("name") or player_out.get("name_cn", "")
        in_name = player_in.get("name") or player_in.get("name_cn", "")

        # 执行换人
        player_out["_on_field"] = False
        player_in["_on_field"] = True
        player_in["_is_substitute"] = False

        # 新上场球员体力回满
        player_in["stamina"] = min(100, player_in.get("stamina", 50) + 30)

        detail = random.choice(SUBSTITUTION_DETAILS)

        self._add_event(minute, "substitution", team_id,
                        player_name=in_name,
                        player_id=player_in.get("id"),
                        detail=f"换下{out_name}，{detail}")

        return True

    def _add_event(self, minute: int, event_type: str, team_id: str,
                   player_name: str = None, player_id: int = None,
                   detail: str = None, assist: str = None):
        """添加比赛事件（附带解说）"""
        event = {
            "minute": minute,
            "type": event_type,
            "team_id": team_id,
            "commentary": get_commentary(event_type),
        }
        if player_name:
            event["player_name"] = player_name
        if player_id is not None:
            event["player_id"] = player_id
        if detail:
            event["detail"] = detail
        if assist:
            event["assist"] = assist
        self.events.append(event)

    def _get_goal_narrative(self, detail: str, player: str, assist: str, score: str) -> list:
        """根据进球类型生成5步回放叙述"""
        for key, narrative in GOAL_NARRATIVES.items():
            if key in detail:
                lines = []
                for line in narrative:
                    formatted = line.format(player=player, assist=assist or "队友", score=score)
                    lines.append(formatted)
                return lines
        # 通用回退
        return [
            f"{player} 发动进攻...",
            f"与{assist or '队友'}做出精妙配合",
            "起脚射门！！！",
            f"⚽ 球进了！比分 {score}！",
            f"{player} 疯狂庆祝！",
        ]

    def _get_celebration(self, player_name: str) -> str:
        """生成庆祝描述"""
        celebration = random.choice(GOAL_CELEBRATIONS)
        return f"{player_name} {celebration}"

    def _add_goal_highlight(self, minute: int, team_id: str, scorer: dict,
                            assist_player: Optional[dict], detail: str,
                            score_before: str, score_after: str):
        """添加进球精彩瞬间"""
        scorer_name = scorer.get("name") or scorer.get("name_cn", "")
        assist_name = assist_player.get("name") or assist_player.get("name_cn", "") if assist_player else None

        narrative = self._get_goal_narrative(detail, scorer_name, assist_name or "队友", score_after)
        celebration = self._get_celebration(scorer_name)

        highlight = {
            "type": "goal",
            "minute": minute,
            "team_id": team_id,
            "player_name": scorer_name,
            "assist": assist_name,
            "detail": detail,
            "score_before": score_before,
            "score_after": score_after,
            "narrative": narrative,
            "celebration": celebration,
            "is_highlight": True,
        }
        self._highlights.append(highlight)

    def _add_save_highlight(self, minute: int, team_id: str, gk_name: str,
                            attacker: dict, score: str):
        """添加精彩扑救瞬间"""
        attacker_name = attacker.get("name") or attacker.get("name_cn", "")
        narrative_template = random.choice(SAVE_NARRATIVES)
        narrative = [line.format(goalkeeper=gk_name) for line in narrative_template]

        highlight = {
            "type": "great_save",
            "minute": minute,
            "team_id": team_id,
            "player_name": gk_name,
            "assist": None,
            "detail": f"{gk_name} 扑出 {attacker_name} 的必进球！",
            "score_before": score,
            "score_after": score,
            "narrative": narrative,
            "celebration": f"{gk_name} 起身握拳怒吼！队友纷纷上前祝贺！",
            "is_highlight": True,
        }
        self._highlights.append(highlight)

    def _add_near_miss_highlight(self, minute: int, team_id: str,
                                 attacker: dict, score: str):
        """添加差点进球瞬间"""
        attacker_name = attacker.get("name") or attacker.get("name_cn", "")
        narrative_template = random.choice(NEAR_MISS_NARRATIVES)
        narrative = [line.format(player=attacker_name) for line in narrative_template]

        highlight = {
            "type": "near_miss",
            "minute": minute,
            "team_id": team_id,
            "player_name": attacker_name,
            "assist": None,
            "detail": f"{attacker_name} 的射门差之毫厘！",
            "score_before": score,
            "score_after": score,
            "narrative": narrative,
            "celebration": None,
            "is_highlight": True,
        }
        self._highlights.append(highlight)

    def _add_red_card_highlight(self, minute: int, team_id: str,
                                player_name: str, detail: str, score: str):
        """添加红牌精彩瞬间"""
        narrative_template = random.choice(RED_CARD_NARRATIVES)
        narrative = [line.format(player=player_name, team=team_id) for line in narrative_template]

        highlight = {
            "type": "red_card",
            "minute": minute,
            "team_id": team_id,
            "player_name": player_name,
            "assist": None,
            "detail": detail,
            "score_before": score,
            "score_after": score,
            "narrative": narrative,
            "celebration": None,
            "is_highlight": True,
        }
        self._highlights.append(highlight)

    def _simulate_half(self, start: int, end: int, half_bias: float = 1.0):
        """模拟半场比赛"""
        interval = 3  # 每3分钟检查

        for minute in range(start, end, interval):
            self.minute = minute

            # ===== 换人逻辑（60-75分钟区间） =====
            if 60 <= minute <= 75:
                for team in [self.home, self.away]:
                    subs_left = team.get("_substitutions_left", 0)
                    # 每次检查15%概率换人，每队最多3次
                    if subs_left > 0 and random.random() < 0.15:
                        if self._perform_substitution(minute, team):
                            team["_substitutions_left"] = subs_left - 1

            # 随机确认进攻方
            # 计算攻防强度
            home_attack = self._calc_attack_strength(self.home)
            away_attack = self._calc_attack_strength(self.away)
            home_defense = self._calc_defense_strength(self.home)
            away_defense = self._calc_defense_strength(self.away)

            # 进攻概率 = 己方攻击力 / (己方攻击力 + 对方攻击力)
            home_poss_prob = home_attack / (home_attack + away_attack) if (home_attack + away_attack) > 0 else 0.5
            home_poss_prob = max(0.3, min(0.7, home_poss_prob))  # 限制范围

            is_home_attack = random.random() < home_poss_prob

            if is_home_attack:
                attack_team = self.home
                defense_team = self.away
                attack_team_id = self.home["team_id"]
                attack_strength = home_attack
                defense_strength = away_defense
            else:
                attack_team = self.away
                defense_team = self.home
                attack_team_id = self.away["team_id"]
                attack_strength = away_attack
                defense_strength = home_defense

            # 天气影响：犯规加成
            weather_mods = self._get_weather_mods()
            foul_mod = weather_mods.get("foul_mod", 0)

            # 黄牌事件 (~2.5% 每3分钟，受天气影响)
            yellow_base = 0.025 * half_bias
            if foul_mod:
                yellow_base *= (1 + foul_mod)
            if random.random() < yellow_base:
                side = random.choice(["home", "away"])
                card_team = self.home if side == "home" else self.away
                player = self._pick_card_player(card_team, ["CB", "CDM", "LB", "RB"])
                p_id = player.get("id")

                # 检查两黄变一红
                yellow_count = self.yellow_cards.get(p_id, 0)
                if yellow_count >= 1 and random.random() < 0.3:
                    # 两黄变一红
                    card_detail = random.choice(RED_CARD_DETAILS)
                    card_player_name = player.get("name") or player.get("name_cn", "")
                    self._add_event(minute, "red_card", card_team["team_id"],
                                    player_name=card_player_name,
                                    player_id=p_id,
                                    detail=card_detail)
                    self._add_red_card_highlight(
                        minute=minute,
                        team_id=card_team["team_id"],
                        player_name=card_player_name,
                        detail=card_detail,
                        score=f"{self.home_score}-{self.away_score}",
                    )
                else:
                    self.yellow_cards[p_id] = self.yellow_cards.get(p_id, 0) + 1
                    self._add_event(minute, "yellow_card", card_team["team_id"],
                                    player_name=player.get("name") or player.get("name_cn", ""),
                                    player_id=p_id,
                                    detail=random.choice(YELLOW_CARD_DETAILS))

            # 红牌事件 (~0.5% 每3分钟，受天气影响)
            red_base = 0.005 * half_bias
            if foul_mod:
                red_base *= (1 + foul_mod * 0.5)
            if random.random() < red_base:
                side = random.choice(["home", "away"])
                card_team = self.home if side == "home" else self.away
                player = self._pick_card_player(card_team, ["CB", "CDM", "ST"])
                card_detail = random.choice(RED_CARD_DETAILS)
                card_player_name = player.get("name") or player.get("name_cn", "")
                self._add_event(minute, "red_card", card_team["team_id"],
                                player_name=card_player_name,
                                player_id=player.get("id"),
                                detail=card_detail)
                self._add_red_card_highlight(
                    minute=minute,
                    team_id=card_team["team_id"],
                    player_name=card_player_name,
                    detail=card_detail,
                    score=f"{self.home_score}-{self.away_score}",
                )

            # 进球判定
            # P(goal) = (attack / (attack + defense)) * randomness * base_rate * half_bias
            if attack_strength + defense_strength <= 0:
                continue

            randomness = random.uniform(0.3, 1.8)  # 随机因子
            goal_prob = (attack_strength / (attack_strength + defense_strength)) * randomness * half_bias * 0.15

            # 天气影响：射门概率调整
            shooting_mod = weather_mods.get("shooting_mod", 0)
            if shooting_mod:
                goal_prob *= (1 + shooting_mod)

            # 下半场体力下降，概率略降
            if minute >= 60:
                goal_prob *= 0.9
            if minute >= 75:
                goal_prob *= 0.85

            goal_prob = max(0.005, min(0.25, goal_prob))  # 限制范围

            score_before = f"{self.home_score}-{self.away_score}"

            if random.random() < goal_prob:
                scorer = self._pick_scorer(attack_team)
                assist_player = self._pick_assist(attack_team, scorer.get("id"))
                detail = random.choice(GOAL_DETAILS)

                if is_home_attack:
                    self.home_score += 1
                else:
                    self.away_score += 1

                score_after = f"{self.home_score}-{self.away_score}"

                self._add_event(
                    minute=minute,
                    event_type="goal",
                    team_id=attack_team_id,
                    player_name=scorer.get("name") or scorer.get("name_cn", ""),
                    player_id=scorer.get("id"),
                    detail=detail,
                    assist=assist_player.get("name") or assist_player.get("name_cn", "") if assist_player else None,
                )

                # 生成进球精彩瞬间
                self._add_goal_highlight(
                    minute=minute,
                    team_id=attack_team_id,
                    scorer=scorer,
                    assist_player=assist_player,
                    detail=detail,
                    score_before=score_before,
                    score_after=score_after,
                )
            elif goal_prob > 0.15:
                # 高概率射门未进 → 精彩扑救或差点进球
                attacker = self._pick_scorer(attack_team)
                score_str = f"{self.home_score}-{self.away_score}"
                if random.random() < 0.6 and defense_team.get("_goalkeepers"):
                    # 精彩扑救
                    on_field_gk = [gk for gk in defense_team["_goalkeepers"] if gk.get("_on_field", True)]
                    if on_field_gk:
                        gk = on_field_gk[0]
                        gk_name = gk.get("name") or gk.get("name_cn", "")
                        self._add_save_highlight(minute, defense_team["team_id"], gk_name, attacker, score_str)
                    else:
                        self._add_near_miss_highlight(minute, attack_team_id, attacker, score_str)
                else:
                    # 差点进球
                    self._add_near_miss_highlight(minute, attack_team_id, attacker, score_str)

    def _calc_player_ratings(self) -> dict:
        """计算所有球员评分"""
        team_ids = [self.home["team_id"], self.away["team_id"]]
        teams = {self.home["team_id"]: self.home, self.away["team_id"]: self.away}
        ratings = {self.home["team_id"]: [], self.away["team_id"]: []}

        # 统计事件
        player_goals = {}
        player_assists = {}
        player_yellows = {}
        player_reds = {}
        player_minutes = {}

        for event in self.events:
            p_id = event.get("player_id")
            if p_id is None:
                continue
            if event["type"] == "goal":
                player_goals[p_id] = player_goals.get(p_id, 0) + 1
            if event.get("assist"):
                # 找助攻球员
                for e in self.events:
                    if e.get("type") == "goal" and e.get("assist") == event.get("assist"):
                        pass
            if event["type"] == "yellow_card":
                player_yellows[p_id] = player_yellows.get(p_id, 0) + 1
            if event["type"] == "red_card":
                player_reds[p_id] = player_reds.get(p_id, 0) + 1

        # 收集助攻
        assist_name_to_id = {}
        for p in self.home["players"]:
            name = p.get("name") or p.get("name_cn", "")
            assist_name_to_id[name] = p.get("id")
        for p in self.away["players"]:
            name = p.get("name") or p.get("name_cn", "")
            assist_name_to_id[name] = p.get("id")

        for event in self.events:
            if event["type"] == "goal" and event.get("assist"):
                a_id = assist_name_to_id.get(event["assist"])
                if a_id is not None:
                    player_assists[a_id] = player_assists.get(a_id, 0) + 1

        for team_id in team_ids:
            team = teams[team_id]
            for p in team["players"]:
                p_id = p.get("id")
                name = p.get("name") or p.get("name_cn", "")
                pos = p.get("position", "")

                # 基础评分
                base = 6.0

                # 位置贡献
                if pos in GOALKEEPER_POSITIONS:
                    base += (p.get("defense", 50) / 100.0) * 1.5
                    # 失球扣分
                    if team_id == self.home["team_id"]:
                        base -= self.away_score * 0.3
                    else:
                        base -= self.home_score * 0.3
                elif pos in DEFENDER_POSITIONS:
                    base += (p.get("defense", 50) / 100.0) * 1.0 + (p.get("physical", 50) / 100.0) * 0.5
                    # 失球扣分(防守球员)
                    if team_id == self.home["team_id"]:
                        base -= self.away_score * 0.2
                    else:
                        base -= self.home_score * 0.2
                elif pos in MIDFIELDER_POSITIONS:
                    base += (p.get("passing", 50) / 100.0) * 1.0 + (p.get("stamina", 50) / 100.0) * 0.5
                elif pos in FORWARD_POSITIONS:
                    base += (p.get("shooting", 50) / 100.0) * 0.8 + (p.get("pace", 50) / 100.0) * 0.5

                # 进球加分
                g = player_goals.get(p_id, 0)
                base += g * 1.5
                if g >= 2:
                    base += 0.5  # 梅开二度加成

                # 助攻加分
                base += player_assists.get(p_id, 0) * 0.5

                # 红黄牌扣分
                base -= player_yellows.get(p_id, 0) * 0.5
                if player_reds.get(p_id, 0) > 0:
                    base -= 2.0

                # 限制在 1.0 ~ 10.0 之间
                rating = max(1.0, min(10.0, base))
                rating = round(rating * 2) / 2  # 保留0.5精度

                ratings[team_id].append({
                    "player_name": name,
                    "rating": rating,
                    "goals": g,
                    "assists": player_assists.get(p_id, 0),
                    "yellow": player_yellows.get(p_id, 0),
                    "red": player_reds.get(p_id, 0),
                })

        return ratings

    def _determine_winner(self) -> Optional[str]:
        """判定胜者（平局则点球决胜）"""
        if self.home_score > self.away_score:
            return self.home["team_id"]
        elif self.away_score > self.home_score:
            return self.away["team_id"]
        # 常规时间平局 → 点球大战
        self._simulate_penalty_shootout()
        if self.home_penalty is not None and self.away_penalty is not None:
            if self.home_penalty > self.away_penalty:
                return self.home["team_id"]
            else:
                return self.away["team_id"]
        return None

    def _simulate_penalty_shootout(self):
        """点球大战模拟"""
        home_goals = 0
        away_goals = 0
        results = []

        def _get_gk(team: dict) -> dict:
            keepers = team.get("_goalkeepers", [])
            return keepers[0] if keepers else {}

        def _attempt(taker: dict, gk: dict) -> bool:
            shooting = taker.get("shooting", 50)
            defending = gk.get("defense", 50) if gk else 50
            score_prob = shooting / max(shooting + defending, 1) * 0.8
            return random.random() < score_prob

        # 5轮点球
        for round_num in range(1, 6):
            for team_info in [
                (self.home, self.home["team_id"]),
                (self.away, self.away["team_id"]),
            ]:
                team, team_id = team_info
                eligible = [p for p in team["players"] if p.get("position", "") not in ["GK"]]
                if not eligible:
                    eligible = team["players"]
                taker = random.choice(eligible)
                gk = _get_gk(self.away if team_id == self.home["team_id"] else self.home)
                scored = _attempt(taker, gk)

                if team_id == self.home["team_id"]:
                    if scored:
                        home_goals += 1
                else:
                    if scored:
                        away_goals += 1

                results.append({
                    "round": round_num,
                    "team_id": team_id,
                    "taker_name": taker.get("name") or taker.get("name_cn", ""),
                    "scored": scored,
                })

        # 如果还平局，突然死亡
        round_num = 6
        while home_goals == away_goals:
            for team_info in [
                (self.home, self.home["team_id"]),
                (self.away, self.away["team_id"]),
            ]:
                team, team_id = team_info
                eligible = [p for p in team["players"] if p.get("position", "") not in ["GK"]]
                if not eligible:
                    eligible = team["players"]
                taker = random.choice(eligible)
                gk = _get_gk(self.away if team_id == self.home["team_id"] else self.home)
                scored = _attempt(taker, gk)

                if team_id == self.home["team_id"]:
                    if scored:
                        home_goals += 1
                else:
                    if scored:
                        away_goals += 1

                results.append({
                    "round": round_num,
                    "team_id": team_id,
                    "taker_name": taker.get("name") or taker.get("name_cn", ""),
                    "scored": scored,
                })
            round_num += 1

        self.home_penalty = home_goals
        self.away_penalty = away_goals
        self.duration = "penalty"

        # 添加点球事件
        self._add_event(90, "penalty_shootout", self.home["team_id"],
                        detail=f"点球大战结束: {home_goals}-{away_goals}")

        return {
            "home_penalty": home_goals,
            "away_penalty": away_goals,
            "results": results,
        }

    def simulate(self) -> dict:
        """
        模拟整场比赛
        返回完整比赛报告
        """
        # 开局解说
        self._add_event(1, "kickoff", self.home["team_id"])

        # 上半场 0-45
        self._simulate_half(0, 46, half_bias=1.0)

        # 中场解说
        self._add_event(45, "halftime", self.home["team_id"])

        # 下半场 45-90
        self._simulate_half(45, 91, half_bias=1.0)

        # 全场结束解说
        self._add_event(90, "fulltime", self.home["team_id"])

        # 计算评分
        player_ratings = self._calc_player_ratings()

        # 判定胜者（平局自动点球）
        winner = self._determine_winner()

        return {
            "home_score": self.home_score,
            "away_score": self.away_score,
            "home_penalty": self.home_penalty,
            "away_penalty": self.away_penalty,
            "winner": winner,
            "duration": self.duration,
            "events": self.events,
            "player_ratings": player_ratings,
            "highlights": self._highlights,
            # 额外信息
            "weather": self.weather,
            "formation_home": self.formation_home,
            "formation_away": self.formation_away,
            "substitutions_home": SUBSTITUTIONS_PER_TEAM - self.home.get("_substitutions_left", 0),
            "substitutions_away": SUBSTITUTIONS_PER_TEAM - self.away.get("_substitutions_left", 0),
        }
