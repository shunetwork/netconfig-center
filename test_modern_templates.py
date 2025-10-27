#!/usr/bin/env python3
"""
测试现代化模板的测试用例
"""

import pytest
import os
import tempfile
from flask import Flask, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required
from werkzeug.security import generate_password_hash, check_password_hash

# 创建测试应用
@pytest.fixture
def app():
    """创建测试应用"""
    app = Flask(__name__, template_folder='templates')
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # 简化的用户模型
    class User(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(120), nullable=False)
        is_active = db.Column(db.Boolean, default=True)
        
        def set_password(self, password):
            self.password_hash = generate_password_hash(password)
        
        def check_password(self, password):
            return check_password_hash(self.password_hash, password)
    
    # 简化的设备模型
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
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 路由定义
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('login'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        from flask_login import current_user, login_user
        from flask import flash, render_template
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=True)
                flash(f'欢迎回来，{user.username}！', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('用户名或密码错误', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        from flask_login import logout_user
        from flask import flash
        logout_user()
        flash('您已退出登录。', 'info')
        return redirect(url_for('login'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        from flask_login import current_user
        from flask import render_template
        devices = Device.query.filter_by(is_active=True).all()
        return render_template('dashboard.html', devices=devices)
    
    @app.route('/devices')
    @login_required
    def devices():
        from flask_login import current_user
        from flask import render_template
        devices = Device.query.filter_by(is_active=True).all()
        return render_template('devices.html', devices=devices)
    
    @app.route('/devices/add', methods=['GET', 'POST'])
    @login_required
    def add_device():
        from flask_login import current_user
        from flask import flash, render_template
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
            flash('设备添加成功！', 'success')
            return redirect(url_for('devices'))
        
        return render_template('add_device.html')
    
    @app.route('/health')
    def health_check():
        from flask import jsonify
        return jsonify({"status": "OK", "message": "NetManagerX is running"})
    
    # 初始化数据库
    with app.app_context():
        db.create_all()
        
        # 创建测试用户
        test_user = User(
            username='testuser',
            email='test@example.com'
        )
        test_user.set_password('testpass')
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
    
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

def test_app_creation(app):
    """测试应用创建"""
    assert app is not None
    assert app.config['TESTING'] == True

def test_home_page_redirect(client):
    """测试主页重定向"""
    response = client.get('/')
    assert response.status_code == 302
    assert response.location == '/login'

def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'OK', 'message': 'NetManagerX is running'}

def test_login_page(client):
    """测试登录页面"""
    response = client.get('/login')
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'NetManagerX' in content
    assert '登录' in content
    assert 'bootstrap' in content.lower()  # 检查是否加载了Bootstrap

def test_login_success(client):
    """测试登录成功"""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    assert response.status_code == 302
    assert response.location == '/dashboard'

def test_login_failure(client):
    """测试登录失败"""
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpass'
    })
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert '用户名或密码错误' in content

def test_dashboard_requires_login(client):
    """测试仪表板需要登录"""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert response.location.startswith('/login')

def test_dashboard_with_login(client):
    """测试登录后的仪表板"""
    # 先登录
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    # 访问仪表板
    response = client.get('/dashboard')
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'NetManagerX' in content
    assert '仪表板' in content
    assert 'bootstrap' in content.lower()  # 检查是否加载了Bootstrap

def test_devices_page_with_login(client):
    """测试设备页面"""
    # 先登录
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    # 访问设备页面
    response = client.get('/devices')
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert '设备管理' in content
    assert '测试路由器' in content

def test_add_device_page_with_login(client):
    """测试添加设备页面"""
    # 先登录
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    # 访问添加设备页面
    response = client.get('/devices/add')
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert '添加设备' in content

def test_logout(client):
    """测试退出登录"""
    # 先登录
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    # 退出登录
    response = client.get('/logout')
    assert response.status_code == 302
    assert response.location == '/login'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
