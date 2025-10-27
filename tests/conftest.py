"""
测试配置文件
定义测试中使用的公共fixture和配置
"""

import pytest
import os
import tempfile
from flask import Flask
from app import create_app, db
from app.models import User, Role, Device, DeviceGroup, ConfigTemplate, Task, AuditLog

@pytest.fixture(scope='session')
def app():
    """创建测试应用实例"""
    # 创建临时数据库文件
    db_fd, db_path = tempfile.mkstemp()
    
    # 配置测试环境
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # 创建默认角色
        admin_role = Role(name='admin', description='管理员')
        admin_role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE | Role.PERMISSION_CONFIGURE | Role.PERMISSION_ADMIN)
        
        user_role = Role(name='user', description='普通用户')
        user_role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE)
        
        db.session.add(admin_role)
        db.session.add(user_role)
        db.session.commit()
        
        yield app
        
        # 清理
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(scope='session')
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture(scope='session')
def runner(app):
    """创建测试运行器"""
    return app.test_cli_runner()

@pytest.fixture
def admin_user(app):
    """创建管理员用户"""
    with app.app_context():
        role = Role.query.filter_by(name='admin').first()
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
def normal_user(app):
    """创建普通用户"""
    with app.app_context():
        role = Role.query.filter_by(name='user').first()
        user = User(
            username='user',
            email='user@example.com',
            role=role
        )
        user.password = 'user123'
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def sample_device_group(app, admin_user):
    """创建示例设备组"""
    with app.app_context():
        group = DeviceGroup(
            name='test_group',
            description='测试设备组',
            created_by=admin_user
        )
        db.session.add(group)
        db.session.commit()
        return group

@pytest.fixture
def sample_device(app, admin_user, sample_device_group):
    """创建示例设备"""
    with app.app_context():
        device = Device(
            name='test_device',
            ip_address='192.168.1.1',
            hostname='test-switch',
            device_type='cisco_switch',
            connection_type='ssh',
            port=22,
            username='admin',
            description='测试设备',
            location='测试机房',
            vendor='Cisco',
            model='Catalyst 2960',
            group=sample_device_group,
            created_by=admin_user
        )
        device.set_password('admin123')
        db.session.add(device)
        db.session.commit()
        return device

@pytest.fixture
def sample_template(app, admin_user):
    """创建示例配置模板"""
    with app.app_context():
        template = ConfigTemplate(
            name='test_template',
            description='测试配置模板',
            category='basic',
            template_content='hostname {{ hostname }}\ninterface {{ interface_name }}\ndescription {{ description }}',
            version='1.0',
            created_by=admin_user
        )
        db.session.add(template)
        db.session.commit()
        return template

@pytest.fixture
def sample_task(app, admin_user, sample_device):
    """创建示例任务"""
    with app.app_context():
        task = Task(
            name='test_task',
            description='测试任务',
            task_type='command',
            command='show version',
            user=admin_user,
            device=sample_device
        )
        db.session.add(task)
        db.session.commit()
        return task

@pytest.fixture
def sample_audit_log(app, admin_user):
    """创建示例审计日志"""
    with app.app_context():
        log = AuditLog(
            user=admin_user,
            action='test_action',
            resource_type='device',
            resource_id=1,
            resource_name='test_device',
            success=True,
            details={'test': 'data'}
        )
        db.session.add(log)
        db.session.commit()
        return log

