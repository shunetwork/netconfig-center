"""
认证模块测试用例
测试用户认证、权限管理、登录登出等功能
"""

import pytest
from flask import url_for
from flask_login import current_user
from app import create_app, db
from app.models import User, Role

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
def sample_role(app):
    """创建测试角色"""
    with app.app_context():
        role = Role(name='test_role', description='测试角色')
        role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE)
        db.session.add(role)
        db.session.commit()
        return role

@pytest.fixture
def sample_user(app, sample_role):
    """创建测试用户"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            role=sample_role
        )
        user.password = 'testpass123'
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def admin_user(app):
    """创建管理员用户"""
    with app.app_context():
        User.create_default_roles()
        admin_user = User.create_admin_user()
        return admin_user

class TestAuthRoutes:
    """认证路由测试"""
    
    def test_login_page_loads(self, client):
        """测试登录页面加载"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert '登录' in response.get_data(as_text=True)
        assert '用户名' in response.get_data(as_text=True)
        assert '密码' in response.get_data(as_text=True)
    
    def test_login_success(self, client, sample_user):
        """测试登录成功"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123',
            'remember_me': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '欢迎回来' in response.get_data(as_text=True) or '仪表板' in response.get_data(as_text=True)
    
    def test_login_failure_wrong_password(self, client, sample_user):
        """测试登录失败 - 密码错误"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword',
            'remember_me': False
        })
        
        assert response.status_code == 200
        assert '用户名或密码错误' in response.get_data(as_text=True)
    
    def test_login_failure_wrong_username(self, client, sample_user):
        """测试登录失败 - 用户名错误"""
        response = client.post('/auth/login', data={
            'username': 'wronguser',
            'password': 'testpass123',
            'remember_me': False
        })
        
        assert response.status_code == 200
        assert '用户名或密码错误' in response.get_data(as_text=True)
    
    def test_login_empty_fields(self, client):
        """测试登录 - 空字段"""
        response = client.post('/auth/login', data={
            'username': '',
            'password': '',
            'remember_me': False
        })
        
        assert response.status_code == 200
        assert '请输入用户名和密码' in response.get_data(as_text=True)
    
    def test_login_inactive_user(self, client, sample_user):
        """测试登录 - 未激活用户"""
        sample_user.is_active = False
        db.session.commit()
        
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123',
            'remember_me': False
        })
        
        assert response.status_code == 200
        assert '用户名或密码错误' in response.get_data(as_text=True)
    
    def test_logout(self, client, sample_user):
        """测试登出"""
        # 先登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 登出
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert '您已成功登出' in response.get_data(as_text=True)
    
    def test_login_redirect_after_login(self, client, sample_user):
        """测试登录后重定向"""
        # 访问需要登录的页面
        response = client.get('/auth/profile', follow_redirects=True)
        assert response.status_code == 200
        assert '登录' in response.get_data(as_text=True)  # 应该重定向到登录页面
        
        # 登录后应该重定向到原来的页面
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        assert response.status_code == 200

class TestUserPermissions:
    """用户权限测试"""
    
    def test_user_permissions(self, app, sample_role):
        """测试用户权限"""
        with app.app_context():
            # 创建具有不同权限的用户
            viewer_role = Role(name='viewer')
            viewer_role.add_permission(Role.PERMISSION_VIEW)
            
            operator_role = Role(name='operator')
            operator_role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE)
            
            admin_role = Role(name='admin')
            admin_role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE | 
                                    Role.PERMISSION_CONFIGURE | Role.PERMISSION_ADMIN)
            
            db.session.add_all([viewer_role, operator_role, admin_role])
            
            viewer_user = User(username='viewer', email='viewer@test.com', role=viewer_role)
            viewer_user.password = 'testpass'
            
            operator_user = User(username='operator', email='operator@test.com', role=operator_role)
            operator_user.password = 'testpass'
            
            admin_user = User(username='admin_user', email='admin@test.com', role=admin_role)
            admin_user.password = 'testpass'
            
            db.session.add_all([viewer_user, operator_user, admin_user])
            db.session.commit()
            
            # 测试权限
            assert viewer_user.can_view()
            assert not viewer_user.can_execute()
            assert not viewer_user.can_configure()
            assert not viewer_user.is_admin
            
            assert operator_user.can_view()
            assert operator_user.can_execute()
            assert not operator_user.can_configure()
            assert not operator_user.is_admin
            
            assert admin_user.can_view()
            assert admin_user.can_execute()
            assert admin_user.can_configure()
            assert admin_user.is_admin

