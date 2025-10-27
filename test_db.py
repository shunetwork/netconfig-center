#!/usr/bin/env python3
"""
数据库测试脚本
用于测试数据库模型和基本功能
"""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app import create_app, db
from app.models import *

def test_database():
    """测试数据库功能"""
    app = create_app('development')
    
    with app.app_context():
        print("正在测试数据库...")
        
        # 创建所有表
        print("创建数据库表...")
        db.create_all()
        
        # 创建默认角色
        print("创建默认角色...")
        User.create_default_roles()
        
        # 创建默认模板分类
        print("创建默认模板分类...")
        TemplateCategory.create_default_categories()
        
        # 创建默认管理员用户
        print("创建默认管理员用户...")
        admin_user = User.create_admin_user()
        
        # 创建测试设备组
        print("创建测试设备组...")
        test_group = DeviceGroup(name='测试设备组', description='用于测试的设备组')
        db.session.add(test_group)
        db.session.commit()
        
        # 创建测试设备
        print("创建测试设备...")
        test_device = Device(
            name='测试交换机',
            ip_address='192.168.1.100',
            hostname='test-switch',
            username='admin',
            group=test_group
        )
        test_device.set_password('admin123')
        db.session.add(test_device)
        db.session.commit()
        
        # 创建测试配置模板
        print("创建测试配置模板...")
        test_template = ConfigTemplate(
            name='基础接口配置',
            description='基础接口配置模板',
            category='interface',
            template_content='''interface {{ interface_name }}
 description {{ description }}
 ip address {{ ip_address }} {{ subnet_mask }}
 no shutdown'''
        )
        db.session.add(test_template)
        db.session.commit()
        
        # 添加模板变量
        test_template.add_variable('interface_name', 'string', '接口名称', 'GigabitEthernet0/1', True)
        test_template.add_variable('description', 'string', '接口描述', '', False)
        test_template.add_variable('ip_address', 'string', 'IP地址', '', True)
        test_template.add_variable('subnet_mask', 'string', '子网掩码', '', True)
        db.session.commit()
        
        # 创建测试任务
        print("创建测试任务...")
        test_task = Task(
            name='测试命令执行',
            description='执行show version命令',
            task_type=TaskType.COMMAND,
            command='show version',
            user=admin_user,
            device=test_device
        )
        db.session.add(test_task)
        db.session.commit()
        
        # 测试模板渲染
        print("测试模板渲染...")
        variables = {
            'interface_name': 'GigabitEthernet0/1',
            'description': '测试接口',
            'ip_address': '192.168.1.1',
            'subnet_mask': '255.255.255.0'
        }
        rendered_config = test_template.render_template(variables)
        print("渲染的配置:")
        print(rendered_config)
        
        # 创建配置备份
        print("创建配置备份...")
        backup = ConfigBackup(
            name='测试配置备份',
            description='测试设备的配置备份',
            config_content=rendered_config,
            user=admin_user,
            device=test_device
        )
        backup.calculate_hash()
        db.session.add(backup)
        db.session.commit()
        
        # 记录审计日志
        print("记录审计日志...")
        AuditLog.log_action(
            user=admin_user,
            action='test_action',
            resource_type='device',
            resource_id=test_device.id,
            resource_name=test_device.name,
            success=True
        )
        
        # 查询和显示结果
        print("\n=== 数据库测试结果 ===")
        print(f"用户数量: {User.query.count()}")
        print(f"角色数量: {Role.query.count()}")
        print(f"设备数量: {Device.query.count()}")
        print(f"设备组数量: {DeviceGroup.query.count()}")
        print(f"配置模板数量: {ConfigTemplate.query.count()}")
        print(f"任务数量: {Task.query.count()}")
        print(f"配置备份数量: {ConfigBackup.query.count()}")
        print(f"审计日志数量: {AuditLog.query.count()}")
        
        print("\n=== 管理员用户信息 ===")
        print(f"用户名: {admin_user.username}")
        print(f"邮箱: {admin_user.email}")
        print(f"角色: {admin_user.role.name}")
        print(f"是否为管理员: {admin_user.is_admin}")
        
        print("\n=== 测试设备信息 ===")
        print(f"设备名: {test_device.name}")
        print(f"IP地址: {test_device.ip_address}")
        print(f"设备组: {test_device.group.name}")
        
        print("\n=== 配置模板信息 ===")
        print(f"模板名: {test_template.name}")
        print(f"分类: {test_template.category}")
        print(f"变量数量: {test_template.variables.count()}")
        
        print("\n数据库测试完成！")

if __name__ == '__main__':
    test_database()
