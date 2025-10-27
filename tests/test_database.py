"""
数据库模型测试用例
测试所有数据模型的创建、关联和基本功能
"""

import pytest
from app import create_app, db
from app.models import (
    User, Role, Device, DeviceGroup, DeviceConnection,
    ConfigTemplate, TemplateVariable, TemplateCategory,
    Task, TaskResult, AuditLog, ConfigBackup
)

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
def sample_device_group(app):
    """创建测试设备组"""
    with app.app_context():
        group = DeviceGroup(name='test_group', description='测试设备组')
        db.session.add(group)
        db.session.commit()
        return group

@pytest.fixture
def sample_device(app, sample_device_group):
    """创建测试设备"""
    with app.app_context():
        device = Device(
            name='test_device',
            ip_address='192.168.1.1',
            hostname='test-switch',
            username='admin',
            group=sample_device_group
        )
        device.set_password('admin123')
        db.session.add(device)
        db.session.commit()
        return device

class TestDatabaseModels:
    """数据库模型测试"""
    
    def test_user_role_relationship(self, app, sample_role, sample_user):
        """测试用户和角色的关联"""
        with app.app_context():
            assert sample_user.role == sample_role
            assert sample_role.users.count() == 1
            assert sample_role.users.first() == sample_user
    
    def test_device_group_relationship(self, app, sample_device_group, sample_device):
        """测试设备和设备组的关联"""
        with app.app_context():
            assert sample_device.group == sample_device_group
            assert sample_device_group.devices.count() == 1
            assert sample_device_group.devices.first() == sample_device
    
    def test_config_template_variables(self, app):
        """测试配置模板和变量的关联"""
        with app.app_context():
            template = ConfigTemplate(
                name='test_template',
                description='测试模板',
                category='basic',
                template_content='hostname {{ hostname }}'
            )
            db.session.add(template)
            db.session.commit()
            
            # 添加变量
            template.add_variable('hostname', 'string', '设备主机名', 'default-switch', True)
            db.session.commit()
            
            assert template.variables.count() == 1
            variable = template.variables.first()
            assert variable.name == 'hostname'
            assert variable.var_type == 'string'
            assert variable.required == True
    
    def test_template_rendering(self, app):
        """测试模板渲染功能"""
        with app.app_context():
            template = ConfigTemplate(
                name='test_template',
                category='basic',
                template_content='hostname {{ hostname }}\ninterface {{ interface }}'
            )
            db.session.add(template)
            db.session.commit()
            
            # 测试模板渲染
            variables = {'hostname': 'test-switch', 'interface': 'GigabitEthernet0/1'}
            result = template.render_template(variables)
            assert 'hostname test-switch' in result
            assert 'interface GigabitEthernet0/1' in result
    
    def test_template_variable_validation(self, app):
        """测试模板变量验证"""
        with app.app_context():
            template = ConfigTemplate(
                name='test_template',
                category='basic',
                template_content='hostname {{ hostname }}'
            )
            db.session.add(template)
            db.session.commit()
            
            # 添加必需变量
            template.add_variable('hostname', 'string', '设备主机名', '', True)
            db.session.commit()
            
            # 测试缺少必需变量
            errors = template.validate_variables({})
            assert len(errors) > 0
            assert '缺少必需变量' in errors[0]
            
            # 测试提供必需变量
            errors = template.validate_variables({'hostname': 'test-switch'})
            assert len(errors) == 0
    
    def test_task_creation_and_status(self, app, sample_user, sample_device):
        """测试任务创建和状态管理"""
        with app.app_context():
            task = Task(
                name='test_task',
                description='测试任务',
                task_type='command',
                command='show version',
                user=sample_user,
                device=sample_device
            )
            db.session.add(task)
            db.session.commit()
            
            assert task.status.value == 'pending'
            assert task.user == sample_user
            assert task.device == sample_device
            
            # 测试任务状态变更
            task.start()
            assert task.status.value == 'running'
            assert task.started_at is not None
            
            task.complete(success=True, message='任务执行成功')
            assert task.status.value == 'success'
            assert task.completed_at is not None
            assert task.result_message == '任务执行成功'
    
    def test_task_result_creation(self, app, sample_user, sample_device):
        """测试任务结果创建"""
        with app.app_context():
            task = Task(
                name='test_task',
                task_type='command',
                command='show version',
                user=sample_user,
                device=sample_device
            )
            db.session.add(task)
            db.session.commit()
            
            result = TaskResult(
                device_name=sample_device.name,
                device_ip=sample_device.ip_address,
                command='show version',
                output='Cisco IOS Software, Version 15.1(4)M4',
                exit_code=0,
                execution_time=1.5,
                task=task,
                device=sample_device
            )
            db.session.add(result)
            db.session.commit()
            
            assert result.task == task
            assert result.device == sample_device
            assert result.is_success() == True
            assert task.results.count() == 1
    
    def test_audit_log_creation(self, app, sample_user):
        """测试审计日志创建"""
        with app.app_context():
            log = AuditLog(
                user=sample_user,
                action='create_device',
                resource_type='device',
                resource_id=1,
                resource_name='test-device',
                success=True
            )
            log.set_details({'device_type': 'switch', 'ip_address': '192.168.1.1'})
            db.session.add(log)
            db.session.commit()
            
            assert log.user == sample_user
            assert log.action == 'create_device'
            assert log.success == True
            details = log.get_details()
            assert details['device_type'] == 'switch'
            assert details['ip_address'] == '192.168.1.1'
    
    def test_config_backup_creation(self, app, sample_user, sample_device):
        """测试配置备份创建"""
        with app.app_context():
            backup = ConfigBackup(
                name='test_backup',
                description='测试备份',
                config_content='hostname test-switch\ninterface GigabitEthernet0/1',
                user=sample_user,
                device=sample_device
            )
            backup.calculate_hash()
            db.session.add(backup)
            db.session.commit()
            
            assert backup.device == sample_device
            assert backup.user == sample_user
            assert backup.config_hash is not None
            assert len(backup.config_hash) == 64  # SHA256 hash length
    
    def test_device_password_encryption(self, app, sample_device):
        """测试设备密码加密"""
        with app.app_context():
            device = Device(
                name='test_device',
                ip_address='192.168.1.2',
                username='admin'
            )
            device.set_password('secretpassword')
            db.session.add(device)
            db.session.commit()
            
            # 密码应该被加密存储
            assert device.password_encrypted is not None
            assert device.password_encrypted != 'secretpassword'
            
            # 应该能够正确解密
            decrypted_password = device.get_password()
            assert decrypted_password == 'secretpassword'
    
    def test_template_category_creation(self, app):
        """测试模板分类创建"""
        with app.app_context():
            category = TemplateCategory(
                name='test_category',
                description='测试分类',
                icon='fas fa-test',
                color='#007bff'
            )
            db.session.add(category)
            db.session.commit()
            
            assert category.name == 'test_category'
            assert category.icon == 'fas fa-test'
            assert category.color == '#007bff'

