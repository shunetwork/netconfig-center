#!/usr/bin/env python3
"""
测试设备状态检查API
"""

import requests
import json

def test_device_status():
    """测试设备状态检查功能"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    # 1. 登录
    print("正在登录...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    if login_response.status_code in [200, 302]:  # 200或302都表示登录成功
        print("登录成功")
    else:
        print(f"登录失败: {login_response.status_code}")
        print(f"响应内容: {login_response.text[:200]}")
        return
    
    # 2. 获取设备列表
    print("获取设备列表...")
    devices_response = session.get(f"{base_url}/devices")
    if devices_response.status_code == 200:
        print("设备列表获取成功")
    else:
        print(f"设备列表获取失败: {devices_response.status_code}")
        return
    
    # 3. 测试单个设备状态检查
    print("测试单个设备状态检查...")
    try:
        status_response = session.post(f"{base_url}/api/devices/status/check-all")
        if status_response.status_code == 200:
            result = status_response.json()
            print(f"状态检查结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"状态检查失败: {status_response.status_code}")
            print(f"响应内容: {status_response.text}")
    except Exception as e:
        print(f"状态检查异常: {e}")
    
    # 4. 测试健康检查
    print("测试健康检查...")
    health_response = session.get(f"{base_url}/health")
    if health_response.status_code == 200:
        print(f"健康检查成功: {health_response.json()}")
    else:
        print(f"健康检查失败: {health_response.status_code}")

if __name__ == "__main__":
    test_device_status()
