"""
配置模板模块蓝图
"""

from flask import Blueprint

bp = Blueprint('templates', __name__)

from app.templates import routes
