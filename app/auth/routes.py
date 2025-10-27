"""
认证模块路由
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.auth.forms import LoginForm, ChangePasswordForm
from app.models import User, AuditLog
from app import db

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.verify_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            user.ping()  # 更新最后登录时间
            
            # 记录登录日志
            AuditLog.log_action(
                user=user,
                action='login',
                resource_type='user',
                resource_id=user.id,
                resource_name=user.username,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=True
            )
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            
            flash(f'欢迎回来，{user.username}！', 'success')
            return redirect(next_page)
        else:
            # 记录登录失败日志
            if user:
                AuditLog.log_action(
                    user=user,
                    action='login_failed',
                    resource_type='user',
                    resource_id=user.id,
                    resource_name=user.username,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    success=False,
                    error_message='密码错误或账户未激活'
                )
            
            flash('用户名或密码错误', 'error')
    
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    username = current_user.username
    
    # 记录登出日志
    AuditLog.log_action(
        user=current_user,
        action='logout',
        resource_type='user',
        resource_id=current_user.id,
        resource_name=username,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@login_required
def profile():
    """用户资料页面"""
    return render_template('auth/profile.html', user=current_user)

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.verify_password(form.current_password.data):
            flash('当前密码错误', 'error')
            return render_template('auth/change_password.html', form=form)
        
        # 更新密码
        current_user.password = form.new_password.data
        db.session.commit()
        
        # 记录密码修改日志
        AuditLog.log_action(
            user=current_user,
            action='change_password',
            resource_type='user',
            resource_id=current_user.id,
            resource_name=current_user.username,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=True
        )
        
        flash('密码修改成功', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', form=form)

@bp.route('/api/user-info')
@login_required
def api_user_info():
    """API: 获取当前用户信息"""
    return jsonify(current_user.to_dict())
