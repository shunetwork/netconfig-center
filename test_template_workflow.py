#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模板添加完整工作流程
"""

import requests
import time

def test_template_workflow():
    """测试模板添加完整工作流程"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== NetManagerX 模板添加完整工作流程测试 ===")
    
    # 1. 登录
    print("\n1. 登录系统...")
    login_data = {'username': 'admin', 'password': 'admin123'}
    login_response = session.post(f"{base_url}/login", data=login_data)
    if login_response.status_code in [200, 302]:
        print("登录成功")
    else:
        print("登录失败")
        return
    
    # 2. 获取初始模板数量
    print("\n2. 获取初始模板数量...")
    list_response = session.get(f"{base_url}/templates")
    if list_response.status_code == 200:
        initial_count = list_response.text.count("template-name")
        print(f"初始模板数量: {initial_count}")
    else:
        print("无法获取模板列表")
        return
    
    # 3. 访问添加模板页面
    print("\n3. 访问添加模板页面...")
    add_response = session.get(f"{base_url}/templates/add")
    if add_response.status_code == 200:
        print("添加模板页面访问成功")
    else:
        print(f"添加模板页面访问失败: {add_response.status_code}")
        return
    
    # 4. 提交新模板
    print("\n4. 提交新模板...")
    template_data = {
        'name': f'工作流程测试模板_{int(time.time())}',
        'description': '这是一个工作流程测试模板',
        'content': 'hostname {{ hostname }}\ninterface {{ interface }}\n  ip address {{ ip_address }} {{ subnet_mask }}',
        'template_type': 'config',
        'category': 'network',
        'variables': '{"hostname": {"type": "string", "description": "设备主机名", "required": true}}'
    }
    
    submit_response = session.post(f"{base_url}/templates/add", data=template_data)
    print(f"提交响应状态码: {submit_response.status_code}")
    
    if submit_response.status_code == 302:
        print("模板添加成功，正在重定向")
        location = submit_response.headers.get('Location', '')
        print(f"重定向到: {location}")
    elif submit_response.status_code == 200:
        print("模板添加返回200状态码，检查是否有错误")
        if "error" in submit_response.text.lower():
            print("发现错误信息")
        else:
            print("没有发现错误信息，可能是正常返回")
    else:
        print(f"模板添加失败: {submit_response.status_code}")
        return
    
    # 5. 验证模板是否添加成功
    print("\n5. 验证模板是否添加成功...")
    time.sleep(1)  # 等待数据库更新
    
    list_response = session.get(f"{base_url}/templates")
    if list_response.status_code == 200:
        final_count = list_response.text.count("template-name")
        print(f"最终模板数量: {final_count}")
        
        if final_count > initial_count:
            print("模板添加成功！")
        else:
            print("模板数量没有增加，可能添加失败")
            
        # 检查新模板是否在列表中
        if template_data['name'] in list_response.text:
            print(f"新模板 '{template_data['name']}' 已出现在列表中")
        else:
            print(f"新模板 '{template_data['name']}' 未出现在列表中")
    else:
        print("无法获取更新后的模板列表")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_template_workflow()
