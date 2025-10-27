"""
通信模块测试用例
测试SSH、Telnet、RESTCONF连接和命令执行功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import url_for
from app import create_app, db
from app.models import Device, DeviceGroup, DeviceType, ConnectionType, DeviceStatus, User, Role

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
def ssh_device(app):
    """创建SSH设备"""
    with app.app_context():
        device = Device(
            name='ssh_device',
            ip_address='192.168.1.1',
            device_type=DeviceType.CISCO_SWITCH,
            connection_type=ConnectionType.SSH,
            port=22,
            username='admin'
        )
        device.set_password('admin123')
        db.session.add(device)
        db.session.commit()
        return device

@pytest.fixture
def telnet_device(app):
    """创建Telnet设备"""
    with app.app_context():
        device = Device(
            name='telnet_device',
            ip_address='192.168.1.2',
            device_type=DeviceType.CISCO_SWITCH,
            connection_type=ConnectionType.TELNET,
            port=23,
            username='admin'
        )
        device.set_password('admin123')
        db.session.add(device)
        db.session.commit()
        return device

class TestSSHClient:
    """SSH客户端测试"""
    
    @patch('app.communication.ssh_client.ConnectHandler')
    def test_ssh_connection_success(self, mock_connect, app, ssh_device):
        """测试SSH连接成功"""
        with app.app_context():
            from app.communication.ssh_client import SSHClient
            
            # 模拟成功的连接
            mock_connection = Mock()
            mock_connection.is_alive.return_value = True
            mock_connect.return_value = mock_connection
            
            client = SSHClient(ssh_device)
            result = client.connect()
            
            assert result['success'] == True
            assert 'SSH连接建立成功' in result['message']
            assert result['connection_id'] is not None
    
    @patch('app.communication.ssh_client.ConnectHandler')
    def test_ssh_connection_failure(self, mock_connect, app, ssh_device):
        """测试SSH连接失败"""
        with app.app_context():
            from app.communication.ssh_client import SSHClient
            from app.communication.ssh_client import NetMikoAuthenticationException
            
            # 模拟认证失败
            mock_connect.side_effect = NetMikoAuthenticationException("认证失败")
            
            client = SSHClient(ssh_device)
            result = client.connect()
            
            assert result['success'] == False
            assert 'SSH认证失败' in result['error']
    
    @patch('app.communication.ssh_client.ConnectHandler')
    def test_ssh_command_execution(self, mock_connect, app, ssh_device):
        """测试SSH命令执行"""
        with app.app_context():
            from app.communication.ssh_client import SSHClient
            
            # 模拟连接和命令执行
            mock_connection = Mock()
            mock_connection.is_alive.return_value = True
            mock_connection.send_command.return_value = "Cisco IOS Software"
            mock_connect.return_value = mock_connection
            
            client = SSHClient(ssh_device)
            client.connect()
            
            result = client.execute_command("show version")
            
            assert result['success'] == True
            assert result['output'] == "Cisco IOS Software"
            assert result['command'] == "show version"
    
    @patch('app.communication.ssh_client.ConnectHandler')
    def test_ssh_config_commands(self, mock_connect, app, ssh_device):
        """测试SSH配置命令发送"""
        with app.app_context():
            from app.communication.ssh_client import SSHClient
            
            # 模拟连接和配置命令执行
            mock_connection = Mock()
            mock_connection.is_alive.return_value = True
            mock_connection.send_config_set.return_value = "配置已应用"
            mock_connect.return_value = mock_connection
            
            client = SSHClient(ssh_device)
            client.connect()
            
            config_commands = ["interface GigabitEthernet0/1", "description Test"]
            result = client.send_config_commands(config_commands)
            
            assert result['success'] == True
            assert result['output'] == "配置已应用"
            assert result['commands'] == config_commands

class TestTelnetClient:
    """Telnet客户端测试"""
    
    @patch('app.communication.telnet_client.telnetlib.Telnet')
    def test_telnet_connection_success(self, mock_telnet, app, telnet_device):
        """测试Telnet连接成功"""
        with app.app_context():
            from app.communication.telnet_client import TelnetClient
            
            # 模拟成功的连接
            mock_telnet_instance = Mock()
            mock_telnet_instance.read_until.side_effect = [
                b"Username:",  # 用户名提示
                b"Password:",  # 密码提示
            ]
            mock_telnet_instance.get_socket.return_value = True
            mock_telnet.return_value = mock_telnet_instance
            
            client = TelnetClient(telnet_device)
            result = client.connect()
            
            assert result['success'] == True
            assert 'Telnet连接建立成功' in result['message']
            assert result['connection_id'] is not None
    
    @patch('app.communication.telnet_client.telnetlib.Telnet')
    def test_telnet_connection_timeout(self, mock_telnet, app, telnet_device):
        """测试Telnet连接超时"""
        with app.app_context():
            from app.communication.telnet_client import TelnetClient
            import socket
            
            # 模拟连接超时
            mock_telnet.side_effect = socket.timeout()
            
            client = TelnetClient(telnet_device)
            result = client.connect()
            
            assert result['success'] == False
            assert 'Telnet连接超时' in result['error']
    
    @patch('app.communication.telnet_client.telnetlib.Telnet')
    def test_telnet_command_execution(self, mock_telnet, app, telnet_device):
        """测试Telnet命令执行"""
        with app.app_context():
            from app.communication.telnet_client import TelnetClient
            
            # 模拟连接和命令执行
            mock_telnet_instance = Mock()
            mock_telnet_instance.read_until.side_effect = [
                b"Username:",
                b"Password:",
            ]
            mock_telnet_instance.get_socket.return_value = True
            mock_telnet_instance.read_very_eager.return_value = b"Cisco IOS Software"
            mock_telnet.return_value = mock_telnet_instance
            
            client = TelnetClient(telnet_device)
            client.connect()
            
            result = client.execute_command("show version")
            
            assert result['success'] == True
            assert "Cisco IOS Software" in result['output']
            assert result['command'] == "show version"

class TestRESTCONFClient:
    """RESTCONF客户端测试"""
    
    @patch('app.communication.restconf_client.requests.Session')
    def test_restconf_connection_success(self, mock_session, app):
        """测试RESTCONF连接成功"""
        with app.app_context():
            from app.communication.restconf_client import RESTCONFClient
            
            # 创建RESTCONF设备
            device = Device(
                name='restconf_device',
                ip_address='192.168.1.3',
                device_type=DeviceType.CISCO_ROUTER,
                connection_type=ConnectionType.RESTCONF,
                port=443,
                username='admin'
            )
            device.set_password('admin123')
            db.session.add(device)
            db.session.commit()
            
            # 模拟成功的连接
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"system": "running"}'
            mock_session_instance = Mock()
            mock_session_instance.get.return_value = mock_response
            mock_session.return_value = mock_session_instance
            
            client = RESTCONFClient(device)
            result = client.connect()
            
            assert result['success'] == True
            assert 'RESTCONF连接建立成功' in result['message']
            assert result['connection_id'] is not None
    
    @patch('app.communication.restconf_client.requests.Session')
    def test_restconf_get_request(self, mock_session, app):
        """测试RESTCONF GET请求"""
        with app.app_context():
            from app.communication.restconf_client import RESTCONFClient
            
            # 创建RESTCONF设备
            device = Device(
                name='restconf_device',
                ip_address='192.168.1.3',
                device_type=DeviceType.CISCO_ROUTER,
                connection_type=ConnectionType.RESTCONF,
                port=443,
                username='admin'
            )
            device.set_password('admin123')
            db.session.add(device)
            db.session.commit()
            
            # 模拟成功的GET请求
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"interfaces": []}
            mock_session_instance = Mock()
            mock_session_instance.get.return_value = mock_response
            mock_session.return_value = mock_session_instance
            
            client = RESTCONFClient(device)
            client.connect()
            
            result = client.get('data/ietf-interfaces:interfaces')
            
            assert result['success'] == True
            assert result['data'] == {"interfaces": []}
            assert result['path'] == 'data/ietf-interfaces:interfaces'

class TestCommunicationRoutes:
    """通信路由测试"""
    
    def test_test_connection_route(self, client, sample_user, ssh_device):
        """测试连接测试路由"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 测试连接（需要mock SSH服务）
        with patch('app.communication.routes.SSHService.test_connection') as mock_test:
            mock_test.return_value = {
                'success': True,
                'message': 'SSH连接测试成功'
            }
            
            response = client.post(f'/communication/test-connection/{ssh_device.id}')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['success'] == True
    
    def test_execute_command_route(self, client, sample_user, ssh_device):
        """测试命令执行路由"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 执行命令（需要mock SSH服务）
        with patch('app.communication.routes.SSHService.execute_command') as mock_execute:
            mock_execute.return_value = {
                'success': True,
                'output': 'Cisco IOS Software',
                'command': 'show version'
            }
            
            response = client.post(f'/communication/execute-command/{ssh_device.id}', 
                                 json={'command': 'show version'})
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['success'] == True
            assert data['output'] == 'Cisco IOS Software'
    
    def test_execute_commands_route(self, client, sample_user, ssh_device):
        """测试批量命令执行路由"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 批量执行命令（需要mock SSH服务）
        with patch('app.communication.routes.SSHService.execute_commands') as mock_execute:
            mock_execute.return_value = [
                {'success': True, 'output': 'Version info', 'command': 'show version'},
                {'success': True, 'output': 'Interface info', 'command': 'show interfaces'}
            ]
            
            response = client.post(f'/communication/execute-commands/{ssh_device.id}', 
                                 json={'commands': ['show version', 'show interfaces']})
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['success'] == True
            assert data['total_commands'] == 2
            assert data['success_count'] == 2
    
    def test_send_config_route(self, client, sample_user, ssh_device):
        """测试配置发送路由"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 发送配置（需要mock SSH服务）
        with patch('app.communication.routes.SSHService.send_config') as mock_send:
            mock_send.return_value = {
                'success': True,
                'output': '配置已应用',
                'commands': ['interface GigabitEthernet0/1', 'description Test']
            }
            
            config_commands = ['interface GigabitEthernet0/1', 'description Test']
            response = client.post(f'/communication/send-config/{ssh_device.id}', 
                                 json={'config_commands': config_commands})
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['success'] == True
            assert data['output'] == '配置已应用'
    
    def test_get_system_info_route(self, client, sample_user, ssh_device):
        """测试获取系统信息路由"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 获取系统信息（需要mock SSH服务）
        with patch('app.communication.routes.SSHService.execute_command') as mock_execute:
            mock_execute.return_value = {
                'success': True,
                'output': 'Cisco IOS Software, Version 15.1(4)M4'
            }
            
            response = client.get(f'/communication/get-system-info/{ssh_device.id}')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['success'] == True
    
    def test_batch_test_connections_route(self, client, sample_user, ssh_device, telnet_device):
        """测试批量连接测试路由"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 批量测试连接（需要mock服务）
        with patch('app.communication.routes.SSHService.test_connection') as mock_ssh, \
             patch('app.communication.routes.TelnetService.test_connection') as mock_telnet:
            
            mock_ssh.return_value = {'success': True, 'message': 'SSH连接测试成功'}
            mock_telnet.return_value = {'success': True, 'message': 'Telnet连接测试成功'}
            
            response = client.post('/communication/batch-test-connections', 
                                 json={'device_ids': [ssh_device.id, telnet_device.id]})
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['success'] == True
            assert data['total_devices'] == 2
            assert data['success_count'] == 2

class TestCommunicationServices:
    """通信服务测试"""
    
    def test_ssh_service_test_connection(self, app, ssh_device):
        """测试SSH服务连接测试"""
        with app.app_context():
            from app.communication.ssh_client import SSHService
            
            with patch('app.communication.ssh_client.ssh_manager.get_connection') as mock_get_connection:
                # 模拟连接和命令执行
                mock_client = Mock()
                mock_client.execute_command.return_value = {
                    'success': True,
                    'output': 'Cisco IOS Software'
                }
                mock_get_connection.return_value.__enter__.return_value = mock_client
                
                result = SSHService.test_connection(ssh_device)
                
                assert result['success'] == True
                assert 'SSH连接测试成功' in result['message']
    
    def test_telnet_service_test_connection(self, app, telnet_device):
        """测试Telnet服务连接测试"""
        with app.app_context():
            from app.communication.telnet_client import TelnetService
            
            with patch('app.communication.telnet_client.telnet_manager.get_connection') as mock_get_connection:
                # 模拟连接和命令执行
                mock_client = Mock()
                mock_client.execute_command.return_value = {
                    'success': True,
                    'output': 'Cisco IOS Software'
                }
                mock_get_connection.return_value.__enter__.return_value = mock_client
                
                result = TelnetService.test_connection(telnet_device)
                
                assert result['success'] == True
                assert 'Telnet连接测试成功' in result['message']
    
    def test_restconf_service_test_connection(self, app):
        """测试RESTCONF服务连接测试"""
        with app.app_context():
            from app.communication.restconf_client import RESTCONFService
            
            # 创建RESTCONF设备
            device = Device(
                name='restconf_device',
                ip_address='192.168.1.3',
                device_type=DeviceType.CISCO_ROUTER,
                connection_type=ConnectionType.RESTCONF,
                port=443,
                username='admin'
            )
            device.set_password('admin123')
            db.session.add(device)
            db.session.commit()
            
            with patch('app.communication.restconf_client.restconf_manager.get_connection') as mock_get_connection:
                # 模拟连接和GET请求
                mock_client = Mock()
                mock_client.get.return_value = {
                    'success': True,
                    'data': {'system': 'running'}
                }
                mock_get_connection.return_value = mock_client
                
                result = RESTCONFService.test_connection(device)
                
                assert result['success'] == True
                assert 'RESTCONF连接测试成功' in result['message']
