"""
设备管理模块测试用例
测试设备CRUD、状态检测、分组管理等功能
"""

import pytest
from flask import url_for
from app import create_app, db
from app.models import Device, DeviceGroup, DeviceType, ConnectionType, DeviceStatus, User, Role
from app.devices.services import DeviceManagementService, DeviceStatusService, DeviceGroupService

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
        role = Role(name='test_role', description='测试角色')
        role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE)
        db.session.add(role)
        
        user = User(
            username='testuser',
            email='test@example.com',
            role=role
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
            device_type=DeviceType.CISCO_SWITCH,
            connection_type=ConnectionType.SSH,
            port=22,
            username='admin',
            group=sample_device_group
        )
        device.set_password('admin123')
        db.session.add(device)
        db.session.commit()
        return device

class TestDeviceManagement:
    """设备管理测试"""
    
    def test_device_creation(self, app, sample_user, sample_device_group):
        """测试设备创建"""
        with app.app_context():
            device_data = {
                'name': 'new_device',
                'ip_address': '192.168.1.100',
                'hostname': 'new-switch',
                'device_type': DeviceType.CISCO_SWITCH,
                'connection_type': ConnectionType.SSH,
                'port': 22,
                'username': 'admin',
                'password': 'admin123',
                'description': '测试设备',
                'group_id': sample_device_group.id
            }
            
            device = DeviceManagementService.create_device(device_data, sample_user.id)
            
            assert device.name == 'new_device'
            assert device.ip_address == '192.168.1.100'
            assert device.username == 'admin'
            assert device.group == sample_device_group
            assert device.get_password() == 'admin123'
    
    def test_device_update(self, app, sample_user, sample_device):
        """测试设备更新"""
        with app.app_context():
            device_data = {
                'name': 'updated_device',
                'ip_address': '192.168.1.2',
                'hostname': 'updated-switch',
                'device_type': DeviceType.CISCO_SWITCH,
                'connection_type': ConnectionType.SSH,
                'port': 22,
                'username': 'admin',
                'password': 'newpassword',
                'description': '更新后的设备'
            }
            
            updated_device = DeviceManagementService.update_device(sample_device, device_data, sample_user.id)
            
            assert updated_device.name == 'updated_device'
            assert updated_device.ip_address == '192.168.1.2'
            assert updated_device.get_password() == 'newpassword'
    
    def test_device_deletion(self, app, sample_user, sample_device):
        """测试设备删除"""
        with app.app_context():
            device_id = sample_device.id
            device_name = sample_device.name
            
            DeviceManagementService.delete_device(sample_device, sample_user.id)
            
            deleted_device = Device.query.get(device_id)
            assert deleted_device is None
    
    def test_device_duplicate_name(self, app, sample_user, sample_device):
        """测试设备名称重复"""
        with app.app_context():
            device_data = {
                'name': sample_device.name,  # 重复名称
                'ip_address': '192.168.1.200',
                'device_type': DeviceType.CISCO_SWITCH,
                'connection_type': ConnectionType.SSH,
                'username': 'admin',
                'password': 'admin123'
            }
            
            # 应该抛出异常或返回错误
            try:
                DeviceManagementService.create_device(device_data, sample_user.id)
                assert False, "应该抛出重复名称异常"
            except Exception:
                pass  # 预期的异常
    
    def test_device_duplicate_ip(self, app, sample_user, sample_device):
        """测试设备IP重复"""
        with app.app_context():
            device_data = {
                'name': 'another_device',
                'ip_address': sample_device.ip_address,  # 重复IP
                'device_type': DeviceType.CISCO_SWITCH,
                'connection_type': ConnectionType.SSH,
                'username': 'admin',
                'password': 'admin123'
            }
            
            # 应该抛出异常或返回错误
            try:
                DeviceManagementService.create_device(device_data, sample_user.id)
                assert False, "应该抛出重复IP异常"
            except Exception:
                pass  # 预期的异常

class TestDeviceGroupManagement:
    """设备组管理测试"""
    
    def test_group_creation(self, app, sample_user):
        """测试设备组创建"""
        with app.app_context():
            group_data = {
                'name': 'new_group',
                'description': '新设备组'
            }
            
            group = DeviceGroupService.create_group(group_data, sample_user.id)
            
            assert group.name == 'new_group'
            assert group.description == '新设备组'
    
    def test_group_update(self, app, sample_user, sample_device_group):
        """测试设备组更新"""
        with app.app_context():
            group_data = {
                'name': 'updated_group',
                'description': '更新后的设备组'
            }
            
            updated_group = DeviceGroupService.update_group(sample_device_group, group_data, sample_user.id)
            
            assert updated_group.name == 'updated_group'
            assert updated_group.description == '更新后的设备组'
    
    def test_group_deletion(self, app, sample_user, sample_device_group):
        """测试设备组删除"""
        with app.app_context():
            group_id = sample_device_group.id
            group_name = sample_device_group.name
            
            DeviceGroupService.delete_group(sample_device_group, sample_user.id)
            
            deleted_group = DeviceGroup.query.get(group_id)
            assert deleted_group is None
    
    def test_group_duplicate_name(self, app, sample_user, sample_device_group):
        """测试设备组名称重复"""
        with app.app_context():
            group_data = {
                'name': sample_device_group.name,  # 重复名称
                'description': '重复名称的设备组'
            }
            
            # 应该抛出异常或返回错误
            try:
                DeviceGroupService.create_group(group_data, sample_user.id)
                assert False, "应该抛出重复名称异常"
            except Exception:
                pass  # 预期的异常

