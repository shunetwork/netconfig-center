#!/usr/bin/env python3
"""
测试添加模板功能
"""

import requests
import json
import time

def test_template_add():
    """测试添加模板功能"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== 添加模板功能测试 ===")
    
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
    
    # 2. 访问添加模板页面
    print("2. 访问添加模板页面...")
    add_page_response = session.get(f"{base_url}/templates/add")
    if add_page_response.status_code == 200:
        print("添加模板页面访问成功")
    else:
        print(f"添加模板页面访问失败: {add_page_response.status_code}")
        return False
    
    # 3. 测试添加模板
    print("3. 测试添加模板...")
    template_data = {
        'name': '测试路由器配置模板',
        'description': '这是一个测试用的路由器配置模板',
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
    
    add_response = session.post(f"{base_url}/templates/add", data=template_data, allow_redirects=False)
    print(f"添加模板响应: {add_response.status_code}")
    
    if add_response.status_code == 302:
        print("模板添加成功，正在重定向...")
        
        # 4. 验证模板是否添加成功
        print("4. 验证模板列表...")
        templates_response = session.get(f"{base_url}/templates")
        if templates_response.status_code == 200:
            print("模板列表页面访问成功")
            if "测试路由器配置模板" in templates_response.text:
                print("模板已成功添加到列表中")
            else:
                print("警告：模板可能未正确添加到列表中")
        else:
            print(f"模板列表页面访问失败: {templates_response.status_code}")
    else:
        print(f"模板添加失败: {add_response.status_code}")
        print(f"响应内容: {add_response.text[:200]}")
        return False
    
    print("=== 测试完成 ===")
    return True

def test_template_validation():
    """测试模板验证功能"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("\n=== 模板验证测试 ===")
    
    # 登录
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    
    # 测试空名称
    print("1. 测试空名称验证...")
    empty_name_data = {
        'name': '',
        'content': 'test content'
    }
    response = session.post(f"{base_url}/templates/add", data=empty_name_data, allow_redirects=False)
    if response.status_code == 200 and "模板名称和内容不能为空" in response.text:
        print("空名称验证通过")
    else:
        print("空名称验证失败")
    
    # 测试空内容
    print("2. 测试空内容验证...")
    empty_content_data = {
        'name': 'test template',
        'content': ''
    }
    response = session.post(f"{base_url}/templates/add", data=empty_content_data, allow_redirects=False)
    if response.status_code == 200 and "模板名称和内容不能为空" in response.text:
        print("空内容验证通过")
    else:
        print("空内容验证失败")
    
    # 测试无效JSON变量
    print("3. 测试无效JSON变量验证...")
    invalid_json_data = {
        'name': 'test template',
        'content': 'test content',
        'variables': 'invalid json'
    }
    response = session.post(f"{base_url}/templates/add", data=invalid_json_data, allow_redirects=False)
    if response.status_code == 200:
        print("无效JSON变量处理正常")
    else:
        print("无效JSON变量处理异常")
    
    print("=== 验证测试完成 ===")

def test_template_types():
    """测试不同模板类型"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("\n=== 模板类型测试 ===")
    
    # 登录
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    
    # 测试配置模板
    print("1. 测试配置模板...")
    config_template = {
        'name': 'Cisco路由器基础配置',
        'description': 'Cisco路由器基础配置模板',
        'content': '''hostname {{hostname}}
enable secret {{enable_password}}
interface {{interface}}
 ip address {{ip_address}} {{subnet_mask}}
 no shutdown''',
        'template_type': 'config',
        'category': 'network'
    }
    
    response = session.post(f"{base_url}/templates/add", data=config_template, allow_redirects=False)
    if response.status_code == 302:
        print("配置模板添加成功")
    else:
        print("配置模板添加失败")
    
    # 测试脚本模板
    print("2. 测试脚本模板...")
    script_template = {
        'name': '网络诊断脚本',
        'description': '网络诊断脚本模板',
        'content': '''#!/bin/bash
# 网络诊断脚本
ping -c 4 {{target_ip}}
traceroute {{target_ip}}
nslookup {{domain_name}}''',
        'template_type': 'script',
        'category': 'general'
    }
    
    response = session.post(f"{base_url}/templates/add", data=script_template, allow_redirects=False)
    if response.status_code == 302:
        print("脚本模板添加成功")
    else:
        print("脚本模板添加失败")
    
    # 测试备份模板
    print("3. 测试备份模板...")
    backup_template = {
        'name': '设备配置备份',
        'description': '设备配置备份模板',
        'content': '''copy running-config {{backup_location}}/{{device_name}}_{{timestamp}}.cfg
copy startup-config {{backup_location}}/{{device_name}}_startup_{{timestamp}}.cfg''',
        'template_type': 'backup',
        'category': 'general'
    }
    
    response = session.post(f"{base_url}/templates/add", data=backup_template, allow_redirects=False)
    if response.status_code == 302:
        print("备份模板添加成功")
    else:
        print("备份模板添加失败")
    
    print("=== 模板类型测试完成 ===")

if __name__ == "__main__":
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(3)
    
    # 运行所有测试
    success = test_template_add()
    test_template_validation()
    test_template_types()
    
    if success:
        print("\n所有测试完成！")
    else:
        print("\n部分测试失败，请检查服务器状态。")
