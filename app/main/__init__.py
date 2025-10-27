"""
主页面蓝图
包含首页、仪表板等主要页面
"""

from flask import Blueprint

bp = Blueprint('main', __name__)

from app.main import routes
