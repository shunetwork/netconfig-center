"""
集成测试用例
测试模块间的集成功能和端到端流程
"""

import pytest
import json
from flask import url_for
from app import create_app, db
from app.models import User, Role, Device, DeviceGroup, ConfigTemplate, Task, AuditLog

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
def sample_user(app):
    """创建测试用户"""
    with app.app_context():
        role = Role(name='admin', description='管理员')
        role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE | Role.PERMISSION_CONFIGURE | Role.PERMISSION_ADMIN)
        db.session.add(role)
        
        user = User(
            username='admin',
            email='admin@example.com',
            role=role
        )
        user.password = 'admin123'
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def sample_device(app, sample_user):
    """创建测试设备"""
    with app.app_context():
        device = Device(
            name='test_device',
            ip_address='192.168.1.1',
            device_type='cisco_switch',
            connection_type='ssh',
            port=22,
            username='admin'
        )
        device.set_password('admin123')
        db.session.add(device)
        db.session.commit()
        return device

@pytest.fixture
def sample_template(app):
    """创建测试模板"""
    with app.app_context():
        template = ConfigTemplate(
            name='test_template',
            description='测试模板',
            category='basic',
            template_content='hostname {{ hostname }}\ninterface {{ interface_name }}'
        )
        db.session.add(template)
        db.session.commit()
        return template

class TestUserWorkflow:
    """用户工作流程测试"""
    
    def test_user_login_workflow(self, client, sample_user):
        """测试用户登录工作流程"""
        # 访问首页，应该重定向到登录页面
        response = client.get('/')
        assert response.status_code == 302
        
        # 访问登录页面
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'登录' in response.data
        
        # 登录
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'欢迎回来' in response.data or b'仪表板' in response.data
    
    def test_user_logout_workflow(self, client, sample_user):
        """测试用户登出工作流程"""
        # 先登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 登出
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'您已成功登出' in response.data

class TestDeviceManagementWorkflow:
    """设备管理工作流程测试"""
    
    def test_device_crud_workflow(self, client, sample_user):
        """测试设备CRUD工作流程"""
        # 登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 访问设备列表页面
        response = client.get('/devices/')
        assert response.status_code == 200
        assert b'设备管理' in response.data
        
        # 访问添加设备页面
        response = client.get('/devices/add')
        assert response.status_code == 200
        assert b'添加设备' in response.data
        
        # 添加设备
        response = client.post('/devices/add', data={
            'name': 'new_device',
            'ip_address': '192.168.1.100',
            'device_type': 'cisco_switch',
            'connection_type': 'ssh',
            'port': 22,
            'username': 'admin',
            'password': 'admin123'
        })
        
        assert response.status_code == 302  # 重定向到设备详情页
        
        # 验证设备已创建
        device = Device.query.filter_by(name='new_device').first()
        assert device is not None
        assert device.ip_address == '192.168.1.100'
    
    def test_device_connection_test_workflow(self, client, sample_user, sample_device):
        """测试设备连接测试工作流程"""
        # 登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 测试设备连接（需要mock SSH服务）
        with client.session_transaction() as sess:
            sess['_user_id'] = str(sample_user.id)
        
        # 这里需要mock SSH连接测试
        response = client.post(f'/devices/{sample_device.id}/test-connection')
        # 由于没有实际的SSH连接，这里可能会返回错误，但至少应该能处理请求
        assert response.status_code in [200, 500]

