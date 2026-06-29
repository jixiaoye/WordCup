"""注册所有 Blueprint"""
from datetime import datetime, timezone

import config
from wxcloudrun.response import success_response

from wxcloudrun.views.teams import bp as teams_bp
from wxcloudrun.views.matches import bp as matches_bp
from wxcloudrun.views.game import bp as game_bp
from wxcloudrun.views.ranking import bp as ranking_bp
from wxcloudrun.views.stadium import bp as stadium_bp
from wxcloudrun.views.mascots import bp as mascots_bp
from wxcloudrun.views.achievements import bp as achievements_bp
from wxcloudrun.views.development import bp as development_bp
from wxcloudrun.views.tournament import bp as tournament_bp


def register_blueprints(app):
    for bp in (
        teams_bp, matches_bp, game_bp, ranking_bp,
        stadium_bp, mascots_bp, achievements_bp, development_bp, tournament_bp,
    ):
        app.register_blueprint(bp)

    @app.get("/api/health")
    def health_check():
        return success_response({
            "status": "ok",
            "version": config.APP_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @app.get("/api/v1/health")
    def health_check_v1():
        return success_response({
            "status": "ok",
            "version": config.APP_VERSION,
        })
