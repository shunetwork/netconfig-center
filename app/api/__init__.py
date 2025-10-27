"""
API模块蓝图
"""

from flask import Blueprint

bp = Blueprint('api', __name__)

from app.api import routes
