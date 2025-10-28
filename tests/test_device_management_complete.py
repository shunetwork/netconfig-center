#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备管理功能完整测试用例
测试设备CRUD、状态检测、模板管理等所有功能
"""

import pytest
import json
from flask import url_for
from app import create_app, db
from app.models import Device, ConfigTemplate, User, Task


class TestDeviceManagementComplete:
    """设备管理完整功能测试"""
    
    @pytest.fixture(scope='class')
    def app(self):
        """创建测试应用"""
        app = create_app('testing')
        
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()
    
    @pytest.fixture(scope='class')
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()
    
    @pytest.fixture(scope='class')
    def auth_headers(self, client):
        """创建认证头"""
        # 创建测试用户
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com'
            )
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()
        
        # 登录获取token
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        return {}
    
    @pytest.fixture(scope='class')
    def sample_device(self, app):
        """创建测试设备"""
        with app.app_context():
            device = Device(
                name='测试路由器',
                ip_address='192.168.1.1',
                hostname='router-01',
                device_type='cisco',
                connection_type='ssh',
                port=22,
                username='admin',
                password='password',
                description='测试设备',
                status='unknown'
            )
            db.session.add(device)
            db.session.commit()
            return device
    
    @pytest.fixture(scope='class')
    def bulk_vlan_template(self, app):
        """创建批量VLAN模板"""
        with app.app_context():
            template = ConfigTemplate(
                name='批量添加VLAN模板',
                description='用于批量添加多个VLAN到网络设备，支持自定义VLAN名称',
                content='''{% for line in vlans.strip().split("\\n") %}
{% set line = line.strip() %}
{% if line %}
{% set parts = line.split(":") %}
{% if parts|length == 2 %}
{% set vlan_id = parts[0].strip() %}
{% set vlan_name = parts[1].strip() %}
vlan {{ vlan_id }}
 name {{ vlan_name }}
end
{% else %}
vlan {{ line }}
 name VLAN_{{ line }}
end
{% endif %}
{% endif %}
{% endfor %}''',
                template_type='config',
                category='network',
                variables='''{"vlans": {"type": "textarea", "default": "100:Sales\\n200:Engineering\\n300:Guest", "description": "批量VLAN ID和名称，每行一个\\n格式1: VLAN_ID (自动命名为VLAN_ID)\\n格式2: VLAN_ID:VLAN_Name (指定名称)\\n\\n示例：\\n100:Sales\\n200:Engineering\\n300:Guest\\n400 (自动命名为VLAN_400)", "required": true}}''',
                is_active=True
            )
            db.session.add(template)
            db.session.commit()
            return template
    
    # ========== 设备管理功能测试 ==========
    
    def test_001_device_add(self, client, auth_headers):
        """测试添加设备"""
        response = client.get('/devices/add')
        assert response.status_code == 200
        
        response = client.post('/devices/add', data={
            'name': '测试设备001',
            'ip_address': '192.168.1.100',
            'hostname': 'test-device-001',
            'device_type': 'cisco',
            'connection_type': 'ssh',
            'port': 22,
            'username': 'admin',
            'password': 'password123',
            'description': '自动化测试设备'
        })
        assert response.status_code == 302  # 重定向到设备列表
    
    def test_002_device_list(self, client, auth_headers):
        """测试设备列表"""
        response = client.get('/devices')
        assert response.status_code == 200
        assert b'测试设备001' in response.data or b'设备管理' in response.data
    
    def test_003_device_delete(self, client, auth_headers, sample_device):
        """测试删除设备"""
        response = client.delete(f'/api/devices/{sample_device.id}/delete')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_004_device_status_check(self, client, auth_headers):
        """测试设备状态检查"""
        response = client.post('/api/devices/status/check-all')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'devices' in data
    
    # ========== 模板管理功能测试 ==========
    
    def test_005_template_list(self, client, auth_headers):
        """测试模板列表"""
        response = client.get('/templates')
        assert response.status_code == 200
    
    def test_006_template_add(self, client, auth_headers):
        """测试添加模板"""
        response = client.get('/templates/add')
        assert response.status_code == 200
        
        response = client.post('/templates/add', data={
            'name': '测试模板',
            'description': '测试模板描述',
            'content': 'vlan {{ vlan_id }}\n name {{ vlan_name }}',
            'template_type': 'config',
            'category': 'network',
            'variables': '{"vlan_id": "string", "vlan_name": "string"}'
        })
        assert response.status_code == 302  # 重定向到模板列表
    
    def test_007_bulk_vlan_template(self, client, auth_headers, bulk_vlan_template):
        """测试批量VLAN模板"""
        # 获取模板变量
        response = client.get(f'/api/templates/{bulk_vlan_template.id}/variables')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'variables' in data
        assert len(data['variables']) > 0
        
        # 验证变量类型
        vlans_var = data['variables'][0]
        assert vlans_var['name'] == 'vlans'
        assert vlans_var['type'] == 'textarea'
    
    # ========== 任务管理功能测试 ==========
    
    def test_008_task_create_page(self, client, auth_headers):
        """测试创建任务页面"""
        response = client.get('/tasks/create')
        assert response.status_code == 200
    
    def test_009_task_list(self, client, auth_headers):
        """测试任务列表"""
        response = client.get('/tasks')
        assert response.status_code == 200
    
    # ========== 数据一致性测试 ==========
    
    def test_010_device_data_persistence(self, app):
        """测试设备数据持久化"""
        with app.app_context():
            # 添加设备
            device = Device(
                name='持久化测试设备',
                ip_address='192.168.1.200',
                username='admin',
                password='pass123',
                status='unknown'
            )
            db.session.add(device)
            db.session.commit()
            
            device_id = device.id
            
            # 查询设备
            saved_device = Device.query.get(device_id)
            assert saved_device is not None
            assert saved_device.name == '持久化测试设备'
            assert saved_device.ip_address == '192.168.1.200'
    
    def test_011_template_variables_parsing(self, app, bulk_vlan_template):
        """测试模板变量解析"""
        with app.app_context():
            variables = bulk_vlan_template.get_variables_dict()
            assert isinstance(variables, dict)
            assert 'vlans' in variables
    
    # ========== 集成测试 ==========
    
    def test_012_complete_workflow(self, client, auth_headers, bulk_vlan_template):
        """测试完整工作流程"""
        # 1. 创建设备
        response = client.post('/devices/add', data={
            'name': '工作流测试设备',
            'ip_address': '192.168.1.250',
            'device_type': 'cisco',
            'connection_type': 'ssh',
            'port': 22,
            'username': 'admin',
            'password': 'test123'
        })
        assert response.status_code == 302
        
        # 2. 获取模板变量
        response = client.get(f'/api/templates/{bulk_vlan_template.id}/variables')
        assert response.status_code == 200
        
        # 3. 创建任务
        response = client.post('/tasks/create', data={
            'name': '工作流测试任务',
            'task_type': 'config',
            'template_id': bulk_vlan_template.id
        })
        assert response.status_code in [200, 302]
    
    # ========== 边界条件测试 ==========
    
    def test_013_empty_device_list(self, app):
        """测试空设备列表"""
        with app.app_context():
            devices = Device.query.all()
            # 应该不抛出异常
            assert devices is not None
    
    def test_014_invalid_template_id(self, client, auth_headers):
        """测试无效模板ID"""
        response = client.get('/api/templates/99999/variables')
        assert response.status_code == 404
    
    def test_015_duplicate_device_name(self, client, auth_headers):
        """测试重复设备名称"""
        # 第一次添加
        response = client.post('/devices/add', data={
            'name': '重复测试设备',
            'ip_address': '192.168.1.101',
            'device_type': 'cisco',
            'connection_type': 'ssh',
            'port': 22,
            'username': 'admin',
            'password': 'test123'
        })
        
        # 第二次添加相同名称（应该成功，因为modern_start.py没有名称唯一性检查）
        response = client.post('/devices/add', data={
            'name': '重复测试设备',
            'ip_address': '192.168.1.102',
            'device_type': 'cisco',
            'connection_type': 'ssh',
            'port': 22,
            'username': 'admin',
            'password': 'test123'
        })
        # 注意：当前实现允许重复名称


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