class TestPasswordSecurity:
    """密码安全测试"""
    
    def test_password_hashing(self, app, sample_role):
        """测试密码加密"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                role=sample_role
            )
            user.password = 'testpass123'
            
            assert user.password_hash is not None
            assert user.password_hash != 'testpass123'
            assert user.verify_password('testpass123')
            assert not user.verify_password('wrongpass')
    
    def test_password_change(self, client, sample_user):
        """测试密码修改"""
        # 先登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 修改密码
        response = client.post('/auth/change-password', data={
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '密码修改成功' in response.get_data(as_text=True)
        
        # 登出
        client.get('/auth/logout')
        
        # 用新密码登录
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'newpass123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '欢迎回来' in response.get_data(as_text=True) or '仪表板' in response.get_data(as_text=True)
    
    def test_password_change_wrong_current_password(self, client, sample_user):
        """测试密码修改 - 当前密码错误"""
        # 先登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 修改密码 - 当前密码错误
        response = client.post('/auth/change-password', data={
            'current_password': 'wrongpass',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        })
        
        assert response.status_code == 200
        assert '当前密码错误' in response.get_data(as_text=True)
    
    def test_password_change_mismatch(self, client, sample_user):
        """测试密码修改 - 新密码不匹配"""
        # 先登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 修改密码 - 新密码不匹配
        response = client.post('/auth/change-password', data={
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'confirm_password': 'differentpass'
        })
        
        assert response.status_code == 200
        assert '新密码和确认密码不匹配' in response.get_data(as_text=True)

class TestProtectedRoutes:
    """受保护路由测试"""
    
    def test_protected_route_redirect(self, client):
        """测试受保护路由重定向到登录页面"""
        response = client.get('/auth/profile', follow_redirects=True)
        assert response.status_code == 200
        assert '登录' in response.data
    
    def test_protected_route_with_login(self, client, sample_user):
        """测试登录后访问受保护路由"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 访问受保护路由
        response = client.get('/auth/profile')
        assert response.status_code == 200

class TestUserProfile:
    """用户资料测试"""
    
    def test_user_profile_page(self, client, sample_user):
        """测试用户资料页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 访问资料页面
        response = client.get('/auth/profile')
        assert response.status_code == 200
        assert b'testuser' in response.data
        assert b'test@example.com' in response.data

class TestAuditLogging:
    """审计日志测试"""
    
    def test_login_audit_log(self, app, sample_user):
        """测试登录审计日志"""
        with app.app_context():
            from app.models import AuditLog
            
            # 模拟登录
            with app.test_client() as client:
                response = client.post('/auth/login', data={
                    'username': 'testuser',
                    'password': 'testpass123'
                })
                
                # 检查审计日志
                logs = AuditLog.query.filter_by(action='login').all()
                assert len(logs) > 0
                
                login_log = logs[0]
                assert login_log.user == sample_user
                assert login_log.success == True
    
    def test_logout_audit_log(self, app, sample_user):
        """测试登出审计日志"""
        with app.app_context():
            from app.models import AuditLog
            
            # 模拟登录和登出
            with app.test_client() as client:
                # 登录
                client.post('/auth/login', data={
                    'username': 'testuser',
                    'password': 'testpass123'
                })
                
                # 登出
                client.get('/auth/logout')
                
                # 检查审计日志
                logout_logs = AuditLog.query.filter_by(action='logout').all()
                assert len(logout_logs) > 0
                
                logout_log = logout_logs[0]
                assert logout_log.user == sample_user
                assert logout_log.success == True
