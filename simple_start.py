#!/usr/bin/env python3
"""
NetManagerX简化启动脚本
仅启动核心功能，避免复杂依赖
"""

import os
import sys
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# 设置环境变量
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///netmanagerx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化扩展
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'info'

# 简单的数据模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    device_type = db.Column(db.String(50), default='cisco_switch')
    connection_type = db.Column(db.String(20), default='ssh')
    port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(50))
    password_encrypted = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

# 表单
class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 80)])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class DeviceForm(FlaskForm):
    name = StringField('设备名称', validators=[DataRequired(), Length(1, 100)])
    ip_address = StringField('IP地址', validators=[DataRequired()])
    device_type = StringField('设备类型', default='cisco_switch')
    connection_type = StringField('连接类型', default='ssh')
    port = StringField('端口', default='22')
    username = StringField('用户名')
    password = PasswordField('密码')
    description = StringField('描述')
    submit = SubmitField('保存')

# 用户加载器
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 路由
@app.route('/')
def index():
    if current_user.is_authenticated:
        devices = Device.query.filter_by(is_active=True).all()
        return render_template('dashboard.html', devices=devices)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            flash(f'欢迎回来，{user.username}！', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('login'))

@app.route('/devices')
@login_required
def devices():
    devices = Device.query.filter_by(is_active=True).all()
    return render_template('devices.html', devices=devices)

@app.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    form = DeviceForm()
    if form.validate_on_submit():
        device = Device(
            name=form.name.data,
            ip_address=form.ip_address.data,
            device_type=form.device_type.data,
            connection_type=form.connection_type.data,
            port=int(form.port.data) if form.port.data else 22,
            username=form.username.data,
            description=form.description.data,
            created_by=current_user.id
        )
        if form.password.data:
            device.password_encrypted = generate_password_hash(form.password.data)
        
        db.session.add(device)
        db.session.commit()
        flash('设备添加成功', 'success')
        return redirect(url_for('devices'))
    
    return render_template('add_device.html', form=form)

@app.route('/api/stats')
@login_required
def api_stats():
    device_count = Device.query.filter_by(is_active=True).count()
    return jsonify({
        'devices': device_count,
        'users': 1,
        'status': 'running'
    })

@app.route('/health')
def health():
    return 'OK', 200

# 模板
@app.route('/dashboard')
@login_required
def dashboard():
    devices = Device.query.filter_by(is_active=True).all()
    return render_template('dashboard.html', devices=devices)

# 初始化数据库
@app.cli.command()
def init_db():
    """初始化数据库"""
    print("正在初始化数据库...")
    db.create_all()
    
    # 创建默认管理员用户（如果不存在）
    existing_user = User.query.filter_by(username='admin').first()
    if not existing_user:
        admin_user = User(
            username='admin',
            email='admin@example.com'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("默认管理员用户已创建")
    else:
        print("默认管理员用户已存在")
    
    print("数据库初始化完成！")
    print("默认管理员账户: admin / admin123")

if __name__ == '__main__':
    # 检查数据库是否存在，如果不存在则初始化
    if not os.path.exists('netmanagerx.db'):
        print("数据库不存在，正在初始化...")
        with app.app_context():
            init_db()
    
    print("NetManagerX简化版启动中...")
    print("访问地址: http://localhost:5000")
    print("默认管理员账户: admin / admin123")
    print("按 Ctrl+C 停止服务器")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