class TestTemplateManagementWorkflow:
    """模板管理工作流程测试"""
    
    def test_template_crud_workflow(self, client, sample_user):
        """测试模板CRUD工作流程"""
        # 登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 访问模板列表页面
        response = client.get('/templates/')
        assert response.status_code == 200
        assert b'配置模板' in response.data
        
        # 访问添加模板页面
        response = client.get('/templates/add')
        assert response.status_code == 200
        assert b'添加模板' in response.data
        
        # 添加模板
        response = client.post('/templates/add', data={
            'name': 'new_template',
            'description': '新模板',
            'category': 'basic',
            'template_content': 'hostname {{ hostname }}',
            'version': '1.0'
        })
        
        assert response.status_code == 302  # 重定向到模板详情页
        
        # 验证模板已创建
        template = ConfigTemplate.query.filter_by(name='new_template').first()
        assert template is not None
        assert template.category == 'basic'
    
    def test_template_render_workflow(self, client, sample_user, sample_template):
        """测试模板渲染工作流程"""
        # 登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 测试模板渲染API
        variables = {
            'hostname': 'test-switch',
            'interface_name': 'GigabitEthernet0/1'
        }
        
        response = client.post(f'/templates/api/template/{sample_template.id}/render', 
                             json={'variables': variables})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert 'hostname test-switch' in data['rendered_content']

