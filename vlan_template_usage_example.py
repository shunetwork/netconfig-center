#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLAN模板使用示例
演示如何使用批量VLAN模板
"""

import requests
import json

def demonstrate_vlan_template_usage():
    """演示VLAN模板的使用方法"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== NetManagerX VLAN模板使用演示 ===")
    
    # 1. 登录系统
    print("\n1. 登录系统...")
    login_data = {'username': 'admin', 'password': 'admin123'}
    session.post(f"{base_url}/login", data=login_data)
    print("登录成功")
    
    # 2. 获取模板列表
    print("\n2. 获取VLAN相关模板...")
    templates_response = session.get(f"{base_url}/templates")
    if templates_response.status_code == 200:
        print("模板列表获取成功")
        # 这里可以解析HTML来找到VLAN模板，但为了简化，我们直接演示用法
    else:
        print("获取模板列表失败")
        return
    
    print("\n=== VLAN模板使用说明 ===")
    
    # 3. 演示批量添加VLAN的用法
    print("\n3. 批量添加VLAN模板使用示例:")
    print("模板名称: 批量添加VLAN模板")
    print("模板类型: 配置模板")
    print("分类: 网络")
    
    print("\n变量定义:")
    vlan_variables = {
        "vlans": [
            {
                "id": 10,
                "name": "Management",
                "description": "管理VLAN",
                "ip_address": "192.168.10.1",
                "subnet_mask": "255.255.255.0"
            },
            {
                "id": 20,
                "name": "Staff",
                "description": "员工VLAN",
                "ip_address": "192.168.20.1",
                "subnet_mask": "255.255.255.0"
            },
            {
                "id": 30,
                "name": "Guest",
                "description": "访客VLAN"
            },
            {
                "id": 40,
                "name": "Server",
                "description": "服务器VLAN",
                "ip_address": "192.168.40.1",
                "subnet_mask": "255.255.255.0"
            }
        ]
    }
    
    print("示例变量数据:")
    print(json.dumps(vlan_variables, indent=2, ensure_ascii=False))
    
    print("\n渲染后的配置:")
    rendered_config = '''! 批量添加VLAN配置
vlan 10
 name Management
 description 管理VLAN
interface Vlan10
 ip address 192.168.10.1 255.255.255.0
 no shutdown
vlan 20
 name Staff
 description 员工VLAN
interface Vlan20
 ip address 192.168.20.1 255.255.255.0
 no shutdown
vlan 30
 name Guest
 description 访客VLAN
vlan 40
 name Server
 description 服务器VLAN
interface Vlan40
 ip address 192.168.40.1 255.255.255.0
 no shutdown
! 保存配置
write memory'''
    
    print(rendered_config)
    
    # 4. 演示VLAN删除模板
    print("\n4. VLAN删除模板使用示例:")
    print("模板名称: 批量删除VLAN模板")
    
    delete_variables = {
        "vlan_ids": [10, 20, 30]
    }
    
    print("删除VLAN示例数据:")
    print(json.dumps(delete_variables, indent=2, ensure_ascii=False))
    
    print("\n渲染后的删除配置:")
    delete_config = '''! 批量删除VLAN配置
no vlan 10
no vlan 20
no vlan 30
! 保存配置
write memory'''
    
    print(delete_config)
    
    # 5. 演示VLAN查看模板
    print("\n5. VLAN查看模板使用示例:")
    print("模板名称: VLAN信息查看模板")
    print("模板类型: 脚本模板")
    
    print("\n查看VLAN配置命令:")
    view_commands = '''! 查看VLAN配置信息
show vlan brief
show vlan
show interfaces vlan
show ip interface brief'''
    
    print(view_commands)
    
    print("\n=== 使用步骤 ===")
    print("1. 访问 http://localhost:5001/templates")
    print("2. 找到'批量添加VLAN模板'")
    print("3. 点击'预览'按钮查看模板内容")
    print("4. 点击'应用'按钮使用模板")
    print("5. 输入VLAN配置数据")
    print("6. 生成配置并应用到设备")
    
    print("\n=== 模板特点 ===")
    print("- 支持批量创建多个VLAN")
    print("- 每个VLAN可配置ID、名称、描述")
    print("- 可选配置VLAN接口IP地址")
    print("- 自动保存配置")
    print("- 支持VLAN删除操作")
    print("- 提供VLAN查看命令")
    print("- 使用Jinja2模板语法，灵活可扩展")

