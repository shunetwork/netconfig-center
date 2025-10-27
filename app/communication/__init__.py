"""
通信与接入模块
包含SSH、Telnet、RESTCONF等网络设备连接功能
"""

from flask import Blueprint

bp = Blueprint('communication', __name__)

from app.communication import routes
