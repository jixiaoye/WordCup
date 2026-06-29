"""
WorldCup 后端配置（微信云托管 Flask）
"""
import os
from pathlib import Path

DEBUG = os.getenv("DEBUG", "true").lower() == "true"

APP_NAME = "WorldCup Showdown"
APP_VERSION = "1.0.0"

# 微信云托管 MySQL 环境变量
MYSQL_USERNAME = os.environ.get("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
MYSQL_ADDRESS = os.environ.get("MYSQL_ADDRESS", "")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "worldcup")

# 云托管部署时配置 MYSQL_ADDRESS；本地开发默认 SQLite
if MYSQL_ADDRESS:
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_ADDRESS}/{MYSQL_DATABASE}"
    )
else:
    _db_path = Path(__file__).parent / "worldcup.db"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{_db_path}"

SQLALCHEMY_TRACK_MODIFICATIONS = False

# 比赛模拟参数
MATCH_GOAL_BASE_RATE = 0.025
MATCH_EVENT_INTERVAL = 3