def create_advanced_vlan_template():
    """创建高级VLAN模板"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    # 登录
    session.post(f"{base_url}/login", data={'username': 'admin', 'password': 'admin123'})
    
    print("\n=== 创建高级VLAN模板 ===")
    
    # 创建高级VLAN配置模板
    advanced_template = {
        'name': '高级VLAN配置模板',
        'description': '支持VLAN、接口配置、路由、ACL等完整网络配置',
        'content': '''! 高级VLAN配置模板
{% for vlan in vlans %}
! 创建VLAN {{ vlan.id }} - {{ vlan.name }}
vlan {{ vlan.id }}
 name {{ vlan.name }}
{% if vlan.description %}
 description {{ vlan.description }}
{% endif %}
{% if vlan.ip_address %}
! 配置VLAN接口
interface Vlan{{ vlan.id }}
 ip address {{ vlan.ip_address }} {{ vlan.subnet_mask }}
{% if vlan.helper_address %}
 ip helper-address {{ vlan.helper_address }}
{% endif %}
{% if vlan.access_list %}
 ip access-group {{ vlan.access_list }} in
{% endif %}
 no shutdown
{% endif %}
{% endfor %}

{% if routing %}
! 配置路由
{% for route in routing %}
ip route {{ route.network }} {{ route.mask }} {{ route.next_hop }}
{% endfor %}
{% endif %}

{% if acls %}
! 配置ACL
{% for acl in acls %}
access-list {{ acl.number }} {{ acl.action }} {{ acl.protocol }} {{ acl.source }} {{ acl.destination }} {{ acl.port }}
{% endfor %}
{% endif %}

! 保存配置
write memory''',
        'template_type': 'config',
        'category': 'network',
        'variables': '''{
  "vlans": {
    "type": "array",
    "description": "VLAN配置列表",
    "items": {
      "type": "object",
      "properties": {
        "id": {"type": "integer", "description": "VLAN ID"},
        "name": {"type": "string", "description": "VLAN名称"},
        "description": {"type": "string", "description": "VLAN描述"},
        "ip_address": {"type": "string", "description": "VLAN接口IP"},
        "subnet_mask": {"type": "string", "description": "子网掩码"},
        "helper_address": {"type": "string", "description": "DHCP中继地址"},
        "access_list": {"type": "string", "description": "访问控制列表"}
      },
      "required": ["id", "name"]
    }
  },
  "routing": {
    "type": "array",
    "description": "路由配置",
    "items": {
      "type": "object",
      "properties": {
        "network": {"type": "string", "description": "目标网络"},
        "mask": {"type": "string", "description": "子网掩码"},
        "next_hop": {"type": "string", "description": "下一跳地址"}
      }
    }
  },
  "acls": {
    "type": "array",
    "description": "访问控制列表",
    "items": {
      "type": "object",
      "properties": {
        "number": {"type": "integer", "description": "ACL编号"},
        "action": {"type": "string", "description": "动作(permit/deny)"},
        "protocol": {"type": "string", "description": "协议"},
        "source": {"type": "string", "description": "源地址"},
        "destination": {"type": "string", "description": "目标地址"},
        "port": {"type": "string", "description": "端口"}
      }
    }
  }
}'''
    }
    
    response = session.post(f"{base_url}/templates/add", data=advanced_template)
    if response.status_code == 302:
        print("高级VLAN模板创建成功！")
    else:
        print(f"高级VLAN模板创建失败: {response.status_code}")

if __name__ == "__main__":
    demonstrate_vlan_template_usage()
    create_advanced_vlan_template()
