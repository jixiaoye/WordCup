"""SQLAlchemy 数据模型"""
from datetime import datetime, timezone

from wxcloudrun import db


def _utcnow():
    return datetime.now(timezone.utc)


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.String(10), primary_key=True)
    name_cn = db.Column(db.String(50), nullable=False)
    name_en = db.Column(db.String(50), nullable=False)
    flag_emoji = db.Column(db.String(10), nullable=False)
    continent = db.Column(db.String(20), nullable=False)
    tier = db.Column(db.Integer, nullable=False)
    overall = db.Column(db.Integer, default=80)
    color_primary = db.Column(db.String(10), default="#1A1A2E")
    color_secondary = db.Column(db.String(10), default="#E94560")
    created_at = db.Column(db.DateTime, default=_utcnow)


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team_id = db.Column(db.String(10), db.ForeignKey("teams.id"), index=True, nullable=False)
    name_cn = db.Column(db.String(50), nullable=False)
    name_en = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(10), nullable=False)
    number = db.Column(db.Integer, default=0)
    pace = db.Column(db.Integer, default=50)
    shooting = db.Column(db.Integer, default=50)
    passing = db.Column(db.Integer, default=50)
    defense = db.Column(db.Integer, default=50)
    stamina = db.Column(db.Integer, default=50)
    physical = db.Column(db.Integer, default=50)

    @property
    def overall(self) -> int:
        weights = {
            "GK": {"defense": 0.4, "physical": 0.25, "passing": 0.15, "stamina": 0.1, "pace": 0.05, "shooting": 0.05},
            "CB": {"defense": 0.4, "physical": 0.25, "passing": 0.15, "pace": 0.1, "stamina": 0.07, "shooting": 0.03},
            "LB": {"pace": 0.25, "defense": 0.25, "stamina": 0.2, "passing": 0.15, "physical": 0.1, "shooting": 0.05},
            "RB": {"pace": 0.25, "defense": 0.25, "stamina": 0.2, "passing": 0.15, "physical": 0.1, "shooting": 0.05},
            "CDM": {"defense": 0.3, "physical": 0.25, "passing": 0.2, "stamina": 0.15, "pace": 0.05, "shooting": 0.05},
            "CM": {"passing": 0.3, "stamina": 0.2, "shooting": 0.15, "physical": 0.15, "defense": 0.1, "pace": 0.1},
            "CAM": {"passing": 0.3, "shooting": 0.25, "pace": 0.15, "stamina": 0.15, "physical": 0.1, "defense": 0.05},
            "LW": {"pace": 0.3, "shooting": 0.25, "passing": 0.2, "stamina": 0.1, "physical": 0.1, "defense": 0.05},
            "RW": {"pace": 0.3, "shooting": 0.25, "passing": 0.2, "stamina": 0.1, "physical": 0.1, "defense": 0.05},
            "ST": {"shooting": 0.35, "pace": 0.25, "physical": 0.2, "passing": 0.1, "stamina": 0.07, "defense": 0.03},
        }
        w = weights.get(self.position, {})
        if not w:
            return (self.pace + self.shooting + self.passing + self.defense + self.stamina + self.physical) // 6
        return round(sum(getattr(self, attr) * weight for attr, weight in w.items()))