class TestDeviceStatusService:
    """设备状态服务测试"""
    
    def test_ping_test(self, app):
        """测试Ping功能"""
        with app.app_context():
            from app.devices.services import DeviceConnectionService
            
            # 测试本地回环地址
            result = DeviceConnectionService.test_ping('127.0.0.1')
            assert 'success' in result
            assert 'message' in result
    
    def test_tcp_port_test(self, app):
        """测试TCP端口连接"""
        with app.app_context():
            from app.devices.services import DeviceConnectionService
            
            # 测试本地SSH端口（可能不开放，但不应该出错）
            result = DeviceConnectionService.test_tcp_port('127.0.0.1', 22)
            assert 'success' in result
            assert 'message' in result
    
    def test_device_status_update(self, app, sample_device):
        """测试设备状态更新"""
        with app.app_context():
            DeviceStatusService.update_device_status(sample_device, DeviceStatus.ONLINE, '设备上线')
            
            assert sample_device.status == DeviceStatus.ONLINE
            assert sample_device.last_checked is not None
    
    def test_batch_status_check(self, app, sample_user):
        """测试批量状态检查"""
        with app.app_context():
            # 创建多个测试设备
            devices = []
            for i in range(3):
                device = Device(
                    name=f'test_device_{i}',
                    ip_address=f'192.168.1.{i+1}',
                    username='admin'
                )
                device.set_password('admin123')
                db.session.add(device)
                devices.append(device)
            
            db.session.commit()
            
            device_ids = [device.id for device in devices]
            result = DeviceStatusService.batch_check_status(device_ids)
            
            assert len(result) == 3
            for device_id in device_ids:
                assert device_id in result
                assert 'device_name' in result[device_id]
                assert 'result' in result[device_id]

class TestDeviceRoutes:
    """设备路由测试"""
    
    def test_device_list_page(self, client, sample_user):
        """测试设备列表页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get('/devices/')
        assert response.status_code == 200
        assert b'设备管理' in response.data
    
    def test_device_detail_page(self, client, sample_user, sample_device):
        """测试设备详情页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get(f'/devices/{sample_device.id}')
        assert response.status_code == 200
        assert sample_device.name.encode() in response.data
    
    def test_device_add_page(self, client, sample_user):
        """测试设备添加页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get('/devices/add')
        assert response.status_code == 200
        assert b'添加设备' in response.data
    
    def test_device_add_post(self, client, sample_user, sample_device_group):
        """测试设备添加POST请求"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.post('/devices/add', data={
            'name': 'new_test_device',
            'ip_address': '192.168.1.200',
            'device_type': DeviceType.CISCO_SWITCH.value,
            'connection_type': ConnectionType.SSH.value,
            'port': 22,
            'username': 'admin',
            'password': 'admin123',
            'group_id': sample_device_group.id
        })
        
        assert response.status_code == 302  # 重定向到设备详情页
    
    def test_device_edit_page(self, client, sample_user, sample_device):
        """测试设备编辑页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get(f'/devices/{sample_device.id}/edit')
        assert response.status_code == 200
        assert b'编辑设备' in response.data
    
    def test_device_delete(self, client, sample_user, sample_device):
        """测试设备删除"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.post(f'/devices/{sample_device.id}/delete')
        assert response.status_code == 302  # 重定向到设备列表页
    
    def test_device_groups_page(self, client, sample_user):
        """测试设备组管理页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get('/devices/groups')
        assert response.status_code == 200
        assert b'设备组' in response.data
    
    def test_device_api_endpoints(self, client, sample_user, sample_device):
        """测试设备API端点"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 测试设备列表API
        response = client.get('/devices/api/devices')
        assert response.status_code == 200
        
        # 测试设备详情API
        response = client.get(f'/devices/api/device/{sample_device.id}')
        assert response.status_code == 200
        
        # 测试设备组API
        response = client.get('/devices/api/groups')
        assert response.status_code == 200

class TestDeviceForms:
    """设备表单测试"""
    
    def test_device_form_validation(self, app):
        """测试设备表单验证"""
        with app.app_context():
            from app.devices.forms import DeviceForm
            
            # 测试空表单
            form = DeviceForm()
            assert not form.validate()
            assert 'name' in form.errors
            assert 'ip_address' in form.errors
            
            # 测试有效表单
            form = DeviceForm(data={
                'name': 'test_device',
                'ip_address': '192.168.1.1',
                'device_type': DeviceType.CISCO_SWITCH.value,
                'connection_type': ConnectionType.SSH.value,
                'username': 'admin',
                'password': 'admin123'
            })
            assert form.validate()
    
    def test_device_group_form_validation(self, app):
        """测试设备组表单验证"""
        with app.app_context():
            from app.devices.forms import DeviceGroupForm
            
            # 测试空表单
            form = DeviceGroupForm()
            assert not form.validate()
            assert 'name' in form.errors
            
            # 测试有效表单
            form = DeviceGroupForm(data={
                'name': 'test_group',
                'description': '测试设备组'
            })
            assert form.validate()
