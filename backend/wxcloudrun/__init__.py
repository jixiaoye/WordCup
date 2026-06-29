"""WorldCup Showdown - Flask 应用"""
import logging

import pymysql
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

import config

pymysql.install_as_MySQLdb()

app = Flask(__name__, instance_relative_config=True)
app.config["DEBUG"] = config.DEBUG
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS

db = SQLAlchemy(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO if config.DEBUG else logging.WARNING)
logger = logging.getLogger(__name__)


def _init_database():
    """创建表结构并初始化种子数据"""
    import wxcloudrun.models  # noqa: F401 — register models
    db.create_all()
    logger.info("数据库表结构已创建/确认")

    from wxcloudrun.models import Team
    from seed_data import seed_all

    if Team.query.count() > 0:
        logger.info("数据库已有球队数据，跳过种子数据")
        return

    logger.info("开始初始化种子数据（32支球队、625名球员）...")
    seed_all()
    db.session.commit()
    logger.info("种子数据初始化完成")


with app.app_context():
    _init_database()

from wxcloudrun.views import register_blueprints  # noqa: E402

register_blueprints(app)
