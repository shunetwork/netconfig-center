"""
错误处理器
"""

from flask import render_template, request, jsonify
from app import db
from app.errors import bp

@bp.app_errorhandler(404)
def not_found_error(error):
    """404错误处理"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    """500错误处理"""
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('errors/500.html'), 500

@bp.app_errorhandler(403)
def forbidden_error(error):
    """403错误处理"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Forbidden'}), 403
    return render_template('errors/403.html'), 403
