"""
认证模块蓝图
包含用户登录、登出、注册等功能
"""

from flask import Blueprint

bp = Blueprint('auth', __name__)

from app.auth import routes
