"""
用户模块测试用例
测试用户认证、权限管理等功能
"""

import pytest
import tempfile
import os
from app import create_app, db
from app.models.user import User, Role

@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """创建测试运行器"""
    return app.test_cli_runner()

class TestUserModel:
    """用户模型测试"""
    
    def test_user_creation(self, app):
        """测试用户创建"""
        with app.app_context():
            # 创建测试角色
            role = Role(name='test_role', description='测试角色')
            role.add_permission(Role.PERMISSION_VIEW)
            db.session.add(role)
            db.session.commit()
            
            # 创建测试用户
            user = User(
                username='testuser',
                email='test@example.com',
                role=role
            )
            user.password = 'testpass123'
            db.session.add(user)
            db.session.commit()
            
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.verify_password('testpass123')
            assert not user.verify_password('wrongpass')
    
    def test_password_hashing(self, app):
        """测试密码加密"""
        with app.app_context():
            role = Role(name='test_role')
            db.session.add(role)
            db.session.commit()
            
            user = User(username='testuser', email='test@example.com', role=role)
            user.password = 'testpass123'
            
            assert user.password_hash is not None
            assert user.password_hash != 'testpass123'
    
    def test_permissions(self, app):
        """测试权限管理"""
        with app.app_context():
            # 创建角色并设置权限
            admin_role = Role(name='admin')
            admin_role.add_permission(Role.PERMISSION_ADMIN)
            db.session.add(admin_role)
            
            user_role = Role(name='user')
            user_role.add_permission(Role.PERMISSION_VIEW)
            db.session.add(user_role)
            
            db.session.commit()
            
            # 创建管理员用户
            admin_user = User(username='admin', email='admin@test.com', role=admin_role)
            admin_user.password = 'adminpass'
            db.session.add(admin_user)
            
            # 创建普通用户
            user = User(username='user', email='user@test.com', role=user_role)
            user.password = 'userpass'
            db.session.add(user)
            
            db.session.commit()
            
            # 测试权限检查
            assert admin_user.has_permission(Role.PERMISSION_ADMIN)
            assert admin_user.can_view()
            assert not user.has_permission(Role.PERMISSION_ADMIN)
            assert user.can_view()
    
    def test_default_roles_creation(self, app):
        """测试默认角色创建"""
        with app.app_context():
            User.create_default_roles()
            
            # 检查默认角色是否创建
            admin_role = Role.query.filter_by(name='admin').first()
            operator_role = Role.query.filter_by(name='operator').first()
            viewer_role = Role.query.filter_by(name='viewer').first()
            
            assert admin_role is not None
            assert operator_role is not None
            assert viewer_role is not None
            
            # 检查权限设置
            assert admin_role.has_permission(Role.PERMISSION_ADMIN)
            assert operator_role.has_permission(Role.PERMISSION_EXECUTE)
            assert viewer_role.has_permission(Role.PERMISSION_VIEW)

class TestUserAPI:
    """用户API测试"""
    
    def test_user_registration(self, client):
        """测试用户注册"""
        # 这里需要实现用户注册API后进行测试
        pass
    
    def test_user_login(self, client):
        """测试用户登录"""
        # 这里需要实现用户登录API后进行测试
        pass
    
    def test_user_profile(self, client):
        """测试用户资料查看"""
        # 这里需要实现用户资料API后进行测试
        pass

class TestUserSecurity:
    """用户安全测试"""
    
    def test_password_strength(self, app):
        """测试密码强度"""
        with app.app_context():
            role = Role(name='test_role')
            db.session.add(role)
            db.session.commit()
            
            # 测试弱密码
            user = User(username='testuser', email='test@example.com', role=role)
            user.password = '123'  # 弱密码
            
            # 应该能设置，但在实际应用中应该有验证
            assert user.password_hash is not None
    
    def test_user_activation(self, app):
        """测试用户激活状态"""
        with app.app_context():
            role = Role(name='test_role')
            db.session.add(role)
            db.session.commit()
            
            user = User(username='testuser', email='test@example.com', role=role)
            user.password = 'testpass123'
            user.is_active = False
            db.session.add(user)
            db.session.commit()
            
            assert not user.is_active