class TestTaskExecutionWorkflow:
    """任务执行工作流程测试"""
    
    def test_task_creation_workflow(self, client, sample_user, sample_device):
        """测试任务创建工作流程"""
        # 登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 访问任务列表页面
        response = client.get('/tasks/')
        assert response.status_code == 200
        assert b'任务管理' in response.data
        
        # 访问创建任务页面
        response = client.get('/tasks/create')
        assert response.status_code == 200
        assert b'创建任务' in response.data
        
        # 创建任务
        task_data = {
            'name': 'test_task',
            'description': '测试任务',
            'task_type': 'command',
            'device_id': sample_device.id,
            'command': 'show version'
        }
        
        response = client.post('/tasks/create', json=task_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] == True
        assert data['task_id'] is not None
        
        # 验证任务已创建
        task = Task.query.get(data['task_id'])
        assert task is not None
        assert task.name == 'test_task'
        assert task.device == sample_device
    
    def test_task_status_workflow(self, client, sample_user, sample_device):
        """测试任务状态查询工作流程"""
        # 登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 创建任务
        task = Task(
            name='status_test_task',
            task_type='command',
            command='show version',
            user=sample_user,
            device=sample_device
        )
        db.session.add(task)
        db.session.commit()
        
        # 查询任务状态
        response = client.get(f'/tasks/api/task/{task.id}/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['task_id'] == task.id
        assert 'status' in data
        assert 'started_at' in data
        assert 'completed_at' in data

class TestAuditLogWorkflow:
    """审计日志工作流程测试"""
    
    def test_audit_log_creation_workflow(self, client, sample_user, sample_device):
        """测试审计日志创建工作流程"""
        # 登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 执行一些操作来生成审计日志
        response = client.post(f'/devices/{sample_device.id}/test-connection')
        
        # 验证审计日志已创建
        logs = AuditLog.query.filter_by(user_id=sample_user.id).all()
        assert len(logs) > 0
        
        # 检查最新的日志
        latest_log = logs[-1]
        assert latest_log.user == sample_user
        assert latest_log.action in ['test_device_connection', 'login']

class TestAPIIntegration:
    """API集成测试"""
    
    def test_api_authentication_workflow(self, client, sample_user):
        """测试API认证工作流程"""
        # 未认证的API请求应该被拒绝
        response = client.get('/api/stats')
        assert response.status_code == 302  # 重定向到登录页面
        
        # 登录后API请求应该成功
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        response = client.get('/api/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'devices' in data
        assert 'tasks' in data
    
    def test_api_error_handling_workflow(self, client, sample_user):
        """测试API错误处理工作流程"""
        # 登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 测试不存在的资源
        response = client.get('/devices/99999')
        assert response.status_code == 404
        
        response = client.get('/templates/99999')
        assert response.status_code == 404
        
        response = client.get('/tasks/99999')
        assert response.status_code == 404

class TestDatabaseIntegration:
    """数据库集成测试"""
    
    def test_database_transaction_workflow(self, app, sample_user):
        """测试数据库事务工作流程"""
        with app.app_context():
            # 测试事务回滚
            try:
                device = Device(
                    name='test_device',
                    ip_address='192.168.1.1',
                    device_type='cisco_switch',
                    connection_type='ssh',
                    username='admin'
                )
                device.set_password('admin123')
                db.session.add(device)
                
                # 故意创建一个无效的任务来触发回滚
                task = Task(
                    name='',  # 空名称应该导致验证失败
                    task_type='command',
                    user=sample_user
                )
                db.session.add(task)
                db.session.commit()
                
                assert False, "应该抛出异常"
                
            except Exception:
                db.session.rollback()
                
                # 验证数据已回滚
                device = Device.query.filter_by(name='test_device').first()
                assert device is None
    
    def test_database_relationship_workflow(self, app, sample_user):
        """测试数据库关系工作流程"""
        with app.app_context():
            # 创建设备组
            group = DeviceGroup(name='test_group', description='测试组')
            db.session.add(group)
            db.session.commit()
            
            # 创建设备
            device = Device(
                name='test_device',
                ip_address='192.168.1.1',
                device_type='cisco_switch',
                connection_type='ssh',
                username='admin',
                group=group
            )
            device.set_password('admin123')
            db.session.add(device)
            db.session.commit()
            
            # 创建任务
            task = Task(
                name='test_task',
                task_type='command',
                command='show version',
                user=sample_user,
                device=device
            )
            db.session.add(task)
            db.session.commit()
            
            # 验证关系
            assert device.group == group
            assert task.device == device
            assert task.user == sample_user
            assert device in group.devices.all()
            assert task in device.tasks.all()
            assert task in sample_user.tasks.all()

class TestEndToEndWorkflow:
    """端到端工作流程测试"""
    
    def test_complete_device_management_workflow(self, client, sample_user):
        """测试完整的设备管理工作流程"""
        # 1. 用户登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 2. 创建设备组
        response = client.post('/devices/groups/add', data={
            'name': 'test_group',
            'description': '测试组'
        })
        assert response.status_code == 302
        
        group = DeviceGroup.query.filter_by(name='test_group').first()
        assert group is not None
        
        # 3. 添加设备
        response = client.post('/devices/add', data={
            'name': 'test_device',
            'ip_address': '192.168.1.1',
            'device_type': 'cisco_switch',
            'connection_type': 'ssh',
            'port': 22,
            'username': 'admin',
            'password': 'admin123',
            'group_id': group.id
        })
        assert response.status_code == 302
        
        device = Device.query.filter_by(name='test_device').first()
        assert device is not None
        assert device.group == group
        
        # 4. 测试设备连接
        response = client.post(f'/devices/{device.id}/test-connection')
        # 这里可能会失败，因为没有实际的SSH连接，但至少应该能处理请求
        
        # 5. 查看设备详情
        response = client.get(f'/devices/{device.id}')
        assert response.status_code == 200
        assert b'test_device' in response.data
    
    def test_complete_template_workflow(self, client, sample_user, sample_device):
        """测试完整的模板工作流程"""
        # 1. 用户登录
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 2. 创建模板
        response = client.post('/templates/add', data={
            'name': 'interface_template',
            'description': '接口配置模板',
            'category': 'interface',
            'template_content': 'interface {{ interface_name }}\ndescription {{ description }}',
            'version': '1.0'
        })
        assert response.status_code == 302
        
        template = ConfigTemplate.query.filter_by(name='interface_template').first()
        assert template is not None
        
        # 3. 渲染模板
        variables = {
            'interface_name': 'GigabitEthernet0/1',
            'description': 'Test Interface'
        }
        
        response = client.post(f'/templates/api/template/{template.id}/render', 
                             json={'variables': variables})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] == True
        assert 'interface GigabitEthernet0/1' in data['rendered_content']
        
        # 4. 创建任务应用模板
        task_data = {
            'name': 'apply_template_task',
            'description': '应用模板任务',
            'task_type': 'config_template',
            'device_id': sample_device.id,
            'template_id': template.id,
            'template_variables': variables
        }
        
        response = client.post('/tasks/create', json=task_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] == True
        
        task = Task.query.get(data['task_id'])
        assert task is not None
        assert task.template == template
        assert task.device == sample_device
