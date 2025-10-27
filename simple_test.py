#!/usr/bin/env python3
"""
简单测试添加设备页面
"""

import requests

def simple_test():
    """简单测试"""
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
    
    # 2. 访问添加设备页面
    print("访问添加设备页面...")
    try:
        add_page_response = session.get(f"{base_url}/devices/add")
        print(f"响应状态码: {add_page_response.status_code}")
        if add_page_response.status_code == 200:
            print("页面访问成功")
        else:
            print(f"页面访问失败: {add_page_response.text[:200]}")
    except Exception as e:
        print(f"访问异常: {e}")

if __name__ == "__main__":
    simple_test()
