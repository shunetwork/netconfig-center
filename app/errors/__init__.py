"""
错误处理模块蓝图
"""

from flask import Blueprint

bp = Blueprint('errors', __name__)

from app.errors import handlers
