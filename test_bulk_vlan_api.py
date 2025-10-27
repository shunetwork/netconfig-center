#!/usr/bin/env python3
"""测试批量VLAN模板API"""

import requests
import json

BASE_URL = "http://localhost:5001"

# 创建会话
session = requests.Session()

def login():
    """登录系统"""
    response = session.post(f"{BASE_URL}/login", data={
        'username': 'admin',
        'password': 'admin123'
    })
    return response.status_code in [200, 302]

def test_vlan_template():
    """测试VLAN模板"""
    print("=== 测试批量VLAN模板 ===")
    
    # 1. 登录
    print("\n1. 登录系统...")
    if not login():
        print("登录失败！")
        return
    print("登录成功！")
    
    # 2. 获取所有模板
    print("\n2. 获取所有模板...")
    response = session.get(f"{BASE_URL}/templates")
    print(f"状态码: {response.status_code}")
    
    # 3. 查找VLAN模板
    print("\n3. 查找批量VLAN模板...")
    # 使用ID 33（支持VLAN名称的版本）
    template_id = 33
    
    # 4. 获取模板变量
    print(f"\n4. 获取模板ID {template_id} 的变量定义...")
    response = session.get(f"{BASE_URL}/api/templates/{template_id}/variables")
    print(f"状态码: {response.status_code}")
    print(f"响应头 Content-Type: {response.headers.get('Content-Type')}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print("JSON响应:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if data.get('success'):
                variables = data.get('variables', [])
                print(f"\n变量数量: {len(variables)}")
                for var in variables:
                    print(f"  变量名: {var.get('name')}")
                    print(f"  类型: {var.get('type')}")
                    print(f"  默认值: {var.get('default')}")
                    print(f"  描述: {var.get('description')}")
        except Exception as e:
            print(f"解析JSON失败: {e}")
            print(f"响应内容: {response.text[:500]}")
    else:
        print(f"请求失败: {response.status_code}")
        print(f"响应内容: {response.text[:500]}")

if __name__ == "__main__":
    test_vlan_template()
