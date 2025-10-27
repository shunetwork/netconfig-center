#!/usr/bin/env python3
"""
测试模板API功能
"""

import requests
import json
import time

def test_template_api():
    """测试模板API功能"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== 模板API功能测试 ===")
    
    # 1. 登录
    print("1. 登录系统...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    if login_response.status_code not in [200, 302]:
        print(f"登录失败: {login_response.status_code}")
        return False
    
    print("登录成功")
    
    # 2. 测试GET请求 (访问添加页面)
    print("2. 测试GET请求...")
    get_response = session.get(f"{base_url}/templates/add")
    if get_response.status_code == 200:
        print("GET请求成功")
        
        # 检查页面内容
        if "添加模板" in get_response.text:
            print("页面标题正确")
        if "模板名称" in get_response.text:
            print("表单字段存在")
        if "模板内容" in get_response.text:
            print("内容字段存在")
    else:
        print(f"GET请求失败: {get_response.status_code}")
        return False
    
    # 3. 测试POST请求 (添加模板)
    print("3. 测试POST请求...")
    template_data = {
        'name': 'API测试模板',
        'description': '通过API测试添加的模板',
        'content': '''hostname {{hostname}}
interface {{interface}}
 ip address {{ip_address}} {{subnet_mask}}
 no shutdown
line vty 0 4
 login local
 transport input ssh
username {{username}} privilege 15 password {{password}}''',
        'template_type': 'config',
        'category': 'network',
        'variables': '{"hostname": "string", "interface": "string", "ip_address": "string", "subnet_mask": "string", "username": "string", "password": "string"}'
    }
    
    post_response = session.post(f"{base_url}/templates/add", data=template_data, allow_redirects=False)
    print(f"POST请求响应: {post_response.status_code}")
    
    if post_response.status_code == 302:
        print("POST请求成功，模板已添加")
        
        # 4. 验证重定向
        print("4. 验证重定向...")
        if 'Location' in post_response.headers:
            location = post_response.headers['Location']
            if '/templates' in location:
                print("重定向到模板列表页面")
            else:
                print(f"重定向到: {location}")
        else:
            print("未找到重定向头")
    else:
        print(f"POST请求失败: {post_response.status_code}")
        print(f"响应内容: {post_response.text[:200]}")
        return False
    
    # 5. 测试模板列表页面
    print("5. 测试模板列表页面...")
    templates_response = session.get(f"{base_url}/templates")
    if templates_response.status_code == 200:
        print("模板列表页面访问成功")
        
        # 检查新添加的模板
        if "API测试模板" in templates_response.text:
            print("新模板已显示在列表中")
        else:
            print("警告：新模板未在列表中显示")
    else:
        print(f"模板列表页面访问失败: {templates_response.status_code}")
    
    print("=== API功能测试完成 ===")
    return True

def test_template_validation_api():
    """测试模板验证API"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("\n=== 模板验证API测试 ===")
    
    # 登录
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    
    # 测试空数据
    print("1. 测试空数据验证...")
    empty_data = {}
    response = session.post(f"{base_url}/templates/add", data=empty_data, allow_redirects=False)
    if response.status_code == 200:
        print("空数据验证正常")
    else:
        print(f"空数据验证异常: {response.status_code}")
    
    # 测试部分数据
    print("2. 测试部分数据验证...")
    partial_data = {
        'name': '测试模板',
        # 缺少content字段
    }
    response = session.post(f"{base_url}/templates/add", data=partial_data, allow_redirects=False)
    if response.status_code == 200:
        print("部分数据验证正常")
    else:
        print(f"部分数据验证异常: {response.status_code}")
    
    # 测试无效数据
    print("3. 测试无效数据验证...")
    invalid_data = {
        'name': '',
        'content': '',
        'template_type': 'invalid_type'
    }
    response = session.post(f"{base_url}/templates/add", data=invalid_data, allow_redirects=False)
    if response.status_code == 200:
        print("无效数据验证正常")
    else:
        print(f"无效数据验证异常: {response.status_code}")
    
    print("=== 验证API测试完成 ===")

if __name__ == "__main__":
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(3)
    
    # 运行所有测试
    success = test_template_api()
    test_template_validation_api()
    
    if success:
        print("\n所有API测试完成！")
    else:
        print("\n部分API测试失败，请检查服务器状态。")
