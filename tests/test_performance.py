"""
性能测试用例
测试系统在高负载和大数据量下的性能表现
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

class TestDatabasePerformance:
    """数据库性能测试"""
    
    def test_device_bulk_insert_performance(self, app, sample_user):
        """测试设备批量插入性能"""
        with app.app_context():
            start_time = time.time()
            
            # 批量创建设备
            devices = []
            for i in range(100):
                device = Device(
                    name=f'device_{i}',
                    ip_address=f'192.168.1.{i+1}',
                    device_type='cisco_switch',
                    connection_type='ssh',
                    username='admin'
                )
                device.set_password('admin123')
                devices.append(device)
            
            db.session.add_all(devices)
            db.session.commit()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 验证性能要求：100个设备插入应在5秒内完成
            assert execution_time < 5.0
            assert Device.query.count() == 100
    
    def test_device_query_performance(self, app, sample_user):
        """测试设备查询性能"""
        with app.app_context():
            # 创建大量设备数据
            devices = []
            for i in range(1000):
                device = Device(
                    name=f'device_{i}',
                    ip_address=f'192.168.1.{i+1}',
                    device_type='cisco_switch',
                    connection_type='ssh',
                    username='admin'
                )
                device.set_password('admin123')
                devices.append(device)
            
            db.session.add_all(devices)
            db.session.commit()
            
            # 测试简单查询性能
            start_time = time.time()
            devices = Device.query.filter_by(device_type='cisco_switch').limit(100).all()
            end_time = time.time()
            query_time = end_time - start_time
            
            # 验证查询性能：100条记录查询应在0.1秒内完成
            assert query_time < 0.1
            assert len(devices) == 100
            
            # 测试复杂查询性能
            start_time = time.time()
            devices = Device.query.filter(
                Device.device_type == 'cisco_switch',
                Device.connection_type == 'ssh'
            ).order_by(Device.name).limit(50).all()
            end_time = time.time()
            complex_query_time = end_time - start_time
            
            # 验证复杂查询性能：50条记录查询应在0.2秒内完成
            assert complex_query_time < 0.2
            assert len(devices) == 50
    
    def test_audit_log_performance(self, app, sample_user):
        """测试审计日志性能"""
        with app.app_context():
            # 批量创建审计日志
            start_time = time.time()
            
            logs = []
            for i in range(500):
                log = AuditLog(
                    user=sample_user,
                    action=f'action_{i}',
                    resource_type='device',
                    resource_id=i,
                    resource_name=f'device_{i}',
                    success=True
                )
                logs.append(log)
            
            db.session.add_all(logs)
            db.session.commit()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 验证性能要求：500条审计日志插入应在3秒内完成
            assert execution_time < 3.0
            assert AuditLog.query.count() == 500
            
            # 测试审计日志查询性能
            start_time = time.time()
            logs = AuditLog.query.filter_by(user=sample_user).order_by(AuditLog.timestamp.desc()).limit(100).all()
            end_time = time.time()
            query_time = end_time - start_time
            
            # 验证查询性能：100条记录查询应在0.1秒内完成
            assert query_time < 0.1
            assert len(logs) == 100

class TestConcurrentPerformance:
    """并发性能测试"""
    
    def test_concurrent_device_creation(self, app, sample_user):
        """测试并发设备创建性能"""
        with app.app_context():
            def create_device(device_id):
                """创建单个设备的函数"""
                device = Device(
                    name=f'concurrent_device_{device_id}',
                    ip_address=f'192.168.1.{device_id+1}',
                    device_type='cisco_switch',
                    connection_type='ssh',
                    username='admin'
                )
                device.set_password('admin123')
                return device
            
            start_time = time.time()
            
            # 使用线程池并发创建设备
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(create_device, i) for i in range(50)]
                devices = [future.result() for future in as_completed(futures)]
            
            # 批量提交到数据库
            db.session.add_all(devices)
            db.session.commit()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 验证并发性能：50个设备并发创建应在2秒内完成
            assert execution_time < 2.0
            assert Device.query.count() == 50
    
    def test_concurrent_task_execution(self, app, sample_user):
        """测试并发任务执行性能"""
        with app.app_context():
            # 创建测试设备
            device = Device(
                name='concurrent_test_device',
                ip_address='192.168.1.1',
                device_type='cisco_switch',
                connection_type='ssh',
                username='admin'
            )
            device.set_password('admin123')
            db.session.add(device)
            db.session.commit()
            
            def create_task(task_id):
                """创建单个任务的函数"""
                task = Task(
                    name=f'concurrent_task_{task_id}',
                    task_type='command',
                    command='show version',
                    user=sample_user,
                    device=device
                )
                return task
            
            start_time = time.time()
            
            # 使用线程池并发创建任务
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(create_task, i) for i in range(20)]
                tasks = [future.result() for future in as_completed(futures)]
            
            # 批量提交到数据库
            db.session.add_all(tasks)
            db.session.commit()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 验证并发性能：20个任务并发创建应在1秒内完成
            assert execution_time < 1.0
            assert Task.query.count() == 20
    
    def test_concurrent_api_requests(self, app, client, sample_user):
        """测试并发API请求性能"""
        # 登录用户
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        def make_api_request():
            """发起API请求的函数"""
            response = client.get('/api/stats')
            return response.status_code == 200
        
        start_time = time.time()
        
        # 使用线程池并发发起API请求
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_api_request) for _ in range(100)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证并发性能：100个API请求应在3秒内完成
        assert execution_time < 3.0
        assert all(results)  # 所有请求都应该成功

class TestMemoryPerformance:
    """内存性能测试"""
    
    def test_large_dataset_memory_usage(self, app, sample_user):
        """测试大数据集内存使用"""
        with app.app_context():
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 创建大量数据
            devices = []
            for i in range(1000):
                device = Device(
                    name=f'large_dataset_device_{i}',
                    ip_address=f'192.168.1.{i+1}',
                    device_type='cisco_switch',
                    connection_type='ssh',
                    username='admin'
                )
                device.set_password('admin123')
                devices.append(device)
            
            db.session.add_all(devices)
            db.session.commit()
            
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            # 验证内存使用：1000个设备不应超过50MB内存
            assert memory_increase < 50
            
            # 测试查询大数据集
            devices = Device.query.all()
            query_memory = process.memory_info().rss / 1024 / 1024  # MB
            query_memory_increase = query_memory - peak_memory
            
            # 验证查询内存使用：查询1000个设备不应超过30MB内存
            assert query_memory_increase < 30
    
    def test_template_rendering_memory_usage(self, app):
        """测试模板渲染内存使用"""
        with app.app_context():
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 创建大型模板
            template_content = 'hostname {{ hostname }}\n' * 1000  # 1000行模板
            template = ConfigTemplate(
                name='large_template',
                category='large',
                template_content=template_content
            )
            db.session.add(template)
            db.session.commit()
            
            # 测试模板渲染
            variables = {'hostname': 'test-switch'}
            from app.templates.services import TemplateService
            
            for i in range(100):
                result = TemplateService.render_template(template, variables)
                assert result['success'] == True
            
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            # 验证内存使用：100次模板渲染不应超过20MB内存
            assert memory_increase < 20

class TestResponseTimePerformance:
    """响应时间性能测试"""
    
    def test_api_response_time(self, app, client, sample_user):
        """测试API响应时间"""
        # 登录用户
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 测试各种API端点的响应时间
        endpoints = [
            '/api/stats',
            '/api/devices',
            '/api/tasks',
            '/api/templates'
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            response_time = end_time - start_time
            
            # 验证响应时间：API请求应在0.5秒内完成
            assert response_time < 0.5
            assert response.status_code == 200
    
    def test_page_load_time(self, app, client, sample_user):
        """测试页面加载时间"""
        # 登录用户
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # 测试各种页面的加载时间
        pages = [
            '/',
            '/devices/',
            '/templates/',
            '/tasks/',
            '/devices/add',
            '/templates/add'
        ]
        
        for page in pages:
            start_time = time.time()
            response = client.get(page)
            end_time = time.time()
            load_time = end_time - start_time
            
            # 验证加载时间：页面加载应在1秒内完成
            assert load_time < 1.0
            assert response.status_code == 200
    
    def test_database_query_response_time(self, app, sample_user):
        """测试数据库查询响应时间"""
        with app.app_context():
            # 创建测试数据
            devices = []
            for i in range(100):
                device = Device(
                    name=f'response_test_device_{i}',
                    ip_address=f'192.168.1.{i+1}',
                    device_type='cisco_switch',
                    connection_type='ssh',
                    username='admin'
                )
                device.set_password('admin123')
                devices.append(device)
            
            db.session.add_all(devices)
            db.session.commit()
            
            # 测试各种查询的响应时间
            queries = [
                lambda: Device.query.all(),
                lambda: Device.query.filter_by(device_type='cisco_switch').all(),
                lambda: Device.query.filter(Device.name.like('%test%')).all(),
                lambda: Device.query.order_by(Device.name).limit(50).all()
            ]
            
            for query in queries:
                start_time = time.time()
                result = query()
                end_time = time.time()
                query_time = end_time - start_time
                
                # 验证查询时间：数据库查询应在0.2秒内完成
                assert query_time < 0.2
                assert len(result) > 0

class TestStressPerformance:
    """压力测试"""
    
    def test_high_concurrent_users(self, app, client):
        """测试高并发用户"""
        def simulate_user_session(user_id):
            """模拟用户会话"""
            # 登录
            response = client.post('/auth/login', data={
                'username': 'admin',
                'password': 'admin123'
            })
            
            if response.status_code == 200:
                # 访问几个页面
                pages = ['/', '/devices/', '/templates/', '/tasks/']
                for page in pages:
                    response = client.get(page)
                    if response.status_code != 200:
                        return False
                
                # 登出
                client.get('/auth/logout')
                return True
            return False
        
        start_time = time.time()
        
        # 模拟50个并发用户
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(simulate_user_session, i) for i in range(50)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证压力测试：50个并发用户会话应在10秒内完成
        assert execution_time < 10.0
        assert sum(results) >= 45  # 至少90%的用户会话应该成功
    
    def test_continuous_operations(self, app, sample_user):
        """测试连续操作性能"""
        with app.app_context():
            start_time = time.time()
            
            # 连续执行1000个操作
            for i in range(1000):
                # 创建设备
                device = Device(
                    name=f'continuous_device_{i}',
                    ip_address=f'192.168.1.{i+1}',
                    device_type='cisco_switch',
                    connection_type='ssh',
                    username='admin'
                )
                device.set_password('admin123')
                db.session.add(device)
                
                # 每100个操作提交一次
                if i % 100 == 0:
                    db.session.commit()
            
            db.session.commit()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 验证连续操作性能：1000个操作应在30秒内完成
            assert execution_time < 30.0
            assert Device.query.count() == 1000
