#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建批量添加VLAN模板的脚本
"""

import requests
import json
import time

def create_bulk_vlan_template():
    """创建批量添加VLAN模板"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== 创建批量添加VLAN模板 ===")
    
    # 1. 登录系统
    print("\n1. 登录系统...")
    login_data = {'username': 'admin', 'password': 'admin123'}
    login_response = session.post(f"{base_url}/login", data=login_data)
    if login_response.status_code in [200, 302]:
        print("登录成功")
    else:
        print("登录失败")
        return
    
    # 2. 创建批量VLAN模板
    print("\n2. 创建批量VLAN模板...")
    template_data = {
        'name': '批量添加VLAN模板',
        'description': '用于批量创建VLAN的配置模板，支持多个VLAN同时创建',
        'content': '''! 批量添加VLAN配置
{% for vlan in vlans %}
vlan {{ vlan.id }}
 name {{ vlan.name }}
{% if vlan.description %}
 description {{ vlan.description }}
{% endif %}
{% if vlan.ip_address %}
interface Vlan{{ vlan.id }}
 ip address {{ vlan.ip_address }} {{ vlan.subnet_mask }}
 no shutdown
{% endif %}
{% endfor %}
! 保存配置
write memory''',
        'template_type': 'config',
        'category': 'network',
        'variables': '''{
  "vlans": {
    "type": "array",
    "description": "VLAN列表",
    "items": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "description": "VLAN ID (1-4094)",
          "minimum": 1,
          "maximum": 4094
        },
        "name": {
          "type": "string",
          "description": "VLAN名称"
        },
        "description": {
          "type": "string",
          "description": "VLAN描述（可选）"
        },
        "ip_address": {
          "type": "string",
          "description": "VLAN接口IP地址（可选）"
        },
        "subnet_mask": {
          "type": "string",
          "description": "子网掩码（可选）"
        }
      },
      "required": ["id", "name"]
    }
  }
}'''
    }
    
    submit_response = session.post(f"{base_url}/templates/add", data=template_data)
    print(f"提交响应状态码: {submit_response.status_code}")
    
    if submit_response.status_code == 302:
        print("批量VLAN模板创建成功！")
        print("模板功能说明:")
        print("- 支持批量创建多个VLAN")
        print("- 每个VLAN可配置ID、名称、描述")
        print("- 可选配置VLAN接口IP地址")
        print("- 自动保存配置")
    else:
        print(f"模板创建失败: {submit_response.status_code}")
        print(f"响应内容: {submit_response.text[:500]}")
    
    # 3. 创建VLAN删除模板
    print("\n3. 创建VLAN删除模板...")
    delete_template_data = {
        'name': '批量删除VLAN模板',
        'description': '用于批量删除VLAN的配置模板',
        'content': '''! 批量删除VLAN配置
{% for vlan_id in vlan_ids %}
no vlan {{ vlan_id }}
{% endfor %}
! 保存配置
write memory''',
        'template_type': 'config',
        'category': 'network',
        'variables': '''{
  "vlan_ids": {
    "type": "array",
    "description": "要删除的VLAN ID列表",
    "items": {
      "type": "integer",
      "description": "VLAN ID",
      "minimum": 1,
      "maximum": 4094
    }
  }
}'''
    }
    
    delete_response = session.post(f"{base_url}/templates/add", data=delete_template_data)
    if delete_response.status_code == 302:
        print("VLAN删除模板创建成功！")
    else:
        print(f"VLAN删除模板创建失败: {delete_response.status_code}")
    
    # 4. 创建VLAN查看模板
    print("\n4. 创建VLAN查看模板...")
    view_template_data = {
        'name': 'VLAN信息查看模板',
        'description': '用于查看VLAN配置信息的命令模板',
        'content': '''! 查看VLAN配置信息
show vlan brief
show vlan
show interfaces vlan
show ip interface brief''',
        'template_type': 'script',
        'category': 'network',
        'variables': '{}'
    }
    
    view_response = session.post(f"{base_url}/templates/add", data=view_template_data)
    if view_response.status_code == 302:
        print("VLAN查看模板创建成功！")
    else:
        print(f"VLAN查看模板创建失败: {view_response.status_code}")
    
    print("\n=== 模板创建完成 ===")
    print("已创建的VLAN相关模板:")
    print("1. 批量添加VLAN模板 - 用于批量创建VLAN")
    print("2. 批量删除VLAN模板 - 用于批量删除VLAN")
    print("3. VLAN信息查看模板 - 用于查看VLAN配置")

def test_vlan_template():
    """测试VLAN模板的使用"""
    print("\n=== VLAN模板使用示例 ===")
    
    # 批量添加VLAN的示例数据
    vlan_example = {
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
            }
        ]
    }
    
    print("批量添加VLAN示例数据:")
    print(json.dumps(vlan_example, indent=2, ensure_ascii=False))
    
    # 渲染后的配置示例
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
! 保存配置
write memory'''
    
    print("\n渲染后的配置:")
    print(rendered_config)

if __name__ == "__main__":
    create_bulk_vlan_template()
    test_vlan_template()
