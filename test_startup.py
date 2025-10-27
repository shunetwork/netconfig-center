#!/usr/bin/env python3
"""
NetManagerX启动测试
测试完整的应用启动流程
"""

import pytest
import os
import tempfile
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

def test_database_initialization():
    """测试数据库初始化流程"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    # 用户模型
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
    
    with app.app_context():
        # 创建数据库
        db.create_all()
        
        # 第一次创建用户 - 应该成功
        user1 = User(
            username='admin',
            email='admin@example.com'
        )
        user1.set_password('admin123')
        db.session.add(user1)
        db.session.commit()
        
        # 验证用户已创建
        assert User.query.count() == 1
        assert User.query.filter_by(username='admin').first() is not None
        
        # 尝试创建重复用户 - 应该失败
        try:
            user2 = User(
                username='admin2',
                email='admin@example.com'  # 相同的email
            )
            user2.set_password('admin123')
            db.session.add(user2)
            db.session.commit()
            assert False, "应该抛出唯一性约束错误"
        except Exception as e:
            # 应该捕获到唯一性约束错误
            assert 'UNIQUE constraint failed' in str(e) or 'IntegrityError' in str(e)
            db.session.rollback()
        
        # 验证只有一个用户
        assert User.query.count() == 1

def test_duplicate_user_handling():
    """测试重复用户处理"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    
    class User(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(120), nullable=False)
        is_active = db.Column(db.Boolean, default=True)
        
        def set_password(self, password):
            self.password_hash = generate_password_hash(password)
    
    with app.app_context():
        db.create_all()
        
        # 创建第一个用户
        user1 = User(
            username='admin',
            email='admin@example.com'
        )
        user1.set_password('admin123')
        db.session.add(user1)
        db.session.commit()
        
        # 检查用户是否已存在
        existing_user = User.query.filter_by(username='admin').first()
        if existing_user:
            print("用户已存在，跳过创建")
        else:
            # 只有在用户不存在时才创建
            new_user = User(
                username='admin',
                email='admin@example.com'
            )
            new_user.set_password('admin123')
            db.session.add(new_user)
            db.session.commit()
        
        # 验证只有一个用户
        assert User.query.count() == 1

def test_startup_with_existing_database():
    """测试使用已存在数据库的启动流程"""
    # 创建临时数据库文件
    db_fd, db_path = tempfile.mkstemp()
    
    try:
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db = SQLAlchemy(app)
        
        class User(UserMixin, db.Model):
            id = db.Column(db.Integer, primary_key=True)
            username = db.Column(db.String(80), unique=True, nullable=False)
            email = db.Column(db.String(120), unique=True, nullable=False)
            password_hash = db.Column(db.String(120), nullable=False)
            is_active = db.Column(db.Boolean, default=True)
            
            def set_password(self, password):
                self.password_hash = generate_password_hash(password)
        
        with app.app_context():
            # 第一次启动 - 创建数据库和用户
            db.create_all()
            
            user1 = User(
                username='admin',
                email='admin@example.com'
            )
            user1.set_password('admin123')
            db.session.add(user1)
            db.session.commit()
            
            # 验证用户已创建
            assert User.query.count() == 1
        
        # 模拟第二次启动 - 应该检测到用户已存在
        with app.app_context():
            # 检查用户是否已存在
            existing_user = User.query.filter_by(username='admin').first()
            assert existing_user is not None
            assert existing_user.username == 'admin'
            
            # 尝试创建重复用户应该被阻止
            try:
                user2 = User(
                    username='admin',
                    email='admin@example.com'
                )
                user2.set_password('admin123')
                db.session.add(user2)
                db.session.commit()
                assert False, "应该检测到重复用户"
            except Exception as e:
                # 应该捕获到唯一性约束错误
                assert 'UNIQUE constraint failed' in str(e) or 'IntegrityError' in str(e)
                db.session.rollback()
            
            # 验证仍然只有一个用户
            assert User.query.count() == 1
    
    finally:
        os.close(db_fd)
        os.unlink(db_path)

def test_application_startup_flow():
    """测试应用启动流程"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    
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
    
    # 模拟启动流程
    with app.app_context():
        # 1. 创建数据库
        db.create_all()
        
        # 2. 检查是否需要初始化
        if User.query.count() == 0:
            # 3. 创建默认用户
            admin_user = User(
                username='admin',
                email='admin@example.com'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("默认用户已创建")
        else:
            print("用户已存在，跳过创建")
        
        # 4. 验证启动成功
        assert User.query.count() == 1
        user = User.query.filter_by(username='admin').first()
        assert user is not None
        assert user.check_password('admin123')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
