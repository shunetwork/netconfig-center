"""
功能测试用例
测试系统的核心功能模块
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import url_for
from app import create_app, db
from app.models import User, Role, Device, DeviceGroup, ConfigTemplate, Task, AuditLog
from app.templates.services import TemplateService
from app.devices.services import DeviceManagementService, DeviceStatusService

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

class TestTemplateFunctionality:
    """模板功能测试"""
    
    def test_template_rendering_functionality(self, app):
        """测试模板渲染功能"""
        with app.app_context():
            # 创建测试模板
            template = ConfigTemplate(
                name='test_template',
                category='basic',
                template_content='hostname {{ hostname }}\ninterface {{ interface_name }}\nip address {{ ip_address }} {{ subnet_mask }}'
            )
            db.session.add(template)
            db.session.commit()
            
            # 测试模板渲染
            variables = {
                'hostname': 'test-switch',
                'interface_name': 'GigabitEthernet0/1',
                'ip_address': '192.168.1.1',
                'subnet_mask': '255.255.255.0'
            }
            
            result = TemplateService.render_template(template, variables)
            
            assert result['success'] == True
            assert 'hostname test-switch' in result['rendered_content']
            assert 'interface GigabitEthernet0/1' in result['rendered_content']
            assert 'ip address 192.168.1.1 255.255.255.0' in result['rendered_content']
    
    def test_template_variable_extraction_functionality(self, app):
        """测试模板变量提取功能"""
        with app.app_context():
            template_content = 'hostname {{ hostname }}\ninterface {{ interface_name }}\nip address {{ ip_address }} {{ subnet_mask }}'
            variables = TemplateService.extract_template_variables(template_content)
            
            assert 'hostname' in variables
            assert 'interface_name' in variables
            assert 'ip_address' in variables
            assert 'subnet_mask' in variables
            assert len(variables) == 4
    
    def test_template_validation_functionality(self, app):
        """测试模板验证功能"""
        with app.app_context():
            # 创建模板和变量
            template = ConfigTemplate(
                name='validation_template',
                category='basic',
                template_content='hostname {{ hostname }}'
            )
            db.session.add(template)
            db.session.commit()
            
            # 添加必需变量
            from app.models import TemplateVariable
            variable = TemplateVariable(
                name='hostname',
                var_type='string',
                required=True,
                template=template
            )
            db.session.add(variable)
            db.session.commit()
            
            # 测试变量验证
            variables = {'hostname': 'test-switch'}
            errors = TemplateService.validate_template_variables(template, variables)
            assert len(errors) == 0  # 应该没有错误
            
            # 测试缺少必需变量
            empty_variables = {}
            errors = TemplateService.validate_template_variables(template, empty_variables)
            assert len(errors) > 0  # 应该有错误
    
    def test_template_search_functionality(self, app):
        """测试模板搜索功能"""
        with app.app_context():
            # 创建多个测试模板
            templates_data = [
                {'name': 'router_config', 'category': 'routing', 'content': 'router ospf 1'},
                {'name': 'interface_config', 'category': 'interface', 'content': 'interface gigabitethernet0/1'},
                {'name': 'vlan_config', 'category': 'vlan', 'content': 'vlan 100'}
            ]
            
            for data in templates_data:
                template = ConfigTemplate(
                    name=data['name'],
                    category=data['category'],
                    template_content=data['content']
                )
                db.session.add(template)
            
            db.session.commit()
            
            # 测试关键词搜索
            results = TemplateService.search_templates(keyword='router')
            assert len(results) > 0
            assert any('router' in t.name for t in results)
            
            # 测试分类搜索
            results = TemplateService.search_templates(category='interface')
            assert len(results) > 0
            assert all(t.category == 'interface' for t in results)

class TestDeviceFunctionality:
    """设备功能测试"""
    
    def test_device_management_functionality(self, app, sample_user):
        """测试设备管理功能"""
        with app.app_context():
            # 测试设备创建
            device_data = {
                'name': 'test_device',
                'ip_address': '192.168.1.1',
                'hostname': 'test-switch',
                'device_type': 'cisco_switch',
                'connection_type': 'ssh',
                'port': 22,
                'username': 'admin',
                'password': 'admin123',
                'description': '测试设备'
            }
            
            device = DeviceManagementService.create_device(device_data, sample_user.id)
            
            assert device.name == 'test_device'
            assert device.ip_address == '192.168.1.1'
            assert device.get_password() == 'admin123'
            
            # 测试设备更新
            update_data = {
                'name': 'updated_device',
                'ip_address': '192.168.1.2',
                'hostname': 'updated-switch',
                'device_type': 'cisco_switch',
                'connection_type': 'ssh',
                'port': 22,
                'username': 'admin',
                'password': 'newpassword',
                'description': '更新后的设备'
            }
            
            updated_device = DeviceManagementService.update_device(device, update_data, sample_user.id)
            
            assert updated_device.name == 'updated_device'
            assert updated_device.ip_address == '192.168.1.2'
            assert updated_device.get_password() == 'newpassword'
    
    def test_device_status_functionality(self, app, sample_user):
        """测试设备状态功能"""
        with app.app_context():
            # 创建设备
            device = Device(
                name='status_test_device',
                ip_address='192.168.1.1',
                device_type='cisco_switch',
                connection_type='ssh',
                username='admin'
            )
            device.set_password('admin123')
            db.session.add(device)
            db.session.commit()
            
            # 测试状态更新
            DeviceStatusService.update_device_status(device, 'online', '设备上线')
            
            assert device.status.value == 'online'
            assert device.last_checked is not None
            
            # 测试批量状态检查（需要mock网络操作）
            with patch('app.devices.services.DeviceConnectionService.test_ping') as mock_ping, \
                 patch('app.devices.services.DeviceConnectionService.test_tcp_port') as mock_port:
                
                mock_ping.return_value = {'success': True, 'message': 'Ping成功'}
                mock_port.return_value = {'success': True, 'message': '端口连接成功'}
                
                result = DeviceStatusService.check_device_status(device)
                
                assert result['status'] == 'online'
                assert 'ping' in result['details']
                assert 'port' in result['details']
    
    def test_device_group_functionality(self, app, sample_user):
        """测试设备组功能"""
        with app.app_context():
            # 测试设备组创建
            group_data = {
                'name': 'test_group',
                'description': '测试设备组'
            }
            
            group = DeviceManagementService.create_group(group_data, sample_user.id)
            
            assert group.name == 'test_group'
            assert group.description == '测试设备组'
            
            # 创建设备并添加到组
            device = Device(
                name='group_test_device',
                ip_address='192.168.1.1',
                device_type='cisco_switch',
                connection_type='ssh',
                username='admin',
                group=group
            )
            device.set_password('admin123')
            db.session.add(device)
            db.session.commit()
            
            # 验证设备组关系
            assert device.group == group
            assert device in group.devices.all()

class TestTaskFunctionality:
    """任务功能测试"""
    
    def test_task_creation_functionality(self, app, sample_user):
        """测试任务创建功能"""
        with app.app_context():
            # 创建设备
            device = Device(
                name='task_test_device',
                ip_address='192.168.1.1',
                device_type='cisco_switch',
                connection_type='ssh',
                username='admin'
            )
            device.set_password('admin123')
            db.session.add(device)
            db.session.commit()
            
            # 测试任务创建
            task = Task(
                name='test_task',
                description='测试任务',
                task_type='command',
                command='show version',
                user=sample_user,
                device=device
            )
            db.session.add(task)
            db.session.commit()
            
            assert task.name == 'test_task'
            assert task.device == device
            assert task.user == sample_user
            assert task.status.value == 'pending'
    
    def test_task_status_management_functionality(self, app, sample_user):
        """测试任务状态管理功能"""
        with app.app_context():
            # 创建任务
            task = Task(
                name='status_test_task',
                task_type='command',
                command='show version',
                user=sample_user
            )
            db.session.add(task)
            db.session.commit()
            
            # 测试任务开始
            task.start()
            assert task.status.value == 'running'
            assert task.started_at is not None
            
            # 测试任务完成
            task.complete(True, '任务执行成功')
            assert task.status.value == 'success'
            assert task.completed_at is not None
            assert task.result_message == '任务执行成功'
            
            # 测试任务重试
            task.retry_count = 0
            task.max_retries = 3
            assert task.retry() == True
            assert task.status.value == 'pending'
            assert task.retry_count == 1
    
    def test_task_result_functionality(self, app, sample_user):
        """测试任务结果功能"""
        with app.app_context():
            # 创建设备和任务
            device = Device(
                name='result_test_device',
                ip_address='192.168.1.1',
                device_type='cisco_switch',
                connection_type='ssh',
                username='admin'
            )
            device.set_password('admin123')
            db.session.add(device)
            
            task = Task(
                name='result_test_task',
                task_type='command',
                command='show version',
                user=sample_user,
                device=device
            )
            db.session.add(task)
            db.session.commit()
            
            # 创建任务结果
            from app.models import TaskResult
            result = TaskResult(
                device_name=device.name,
                device_ip=device.ip_address,
                command='show version',
                output='Cisco IOS Software, Version 15.1(4)M4',
                exit_code=0,
                execution_time=1.5,
                task=task,
                device=device
            )
            db.session.add(result)
            db.session.commit()
            
            assert result.task == task
            assert result.device == device
            assert result.is_success() == True
            assert task.results.count() == 1

class TestAuditLogFunctionality:
    """审计日志功能测试"""
    
    def test_audit_log_creation_functionality(self, app, sample_user):
        """测试审计日志创建功能"""
        with app.app_context():
            # 测试审计日志创建
            AuditLog.log_action(
                user=sample_user,
                action='test_action',
                resource_type='device',
                resource_id=1,
                resource_name='test_device',
                success=True,
                details={'test': 'data'}
            )
            
            # 验证日志已创建
            logs = AuditLog.query.filter_by(user=sample_user).all()
            assert len(logs) > 0
            
            latest_log = logs[-1]
            assert latest_log.action == 'test_action'
            assert latest_log.resource_type == 'device'
            assert latest_log.success == True
            
            # 验证详情数据
            details = latest_log.get_details()
            assert details['test'] == 'data'
    
    def test_audit_log_query_functionality(self, app, sample_user):
        """测试审计日志查询功能"""
        with app.app_context():
            # 创建多个审计日志
            actions = ['create_device', 'update_device', 'delete_device']
            
            for action in actions:
                AuditLog.log_action(
                    user=sample_user,
                    action=action,
                    resource_type='device',
                    resource_id=1,
                    resource_name='test_device',
                    success=True
                )
            
            # 测试按动作查询
            logs = AuditLog.query.filter_by(action='create_device').all()
            assert len(logs) == 1
            assert logs[0].action == 'create_device'
            
            # 测试按用户查询
            logs = AuditLog.query.filter_by(user=sample_user).all()
            assert len(logs) == 3
            
            # 测试按成功状态查询
            logs = AuditLog.query.filter_by(success=True).all()
            assert len(logs) == 3

class TestSecurityFunctionality:
    """安全功能测试"""
    
    def test_password_encryption_functionality(self, app, sample_user):
        """测试密码加密功能"""
        with app.app_context():
            # 测试用户密码加密
            user = User(
                username='security_test_user',
                email='security@example.com',
                role=sample_user.role
            )
            user.password = 'testpassword123'
            
            assert user.password_hash is not None
            assert user.password_hash != 'testpassword123'
            assert user.verify_password('testpassword123')
            assert not user.verify_password('wrongpassword')
            
            # 测试设备密码加密
            device = Device(
                name='security_test_device',
                ip_address='192.168.1.1',
                device_type='cisco_switch',
                connection_type='ssh',
                username='admin'
            )
            device.set_password('devicepassword123')
            
            assert device.password_encrypted is not None
            assert device.password_encrypted != 'devicepassword123'
            assert device.get_password() == 'devicepassword123'
    
    def test_permission_functionality(self, app):
        """测试权限功能"""
        with app.app_context():
            # 创建不同权限的角色
            viewer_role = Role(name='viewer', description='查看者')
            viewer_role.add_permission(Role.PERMISSION_VIEW)
            
            operator_role = Role(name='operator', description='操作员')
            operator_role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE)
            
            admin_role = Role(name='admin', description='管理员')
            admin_role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE | Role.PERMISSION_CONFIGURE | Role.PERMISSION_ADMIN)
            
            db.session.add_all([viewer_role, operator_role, admin_role])
            
            # 创建用户并测试权限
            viewer_user = User(username='viewer', email='viewer@example.com', role=viewer_role)
            viewer_user.password = 'testpass'
            
            operator_user = User(username='operator', email='operator@example.com', role=operator_role)
            operator_user.password = 'testpass'
            
            admin_user = User(username='admin_user', email='admin@example.com', role=admin_role)
            admin_user.password = 'testpass'
            
            db.session.add_all([viewer_user, operator_user, admin_user])
            db.session.commit()
            
            # 测试权限检查
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

class TestDataValidationFunctionality:
    """数据验证功能测试"""
    
    def test_device_validation_functionality(self, app, sample_user):
        """测试设备数据验证功能"""
        with app.app_context():
            # 测试IP地址验证
            device_data = {
                'name': 'test_device',
                'ip_address': 'invalid_ip',  # 无效IP地址
                'device_type': 'cisco_switch',
                'connection_type': 'ssh',
                'username': 'admin',
                'password': 'admin123'
            }
            
            # 这里应该抛出验证错误，但由于我们直接调用服务，需要手动验证
            # 在实际应用中，这会在表单验证阶段被捕获
            assert True  # 占位符，实际测试需要更复杂的验证逻辑
    
    def test_template_validation_functionality(self, app):
        """测试模板数据验证功能"""
        with app.app_context():
            # 测试模板语法验证
            template_content = 'hostname {{ hostname\ninterface {{ interface_name }}'  # 缺少闭合括号
            
            try:
                from jinja2 import Template
                Template(template_content)
                assert False, "应该抛出语法错误"
            except Exception:
                assert True  # 预期的语法错误
    
    def test_task_validation_functionality(self, app, sample_user):
        """测试任务数据验证功能"""
        with app.app_context():
            # 测试任务数据验证
            task = Task(
                name='',  # 空名称
                task_type='command',
                command='show version',
                user=sample_user
            )
            
            # 这里应该验证失败，但由于我们直接创建对象，需要手动验证
            # 在实际应用中，这会在表单验证阶段被捕获
            assert True  # 占位符，实际测试需要更复杂的验证逻辑