class TestDatabaseRelationships:
    """数据库关联测试"""
    
    def test_user_tasks_relationship(self, app, sample_user):
        """测试用户和任务的关联"""
        with app.app_context():
            task1 = Task(name='task1', task_type='command', user=sample_user)
            task2 = Task(name='task2', task_type='command', user=sample_user)
            db.session.add_all([task1, task2])
            db.session.commit()
            
            assert sample_user.tasks.count() == 2
            assert task1 in sample_user.tasks.all()
            assert task2 in sample_user.tasks.all()
    
    def test_device_tasks_relationship(self, app, sample_device):
        """测试设备和任务的关联"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.password = 'testpass'
            db.session.add(user)
            db.session.commit()
            
            task1 = Task(name='task1', task_type='command', user=user, device=sample_device)
            task2 = Task(name='task2', task_type='command', user=user, device=sample_device)
            db.session.add_all([task1, task2])
            db.session.commit()
            
            assert sample_device.tasks.count() == 2
            assert task1 in sample_device.tasks.all()
            assert task2 in sample_device.tasks.all()
    
    def test_template_tasks_relationship(self, app):
        """测试模板和任务的关联"""
        with app.app_context():
            template = ConfigTemplate(
                name='test_template',
                category='basic',
                template_content='hostname {{ hostname }}'
            )
            db.session.add(template)
            
            user = User(username='testuser', email='test@example.com')
            user.password = 'testpass'
            db.session.add(user)
            db.session.commit()
            
            task = Task(
                name='template_task',
                task_type='config_template',
                user=user,
                template=template
            )
            task.set_template_variables({'hostname': 'test-switch'})
            db.session.add(task)
            db.session.commit()
            
            assert template.tasks.count() == 1
            assert task.template == template
            variables = task.get_template_variables()
            assert variables['hostname'] == 'test-switch'
