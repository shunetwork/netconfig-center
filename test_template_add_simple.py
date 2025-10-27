#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的模板添加功能测试
"""

import requests
import time

def test_template_add_page():
    """测试模板添加页面"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    # 1. 登录
    print("1. 登录系统...")
    login_data = {'username': 'admin', 'password': 'admin123'}
    login_response = session.post(f"{base_url}/login", data=login_data)
    print(f"登录响应: {login_response.status_code}")
    
    # 2. 访问模板列表页面
    print("2. 访问模板列表页面...")
    list_response = session.get(f"{base_url}/templates")
    print(f"模板列表响应: {list_response.status_code}")
    if list_response.status_code == 200:
        print("模板列表页面访问成功")
    else:
        print(f"模板列表页面访问失败: {list_response.text[:200]}")
        return
    
    # 3. 访问添加模板页面
    print("3. 访问添加模板页面...")
    add_response = session.get(f"{base_url}/templates/add")
    print(f"添加模板页面响应: {add_response.status_code}")
    if add_response.status_code == 200:
        print("添加模板页面访问成功")
        if "添加模板" in add_response.text:
            print("页面内容正确")
        else:
            print("页面内容可能有问题")
    else:
        print(f"添加模板页面访问失败: {add_response.text[:200]}")
        return
    
    # 4. 提交模板数据
    print("4. 提交模板数据...")
    template_data = {
        'name': '测试模板',
        'description': '这是一个测试模板',
        'content': 'hostname {{ hostname }}\ninterface {{ interface }}\n  ip address {{ ip_address }} {{ subnet_mask }}',
        'template_type': 'config',
        'category': 'network',
        'variables': '{"hostname": {"type": "string", "description": "设备主机名", "required": true}}'
    }
    
    submit_response = session.post(f"{base_url}/templates/add", data=template_data)
    print(f"提交响应: {submit_response.status_code}")
    if submit_response.status_code == 302:
        print("模板添加成功，正在重定向...")
        print(f"重定向到: {submit_response.headers.get('Location', '未知')}")
    else:
        print(f"模板添加失败: {submit_response.text[:500]}")
    
    # 5. 检查模板列表
    print("5. 检查模板列表...")
    list_response = session.get(f"{base_url}/templates")
    if list_response.status_code == 200:
        if "测试模板" in list_response.text:
            print("模板已成功添加到列表")
        else:
            print("模板未在列表中找到")
    else:
        print(f"获取模板列表失败: {list_response.status_code}")

if __name__ == "__main__":
    test_template_add_page()