class GameRoom(db.Model):
    __tablename__ = "game_rooms"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(10), unique=True, index=True, nullable=False)
    host_player = db.Column(db.String(50), nullable=False)
    guest_player = db.Column(db.String(50), nullable=True)
    host_team_id = db.Column(db.String(10), db.ForeignKey("teams.id"), nullable=False)
    guest_team_id = db.Column(db.String(10), db.ForeignKey("teams.id"), nullable=True)
    status = db.Column(db.String(20), default="waiting")
    current_match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_id = db.Column(db.Integer, db.ForeignKey("game_rooms.id"), nullable=True, index=True)
    team_home_id = db.Column(db.String(10), db.ForeignKey("teams.id"), nullable=False)
    team_away_id = db.Column(db.String(10), db.ForeignKey("teams.id"), nullable=False)
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    home_penalty = db.Column(db.Integer, nullable=True)
    away_penalty = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default="pending")
    winner = db.Column(db.String(10), nullable=True)
    round_name = db.Column(db.String(50), default="16强")
    match_report = db.Column(db.Text, nullable=True)
    current_turn = db.Column(db.Integer, default=0)
    turn_phase = db.Column(db.String(20), default="idle")
    attacking_team = db.Column(db.String(10), nullable=True)
    turn_deadline = db.Column(db.DateTime, nullable=True)
    home_player = db.Column(db.String(50), nullable=True)
    away_player = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)


class MatchEvent(db.Model):
    __tablename__ = "match_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), index=True, nullable=False)
    minute = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    team_id = db.Column(db.String(10), nullable=False)
    player_id = db.Column(db.Integer, nullable=True)
    player_name = db.Column(db.String(50), nullable=True)
    detail = db.Column(db.String(200), nullable=True)
    turn_number = db.Column(db.Integer, nullable=True)


class MatchTurn(db.Model):
    __tablename__ = "match_turns"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), index=True, nullable=False)
    turn_number = db.Column(db.Integer, nullable=False)
    attacking_team = db.Column(db.String(10), nullable=False)
    defensing_team = db.Column(db.String(10), nullable=False)
    attack_action = db.Column(db.String(20), nullable=True)
    defense_action = db.Column(db.String(20), nullable=True)
    result = db.Column(db.Text, nullable=True)
    zone = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default="waiting_attack")
    created_at = db.Column(db.DateTime, default=_utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)


class AdZone(db.Model):
    __tablename__ = "ad_zones"

    id = db.Column(db.String(4), primary_key=True)
    position = db.Column(db.String(32), nullable=False)
    size_category = db.Column(db.String(10), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(64), nullable=False)


class AdCampaign(db.Model):
    __tablename__ = "ad_campaigns"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    advertiser_name = db.Column(db.String(64), nullable=False)
    slogan = db.Column(db.String(128), nullable=False)
    bg_color = db.Column(db.String(16), default="#333333")
    text_color = db.Column(db.String(16), default="#FFFFFF")
    zone_id = db.Column(db.String(4), db.ForeignKey("ad_zones.id"), nullable=False)
    logo_text = db.Column(db.String(32), default="")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_utcnow)


class Mascot(db.Model):
    __tablename__ = "mascots"

    team_id = db.Column(db.String(10), db.ForeignKey("teams.id"), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    name_en = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(20), nullable=False)
    element = db.Column(db.String(10), nullable=False)
    rarity = db.Column(db.Integer, default=1)
    boost_attack = db.Column(db.Integer, default=0)
    boost_defense = db.Column(db.Integer, default=0)
    boost_speed = db.Column(db.Integer, default=0)
    boost_spirit = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, default="")
    description_en = db.Column(db.Text, default="")


class Tournament(db.Model):
    __tablename__ = "tournaments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="draw")
    round_name = db.Column(db.String(20), default="16强")
    current_round = db.Column(db.Integer, default=1)
    teams_json = db.Column(db.Text, nullable=False)
    bracket_json = db.Column(db.Text, nullable=True)
    winner = db.Column(db.String(10), nullable=True)
    top_scorer = db.Column(db.String(100), nullable=True)
    mvp = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)


class TournamentMatch(db.Model):
    __tablename__ = "tournament_matches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id"), index=True, nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    match_order = db.Column(db.Integer, nullable=False)
    team_home_id = db.Column(db.String(10), nullable=True)
    team_away_id = db.Column(db.String(10), nullable=True)
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    home_penalty = db.Column(db.Integer, nullable=True)
    away_penalty = db.Column(db.Integer, nullable=True)
    winner = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(20), default="pending")
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=True)
    match_report_json = db.Column(db.Text, nullable=True)
