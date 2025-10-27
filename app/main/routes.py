"""
主页面路由
"""

from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.main import bp
from app.models import Device, Task, AuditLog, ConfigBackup

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    """首页/仪表板"""
    # 获取统计数据
    stats = {
        'total_devices': Device.query.count(),
        'online_devices': Device.query.filter_by(status='online').count(),
        'offline_devices': Device.query.filter_by(status='offline').count(),
        'total_tasks': Task.query.count(),
        'running_tasks': Task.query.filter_by(status='running').count(),
        'recent_backups': ConfigBackup.query.order_by(ConfigBackup.created_at.desc()).limit(5).count()
    }
    
    # 获取最近的审计日志
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    
    # 获取最近的任务
    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(5).all()
    
    return render_template('main/index.html', 
                         stats=stats, 
                         recent_logs=recent_logs,
                         recent_tasks=recent_tasks)

@bp.route('/dashboard')
@login_required
def dashboard():
    """仪表板页面"""
    return render_template('main/dashboard.html')

@bp.route('/api/stats')
@login_required
def api_stats():
    """API: 获取统计数据"""
    stats = {
        'devices': {
            'total': Device.query.count(),
            'online': Device.query.filter_by(status='online').count(),
            'offline': Device.query.filter_by(status='offline').count(),
            'unknown': Device.query.filter_by(status='unknown').count()
        },
        'tasks': {
            'total': Task.query.count(),
            'pending': Task.query.filter_by(status='pending').count(),
            'running': Task.query.filter_by(status='running').count(),
            'success': Task.query.filter_by(status='success').count(),
            'failed': Task.query.filter_by(status='failed').count()
        },
        'backups': {
            'total': ConfigBackup.query.count(),
            'recent': ConfigBackup.query.order_by(ConfigBackup.created_at.desc()).limit(10).count()
        }
    }
    return jsonify(stats)
