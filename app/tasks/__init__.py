"""
任务执行模块
包含异步任务处理、命令执行、结果记录等功能
"""

from flask import Blueprint

bp = Blueprint('tasks', __name__)

from app.tasks import routes