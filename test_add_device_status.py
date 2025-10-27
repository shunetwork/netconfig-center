#!/usr/bin/env python3
"""
测试添加设备后的状态检查
"""

import requests
import json
import time

def test_add_device_and_status():
    """测试添加设备并检查状态"""
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
    
    # 2. 添加新设备
    print("添加新设备...")
    device_data = {
        'name': '测试设备',
        'ip_address': '8.8.8.8',  # 使用Google DNS，应该是在线的
        'hostname': 'test-device',
        'device_type': 'cisco',
        'connection_type': 'ssh',
        'port': '53',  # DNS端口
        'username': 'admin',
        'password': 'password',
        'description': '测试设备'
    }
    
    add_response = session.post(f"{base_url}/devices/add", data=device_data, allow_redirects=False)
    print(f"添加设备响应: {add_response.status_code}")
    
    # 3. 等待一下让状态检查完成
    time.sleep(2)
    
    # 4. 检查所有设备状态
    print("检查所有设备状态...")
    status_response = session.post(f"{base_url}/api/devices/status/check-all")
    if status_response.status_code == 200:
        result = status_response.json()
        print(f"设备状态检查结果:")
        for device in result['devices']:
            print(f"  - {device['name']}: {device['status_text']} (响应时间: {device['response_time']}ms)")
    else:
        print(f"状态检查失败: {status_response.status_code}")

if __name__ == "__main__":
    test_add_device_and_status()
