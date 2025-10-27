"""
API模块路由
"""

from flask import jsonify, request
from flask_login import login_required
from app.api import bp

@bp.route('/health')
def health():
    """健康检查API"""
    return jsonify({
        'status': 'healthy',
        'message': 'NetManagerX API is running'
    })

@bp.route('/version')
def version():
    """版本信息API"""
    return jsonify({
        'version': '1.0.0',
        'name': 'NetManagerX',
        'description': '网络设备配置管理平台'
    })
