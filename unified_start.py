#!/usr/bin/env python3
"""
NetManagerX统一启动脚本
合并测试和运行环境
"""

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import click

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'netmanagerx-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///netmanagerx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化扩展
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录以访问此页面。'

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

# 设备模型
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    hostname = db.Column(db.String(100))
    device_type = db.Column(db.String(50), default='cisco')
    connection_type = db.Column(db.String(20), default='ssh')
    port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(100))
    password = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Device {self.name} ({self.ip_address})>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 路由定义
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            user.ping()
            flash(f'欢迎回来，{user.username}！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已退出登录。', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    devices = Device.query.filter_by(is_active=True).all()
    return render_template('dashboard.html', user=current_user, devices=devices)

@app.route('/devices')
@login_required
def devices():
    devices = Device.query.filter_by(is_active=True).all()
    return render_template('devices.html', devices=devices)

@app.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        device = Device(
            name=request.form.get('name'),
            ip_address=request.form.get('ip_address'),
            hostname=request.form.get('hostname'),
            device_type=request.form.get('device_type', 'cisco'),
            connection_type=request.form.get('connection_type', 'ssh'),
            port=int(request.form.get('port', 22)),
            username=request.form.get('username'),
            password=request.form.get('password'),
            description=request.form.get('description')
        )
        db.session.add(device)
        db.session.commit()
        flash('设备添加成功', 'success')
        return redirect(url_for('devices'))
    
    return render_template('add_device.html')

@app.route('/api/devices')
@login_required
def api_devices():
    devices = Device.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': device.id,
        'name': device.name,
        'ip_address': device.ip_address,
        'hostname': device.hostname,
        'device_type': device.device_type,
        'connection_type': device.connection_type,
        'port': device.port,
        'is_active': device.is_active
    } for device in devices])

@app.route('/health')
def health():
    return jsonify({'status': 'OK', 'message': 'NetManagerX is running'})

# 数据库初始化命令
@app.cli.command('init-db')
def init_db():
    """初始化数据库"""
    print("正在初始化数据库...")
    db.create_all()
    
    # 检查用户是否已存在
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
    
    # 创建测试设备
    existing_device = Device.query.filter_by(name='测试路由器').first()
    if not existing_device:
        test_device = Device(
            name='测试路由器',
            ip_address='192.168.1.1',
            hostname='router-01',
            device_type='cisco',
            connection_type='ssh',
            port=22,
            username='admin',
            password='password',
            description='测试设备'
        )
        db.session.add(test_device)
        db.session.commit()
        print("测试设备已创建")
    else:
        print("测试设备已存在")
    
    print("数据库初始化完成！")
    print("默认管理员账户: admin / admin123")

# 测试命令
@app.cli.command('test')
def run_tests():
    """运行测试"""
    import subprocess
    import sys
    
    print("运行NetManagerX测试...")
    
    # 运行基础测试
    result = subprocess.run([sys.executable, 'test_basic.py'], capture_output=True, text=True)
    print("基础测试结果:")
    print(result.stdout)
    if result.stderr:
        print("错误信息:")
        print(result.stderr)
    
    # 运行启动测试
    result = subprocess.run([sys.executable, 'test_startup.py'], capture_output=True, text=True)
    print("启动测试结果:")
    print(result.stdout)
    if result.stderr:
        print("错误信息:")
        print(result.stderr)

if __name__ == '__main__':
    # 检查数据库是否存在，如果不存在则初始化
    if not os.path.exists('netmanagerx.db'):
        print("数据库不存在，正在初始化...")
        with app.app_context():
            init_db()
    
    print("NetManagerX统一服务启动中...")
    print("访问地址: http://localhost:5000")
    print("默认管理员账户: admin / admin123")
    print("按 Ctrl+C 停止服务器")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