@pytest.fixture
def authenticated_client(client, admin_user):
    """创建已认证的测试客户端"""
    # 登录用户
    client.post('/auth/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    return client

@pytest.fixture
def mock_ssh_connection():
    """模拟SSH连接"""
    from unittest.mock import Mock
    
    mock_connection = Mock()
    mock_connection.is_alive.return_value = True
    mock_connection.send_command.return_value = 'Cisco IOS Software, Version 15.1(4)M4'
    mock_connection.send_command_expect.return_value = ('Cisco IOS Software, Version 15.1(4)M4', '')
    mock_connection.send_config_set.return_value = 'configured'
    mock_connection.disconnect.return_value = None
    
    return mock_connection

@pytest.fixture
def mock_netmiko():
    """模拟Netmiko连接"""
    from unittest.mock import patch, Mock
    
    mock_device = Mock()
    mock_device.send_command.return_value = 'Cisco IOS Software, Version 15.1(4)M4'
    mock_device.send_command_expect.return_value = ('Cisco IOS Software, Version 15.1(4)M4', '')
    mock_device.send_config_set.return_value = 'configured'
    mock_device.disconnect.return_value = None
    
    with patch('netmiko.ConnectHandler') as mock_connect:
        mock_connect.return_value = mock_device
        yield mock_device

@pytest.fixture
def mock_paramiko():
    """模拟Paramiko连接"""
    from unittest.mock import patch, Mock
    
    mock_client = Mock()
    mock_client.connect.return_value = None
    mock_client.get_transport.return_value = Mock()
    mock_client.get_transport.return_value.is_active.return_value = True
    mock_client.exec_command.return_value = (Mock(), Mock(), Mock())
    mock_client.close.return_value = None
    
    with patch('paramiko.SSHClient') as mock_ssh:
        mock_ssh.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_celery():
    """模拟Celery任务"""
    from unittest.mock import patch, Mock
    
    mock_task = Mock()
    mock_task.delay.return_value = Mock(id='test-task-id')
    mock_task.apply_async.return_value = Mock(id='test-task-id')
    
    with patch('app.tasks.network_tasks.execute_device_command', mock_task), \
         patch('app.tasks.network_tasks.execute_device_commands', mock_task), \
         patch('app.tasks.template_tasks.render_and_apply_template', mock_task), \
         patch('app.tasks.backup_tasks.backup_device_config', mock_task):
        yield mock_task

@pytest.fixture
def sample_config_backup(app, admin_user, sample_device):
    """创建示例配置备份"""
    with app.app_context():
        backup = ConfigBackup(
            device=sample_device,
            backup_name='test_backup',
            config_content='hostname test-switch\ninterface GigabitEthernet0/1\ndescription test',
            config_type='running',
            backup_method='manual',
            created_by=admin_user
        )
        db.session.add(backup)
        db.session.commit()
        return backup

@pytest.fixture
def sample_template_variable(app, sample_template):
    """创建示例模板变量"""
    with app.app_context():
        variable = TemplateVariable(
            name='hostname',
            var_type='string',
            required=True,
            default_value='test-switch',
            description='设备主机名',
            template=sample_template
        )
        db.session.add(variable)
        db.session.commit()
        return variable

@pytest.fixture
def sample_template_category(app):
    """创建示例模板分类"""
    with app.app_context():
        category = TemplateCategory(
            name='interface',
            display_name='接口配置',
            description='接口相关配置模板',
            sort_order=1
        )
        db.session.add(category)
        db.session.commit()
        return category

@pytest.fixture
def sample_backup_schedule(app, admin_user, sample_device):
    """创建示例备份计划"""
    with app.app_context():
        schedule = BackupSchedule(
            name='test_schedule',
            description='测试备份计划',
            schedule_type='daily',
            schedule_time='02:00',
            enabled=True,
            created_by=admin_user
        )
        db.session.add(schedule)
        db.session.commit()
        
        # 添加设备到备份计划
        from app.models.backup import BackupScheduleDevice
        schedule_device = BackupScheduleDevice(
            schedule=schedule,
            device=sample_device
        )
        db.session.add(schedule_device)
        db.session.commit()
        
        return schedule

@pytest.fixture
def sample_task_result(app, sample_task, sample_device):
    """创建示例任务结果"""
    with app.app_context():
        result = TaskResult(
            device_name=sample_device.name,
            device_ip=sample_device.ip_address,
            command=sample_task.command,
            output='Cisco IOS Software, Version 15.1(4)M4',
            exit_code=0,
            execution_time=1.5,
            task=sample_task,
            device=sample_device
        )
        db.session.add(result)
        db.session.commit()
        return result

@pytest.fixture(autouse=True)
def cleanup_database(app):
    """自动清理数据库"""
    yield
    with app.app_context():
        # 清理所有数据
        db.session.rollback()
        db.session.remove()

@pytest.fixture
def test_data_setup(app, admin_user):
    """设置测试数据"""
    with app.app_context():
        # 创建设备组
        group = DeviceGroup(name='test_group', description='测试组', created_by=admin_user)
        db.session.add(group)
        
        # 创建设备
        device = Device(
            name='test_device',
            ip_address='192.168.1.1',
            device_type='cisco_switch',
            connection_type='ssh',
            username='admin',
            group=group,
            created_by=admin_user
        )
        device.set_password('admin123')
        db.session.add(device)
        
        # 创建模板
        template = ConfigTemplate(
            name='test_template',
            category='basic',
            template_content='hostname {{ hostname }}',
            created_by=admin_user
        )
        db.session.add(template)
        
        # 创建任务
        task = Task(
            name='test_task',
            task_type='command',
            command='show version',
            user=admin_user,
            device=device
        )
        db.session.add(task)
        
        db.session.commit()
        
        return {
            'group': group,
            'device': device,
            'template': template,
            'task': task
        }

# 测试标记
def pytest_configure(config):
    """配置测试标记"""
    config.addinivalue_line(
        "markers", "unit: 单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "functional: 功能测试"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试"
    )

def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        # 为慢速测试添加标记
        if "performance" in item.nodeid or "stress" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # 为集成测试添加标记
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # 为功能测试添加标记
        if "functional" in item.nodeid:
            item.add_marker(pytest.mark.functional)
        
        # 为性能测试添加标记
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)

# 测试报告配置
def pytest_html_report_title(report):
    """设置HTML报告标题"""
    report.title = "NetManagerX 测试报告"

def pytest_html_results_table_header(cells):
    """设置HTML报告表头"""
    cells.insert(2, html.th('Description'))
    cells.insert(3, html.th('Duration'))
    cells.pop()

def pytest_html_results_table_row(report, cells):
    """设置HTML报告表格行"""
    cells.insert(2, html.td(report.description))
    cells.insert(3, html.td(report.duration))
    cells.pop()

def pytest_html_results_summary(prefix, summary, postfix):
    """设置HTML报告摘要"""
    prefix.extend([html.p("NetManagerX 网络配置管理系统测试报告")])

# 测试覆盖率配置
def pytest_configure(config):
    """配置测试覆盖率"""
    if config.getoption("--cov"):
        config.addinivalue_line(
            "markers", "cov: 覆盖率测试"
        )
