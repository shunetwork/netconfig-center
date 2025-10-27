#!/usr/bin/env python3
"""
测试flash消息修复效果
"""

import requests
import time

def test_flash_message_fix():
    """测试flash消息修复"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    # 1. 登录
    print("正在登录...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    if login_response.status_code not in [200, 302]:
        print(f"登录失败: {login_response.status_code}")
        return
    
    print("登录成功")
    
    # 2. 添加一个设备（这会触发flash消息）
    print("添加设备以产生flash消息...")
    device_data = {
        'name': '测试设备2',
        'ip_address': '8.8.8.8',
        'hostname': 'test-device-2',
        'device_type': 'cisco',
        'connection_type': 'ssh',
        'port': '53',
        'username': 'admin',
        'password': 'password',
        'description': '测试设备2'
    }
    
    add_response = session.post(f"{base_url}/devices/add", data=device_data, allow_redirects=False)
    print(f"添加设备响应: {add_response.status_code}")
    
    # 3. 访问添加设备页面（GET请求）
    print("访问添加设备页面...")
    add_page_response = session.get(f"{base_url}/devices/add")
    if add_page_response.status_code == 200:
        print("添加设备页面访问成功")
        
        # 检查页面内容中是否还有之前的flash消息
        if "设备添加成功!" in add_page_response.text:
            print("问题未修复：页面中仍然显示之前的flash消息")
        else:
            print("问题已修复：页面中没有显示之前的flash消息")
    else:
        print(f"添加设备页面访问失败: {add_page_response.status_code}")

if __name__ == "__main__":
    test_flash_message_fix()
