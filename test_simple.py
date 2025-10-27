#!/usr/bin/env python3
"""
NetManagerX简化测试
测试基本功能
"""

import pytest
import os
import tempfile
from flask import Flask, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 创建测试应用
@pytest.fixture
def app():
    """创建测试应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # 简单的用户模型
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
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 简单的路由
    @app.route('/')
    def index():
        return '<h1>NetManagerX</h1><p>系统运行正常</p>'
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        from flask_login import login_user
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('index'))
            return '登录失败'
        return '''
        <form method="post">
            <input type="text" name="username" placeholder="用户名" required>
            <input type="password" name="password" placeholder="密码" required>
            <button type="submit">登录</button>
        </form>
        '''
    
    @app.route('/health')
    def health():
        return {'status': 'OK', 'message': 'NetManagerX is running'}
    
    with app.app_context():
        db.create_all()
        
        # 创建测试用户
        test_user = User(
            username='testuser',
            email='test@example.com'
        )
        test_user.set_password('testpass')
        db.session.add(test_user)
        db.session.commit()
    
    yield app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def sample_user(app):
    """创建示例用户"""
    from flask_login import login_user
    with app.app_context():
        user = app.User.query.filter_by(username='testuser').first()
        return user

def test_app_creation(app):
    """测试应用创建"""
    assert app is not None
    assert app.config['TESTING'] == True

def test_database_creation(app):
    """测试数据库创建"""
    with app.app_context():
        # 检查用户表是否存在
        result = db.engine.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        assert result.fetchone() is not None

def test_home_page(client):
    """测试主页"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'NetManagerX' in response.get_data(as_text=True)

def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'OK'
    assert 'NetManagerX' in data['message']

def test_login_page(client):
    """测试登录页面"""
    response = client.get('/login')
    assert response.status_code == 200
    assert '用户名' in response.get_data(as_text=True)
    assert '密码' in response.get_data(as_text=True)

def test_login_success(client, app):
    """测试登录成功"""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    # 登录成功会重定向到主页，状态码是302
    assert response.status_code == 302
    # 检查重定向位置
    assert response.location == '/'

def test_login_failure(client):
    """测试登录失败"""
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpass'
    })
    assert response.status_code == 200
    assert '登录失败' in response.get_data(as_text=True)

def test_user_model(app):
    """测试用户模型"""
    with app.app_context():
        # 获取User模型
        User = app.User
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass')
        assert not user.check_password('wrongpass')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
