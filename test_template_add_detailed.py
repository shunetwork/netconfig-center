#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细的模板添加功能测试
"""

import requests
import time
import json

def test_template_add_detailed():
    """详细测试模板添加功能"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== NetManagerX 模板添加功能详细测试 ===")
    
    # 1. 登录
    print("\n1. 登录系统...")
    login_data = {'username': 'admin', 'password': 'admin123'}
    login_response = session.post(f"{base_url}/login", data=login_data)
    print(f"登录响应状态码: {login_response.status_code}")
    if login_response.status_code in [200, 302]:
        print("登录成功")
    else:
        print(f"登录失败: {login_response.text[:200]}")
        return
    
    # 2. 访问模板列表页面
    print("\n2. 访问模板列表页面...")
    list_response = session.get(f"{base_url}/templates")
    print(f"模板列表响应状态码: {list_response.status_code}")
    if list_response.status_code == 200:
        print("模板列表页面访问成功")
        # 检查页面内容
        if "配置模板" in list_response.text:
            print("页面内容正确：包含'配置模板'")
        if "添加模板" in list_response.text:
            print("页面内容正确：包含'添加模板'按钮")
    else:
        print(f"模板列表页面访问失败")
        return
    
    # 3. 访问添加模板页面
    print("\n3. 访问添加模板页面...")
    add_response = session.get(f"{base_url}/templates/add")
    print(f"添加模板页面响应状态码: {add_response.status_code}")
    if add_response.status_code == 200:
        print("添加模板页面访问成功")
        # 检查页面内容
        if "添加模板" in add_response.text:
            print("页面内容正确：包含'添加模板'标题")
        if "模板名称" in add_response.text:
            print("页面内容正确：包含'模板名称'字段")
        if "模板内容" in add_response.text:
            print("页面内容正确：包含'模板内容'字段")
    else:
        print(f"添加模板页面访问失败: {add_response.text[:200]}")
        return
    
    # 4. 提交模板数据
    print("\n4. 提交模板数据...")
    template_data = {
        'name': '详细测试模板',
        'description': '这是一个详细测试的模板',
        'content': 'hostname {{ hostname }}\ninterface {{ interface }}\n  ip address {{ ip_address }} {{ subnet_mask }}\n  no shutdown',
        'template_type': 'config',
        'category': 'network',
        'variables': '{"hostname": {"type": "string", "description": "设备主机名", "required": true}, "interface": {"type": "string", "description": "接口名称", "required": true}, "ip_address": {"type": "string", "description": "IP地址", "required": true}, "subnet_mask": {"type": "string", "description": "子网掩码", "required": true}}'
    }
    
    print(f"提交的数据: {template_data}")
    submit_response = session.post(f"{base_url}/templates/add", data=template_data)
    print(f"提交响应状态码: {submit_response.status_code}")
    print(f"响应头: {dict(submit_response.headers)}")
    
    if submit_response.status_code == 302:
        print("模板添加成功，正在重定向...")
        location = submit_response.headers.get('Location', '未知')
        print(f"重定向到: {location}")
    elif submit_response.status_code == 200:
        print("模板添加返回200状态码，可能有问题")
        print(f"响应内容前500字符: {submit_response.text[:500]}")
    else:
        print(f"模板添加失败，状态码: {submit_response.status_code}")
        print(f"响应内容: {submit_response.text[:500]}")
        return
    
    # 5. 检查模板列表
    print("\n5. 检查模板列表...")
    time.sleep(1)  # 等待数据库更新
    list_response = session.get(f"{base_url}/templates")
    if list_response.status_code == 200:
        if "详细测试模板" in list_response.text:
            print("模板已成功添加到列表")
        else:
            print("模板未在列表中找到")
            print("当前模板列表内容:")
            print(list_response.text[:1000])
    else:
        print(f"获取模板列表失败: {list_response.status_code}")
    
    # 6. 测试模板查看功能
    print("\n6. 测试模板查看功能...")
    view_response = session.get(f"{base_url}/templates/1")
    print(f"模板查看响应状态码: {view_response.status_code}")
    if view_response.status_code == 200:
        print("模板查看功能正常")
    else:
        print(f"模板查看功能异常: {view_response.status_code}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_template_add_detailed()
