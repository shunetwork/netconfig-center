#!/usr/bin/env python3
"""
完整测试flash消息修复效果
"""

import requests
import time

def test_complete_fix():
    """完整测试修复效果"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== Flash消息修复测试 ===")
    
    # 1. 登录
    print("1. 登录系统...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    if login_response.status_code not in [200, 302]:
        print(f"登录失败: {login_response.status_code}")
        return
    
    print("登录成功")
    
    # 2. 访问添加设备页面（第一次，应该是干净的）
    print("2. 第一次访问添加设备页面...")
    add_page_response = session.get(f"{base_url}/devices/add")
    if add_page_response.status_code == 200:
        print("页面访问成功")
        if "设备添加成功!" in add_page_response.text:
            print("问题：页面中显示了不应该存在的flash消息")
        else:
            print("正常：页面中没有显示flash消息")
    else:
        print(f"页面访问失败: {add_page_response.status_code}")
        return
    
    # 3. 添加一个设备（这会产生flash消息）
    print("3. 添加设备...")
    device_data = {
        'name': '测试设备修复',
        'ip_address': '1.1.1.1',
        'hostname': 'test-fix',
        'device_type': 'cisco',
        'connection_type': 'ssh',
        'port': '22',
        'username': 'admin',
        'password': 'password',
        'description': '测试修复的设备'
    }
    
    add_response = session.post(f"{base_url}/devices/add", data=device_data, allow_redirects=False)
    print(f"添加设备响应: {add_response.status_code}")
    
    # 4. 再次访问添加设备页面（应该清除之前的flash消息）
    print("4. 再次访问添加设备页面...")
    add_page_response2 = session.get(f"{base_url}/devices/add")
    if add_page_response2.status_code == 200:
        print("页面访问成功")
        if "设备添加成功!" in add_page_response2.text:
            print("问题：页面中仍然显示之前的flash消息")
        else:
            print("修复成功：页面中没有显示之前的flash消息")
    else:
        print(f"页面访问失败: {add_page_response2.status_code}")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_complete_fix()
