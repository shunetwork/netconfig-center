#!/usr/bin/env python3
"""
NetManagerX完整应用测试
测试完整的Web界面和功能
"""

import pytest
import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# 创建完整的测试应用
@pytest.fixture
def app():
    """创建完整的测试应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
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
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
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
    
    # 路由定义
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return render_template('dashboard.html', user=current_user)
        else:
            return redirect(url_for('login'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=True)
                user.ping()
                flash(f'欢迎回来，{user.username}！', 'success')
                return redirect(url_for('index'))
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
    
    # 模板
    @app.route('/templates/dashboard.html')
    def dashboard_template():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>NetManagerX - 仪表板</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #007bff; color: white; padding: 20px; border-radius: 5px; }
                .nav { margin: 20px 0; }
                .nav a { margin-right: 20px; text-decoration: none; color: #007bff; }
                .content { background: #f8f9fa; padding: 20px; border-radius: 5px; }
                .device-list { margin-top: 20px; }
                .device-item { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>NetManagerX 网络配置管理系统</h1>
                <p>欢迎，{{ user.username }}！</p>
            </div>
            
            <div class="nav">
                <a href="/dashboard">仪表板</a>
                <a href="/devices">设备管理</a>
                <a href="/logout">退出登录</a>
            </div>
            
            <div class="content">
                <h2>系统概览</h2>
                <p>网络配置管理系统运行正常</p>
                
                <div class="device-list">
                    <h3>设备列表</h3>
                    {% for device in devices %}
                    <div class="device-item">
                        <h4>{{ device.name }}</h4>
                        <p>IP地址: {{ device.ip_address }}</p>
                        <p>类型: {{ device.device_type }}</p>
                        <p>状态: {{ '在线' if device.is_active else '离线' }}</p>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </body>
        </html>
        '''
    
    @app.route('/templates/login.html')
    def login_template():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>NetManagerX - 登录</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f8f9fa; }
                .login-container { max-width: 400px; margin: 100px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
                button:hover { background: #0056b3; }
                .alert { padding: 10px; margin: 10px 0; border-radius: 5px; }
                .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            </style>
        </head>
        <body>
            <div class="login-container">
                <h2>NetManagerX 登录</h2>
                <form method="post">
                    <div class="form-group">
                        <label for="username">用户名:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">密码:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit">登录</button>
                </form>
            </div>
        </body>
        </html>
        '''
    
    @app.route('/templates/devices.html')
    def devices_template():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>NetManagerX - 设备管理</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #007bff; color: white; padding: 20px; border-radius: 5px; }
                .nav { margin: 20px 0; }
                .nav a { margin-right: 20px; text-decoration: none; color: #007bff; }
                .content { background: #f8f9fa; padding: 20px; border-radius: 5px; }
                .device-list { margin-top: 20px; }
                .device-item { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
                .btn:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>NetManagerX 设备管理</h1>
            </div>
            
            <div class="nav">
                <a href="/dashboard">仪表板</a>
                <a href="/devices">设备管理</a>
                <a href="/logout">退出登录</a>
            </div>
            
            <div class="content">
                <h2>设备列表</h2>
                <a href="/devices/add" class="btn">添加设备</a>
                
                <div class="device-list">
                    {% for device in devices %}
                    <div class="device-item">
                        <h4>{{ device.name }}</h4>
                        <p>IP地址: {{ device.ip_address }}</p>
                        <p>主机名: {{ device.hostname or 'N/A' }}</p>
                        <p>类型: {{ device.device_type }}</p>
                        <p>连接类型: {{ device.connection_type }}</p>
                        <p>端口: {{ device.port }}</p>
                        <p>状态: {{ '在线' if device.is_active else '离线' }}</p>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </body>
        </html>
        '''
    
    @app.route('/templates/add_device.html')
    def add_device_template():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>NetManagerX - 添加设备</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #007bff; color: white; padding: 20px; border-radius: 5px; }
                .nav { margin: 20px 0; }
                .nav a { margin-right: 20px; text-decoration: none; color: #007bff; }
                .content { background: #f8f9fa; padding: 20px; border-radius: 5px; }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input[type="text"], input[type="password"], input[type="number"], select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                button { padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
                button:hover { background: #0056b3; }
                .btn-secondary { background: #6c757d; }
                .btn-secondary:hover { background: #545b62; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>NetManagerX 添加设备</h1>
            </div>
            
            <div class="nav">
                <a href="/dashboard">仪表板</a>
                <a href="/devices">设备管理</a>
                <a href="/logout">退出登录</a>
            </div>
            
            <div class="content">
                <h2>添加新设备</h2>
                <form method="post">
                    <div class="form-group">
                        <label for="name">设备名称:</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="ip_address">IP地址:</label>
                        <input type="text" id="ip_address" name="ip_address" required>
                    </div>
                    <div class="form-group">
                        <label for="hostname">主机名:</label>
                        <input type="text" id="hostname" name="hostname">
                    </div>
                    <div class="form-group">
                        <label for="device_type">设备类型:</label>
                        <select id="device_type" name="device_type">
                            <option value="cisco">Cisco</option>
                            <option value="huawei">Huawei</option>
                            <option value="juniper">Juniper</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="connection_type">连接类型:</label>
                        <select id="connection_type" name="connection_type">
                            <option value="ssh">SSH</option>
                            <option value="telnet">Telnet</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="port">端口:</label>
                        <input type="number" id="port" name="port" value="22">
                    </div>
                    <div class="form-group">
                        <label for="username">用户名:</label>
                        <input type="text" id="username" name="username">
                    </div>
                    <div class="form-group">
                        <label for="password">密码:</label>
                        <input type="password" id="password" name="password">
                    </div>
                    <div class="form-group">
                        <label for="description">描述:</label>
                        <textarea id="description" name="description" rows="3"></textarea>
                    </div>
                    <button type="submit">添加设备</button>
                    <a href="/devices" class="btn btn-secondary">取消</a>
                </form>
            </div>
        </body>
        </html>
        '''
    
    with app.app_context():
        db.create_all()
        
        # 创建测试用户
        test_user = User(
            username='admin',
            email='admin@example.com'
        )
        test_user.set_password('admin123')
        db.session.add(test_user)
        
        # 创建测试设备
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
    
    yield app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

def test_app_creation(app):
    """测试应用创建"""
    assert app is not None
    assert app.config['TESTING'] == True

def test_home_page_redirect(client):
    """测试主页重定向到登录"""
    response = client.get('/')
    assert response.status_code == 302
    assert response.location == '/login'

def test_login_page(client):
    """测试登录页面"""
    response = client.get('/login')
    assert response.status_code == 200
    assert 'NetManagerX 登录' in response.get_data(as_text=True)
    assert '用户名' in response.get_data(as_text=True)
    assert '密码' in response.get_data(as_text=True)

def test_login_success(client):
    """测试登录成功"""
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    assert response.status_code == 302
    assert response.location == '/'

def test_login_failure(client):
    """测试登录失败"""
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpass'
    })
    assert response.status_code == 200
    assert '用户名或密码错误' in response.get_data(as_text=True)

def test_dashboard_after_login(client):
    """测试登录后的仪表板"""
    # 先登录
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    
    # 访问仪表板
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert 'NetManagerX 网络配置管理系统' in response.get_data(as_text=True)
    assert '欢迎，admin！' in response.get_data(as_text=True)

def test_devices_page(client):
    """测试设备管理页面"""
    # 先登录
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    
    # 访问设备页面
    response = client.get('/devices')
    assert response.status_code == 200
    assert '设备管理' in response.get_data(as_text=True)
    assert '测试路由器' in response.get_data(as_text=True)

def test_add_device_page(client):
    """测试添加设备页面"""
    # 先登录
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    
    # 访问添加设备页面
    response = client.get('/devices/add')
    assert response.status_code == 200
    assert '添加新设备' in response.get_data(as_text=True)
    assert '设备名称' in response.get_data(as_text=True)

def test_add_device_success(client):
    """测试添加设备成功"""
    # 先登录
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    
    # 添加设备
    response = client.post('/devices/add', data={
        'name': '新设备',
        'ip_address': '192.168.1.2',
        'hostname': 'new-device',
        'device_type': 'cisco',
        'connection_type': 'ssh',
        'port': 22,
        'username': 'admin',
        'password': 'password',
        'description': '新添加的设备'
    })
    assert response.status_code == 302
    assert response.location == '/devices'

def test_api_devices(client):
    """测试设备API"""
    # 先登录
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    
    # 访问设备API
    response = client.get('/api/devices')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 1
    assert data[0]['name'] == '测试路由器'
    assert data[0]['ip_address'] == '192.168.1.1'

def test_logout(client):
    """测试退出登录"""
    # 先登录
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    
    # 退出登录
    response = client.get('/logout')
    assert response.status_code == 302
    assert response.location == '/login'

def test_protected_route_redirect(client):
    """测试受保护路由重定向"""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert response.location == '/login'

def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'OK'
    assert 'NetManagerX' in data['message']

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
