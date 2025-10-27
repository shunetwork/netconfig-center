#!/usr/bin/env python3
"""
测试模板数据库功能
"""

import requests
import json
import time

def test_template_database():
    """测试模板数据库功能"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== 模板数据库功能测试 ===")
    
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
    
    # 2. 添加一个测试模板
    print("2. 添加测试模板...")
    template_data = {
        'name': '数据库测试模板',
        'description': '用于测试数据库功能的模板',
        'content': '''hostname {{hostname}}
interface {{interface}}
 ip address {{ip_address}} {{subnet_mask}}
 no shutdown
line vty 0 4
 login local
 transport input ssh''',
        'template_type': 'config',
        'category': 'network',
        'variables': '{"hostname": "string", "interface": "string", "ip_address": "string", "subnet_mask": "string"}'
    }
    
    add_response = session.post(f"{base_url}/templates/add", data=template_data, allow_redirects=False)
    print(f"添加模板响应: {add_response.status_code}")
    
    if add_response.status_code == 302:
        print("模板添加成功")
        
        # 3. 验证模板列表页面
        print("3. 验证模板列表页面...")
        templates_response = session.get(f"{base_url}/templates")
        if templates_response.status_code == 200:
            print("模板列表页面访问成功")
            
            # 检查模板是否在页面中
            if "数据库测试模板" in templates_response.text:
                print("模板已成功显示在列表中")
            else:
                print("警告：模板未在列表中显示")
                
            # 检查模板类型
            if "config" in templates_response.text or "配置模板" in templates_response.text:
                print("模板类型显示正常")
            else:
                print("模板类型显示可能有问题")
                
        else:
            print(f"模板列表页面访问失败: {templates_response.status_code}")
            return False
    else:
        print(f"模板添加失败: {add_response.status_code}")
        return False
    
    # 4. 测试模板变量功能
    print("4. 测试模板变量功能...")
    variable_template = {
        'name': '变量测试模板',
        'description': '测试变量功能的模板',
        'content': 'hostname {{hostname}}\ninterface {{interface}}',
        'template_type': 'config',
        'category': 'general',
        'variables': '{"hostname": "string", "interface": "string", "ip_address": "string"}'
    }
    
    var_response = session.post(f"{base_url}/templates/add", data=variable_template, allow_redirects=False)
    if var_response.status_code == 302:
        print("变量模板添加成功")
    else:
        print("变量模板添加失败")
    
    # 5. 测试不同分类
    print("5. 测试不同分类...")
    categories = ['network', 'security', 'routing', 'switching']
    for category in categories:
        cat_template = {
            'name': f'{category}测试模板',
            'description': f'{category}分类测试模板',
            'content': f'# {category}配置模板\nhostname {{hostname}}',
            'template_type': 'config',
            'category': category
        }
        
        cat_response = session.post(f"{base_url}/templates/add", data=cat_template, allow_redirects=False)
        if cat_response.status_code == 302:
            print(f"{category}分类模板添加成功")
        else:
            print(f"{category}分类模板添加失败")
    
    print("=== 数据库功能测试完成 ===")
    return True

def test_template_content_validation():
    """测试模板内容验证"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("\n=== 模板内容验证测试 ===")
    
    # 登录
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    
    # 测试长内容
    print("1. 测试长内容模板...")
    long_content = "hostname {{hostname}}\n" * 100  # 创建长内容
    long_template = {
        'name': '长内容测试模板',
        'description': '测试长内容处理',
        'content': long_content,
        'template_type': 'config',
        'category': 'general'
    }
    
    response = session.post(f"{base_url}/templates/add", data=long_template, allow_redirects=False)
    if response.status_code == 302:
        print("长内容模板添加成功")
    else:
        print("长内容模板添加失败")
    
    # 测试特殊字符
    print("2. 测试特殊字符...")
    special_template = {
        'name': '特殊字符测试模板',
        'description': '测试特殊字符处理：!@#$%^&*()',
        'content': '''hostname {{hostname}}
! 这是注释
interface {{interface}}
 ip address {{ip_address}} {{subnet_mask}}
 no shutdown
! 结束配置''',
        'template_type': 'config',
        'category': 'general'
    }
    
    response = session.post(f"{base_url}/templates/add", data=special_template, allow_redirects=False)
    if response.status_code == 302:
        print("特殊字符模板添加成功")
    else:
        print("特殊字符模板添加失败")
    
    print("=== 内容验证测试完成 ===")

if __name__ == "__main__":
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(3)
    
    # 运行所有测试
    success = test_template_database()
    test_template_content_validation()
    
    if success:
        print("\n所有数据库测试完成！")
    else:
        print("\n部分数据库测试失败，请检查服务器状态。")
