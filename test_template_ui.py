#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模板添加页面界面
"""

import requests

def test_template_ui():
    """测试模板添加页面界面"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    # 登录
    login_data = {'username': 'admin', 'password': 'admin123'}
    session.post(f"{base_url}/login", data=login_data)
    
    # 访问添加模板页面
    response = session.get(f"{base_url}/templates/add")
    
    if response.status_code == 200:
        print("模板添加页面访问成功")
        
        # 检查关键元素
        content = response.text
        
        checks = [
            ("页面标题", "添加模板" in content),
            ("表单元素", "form" in content and "method=\"POST\"" in content),
            ("模板名称字段", "name=\"name\"" in content),
            ("模板内容字段", "name=\"content\"" in content),
            ("模板类型选择", "name=\"template_type\"" in content),
            ("描述字段", "name=\"description\"" in content),
            ("分类字段", "name=\"category\"" in content),
            ("变量字段", "name=\"variables\"" in content),
            ("提交按钮", "type=\"submit\"" in content),
            ("侧边栏", "sidebar" in content),
            ("导航菜单", "配置模板" in content)
        ]
        
        print("\n界面元素检查:")
        for name, result in checks:
            status = "PASS" if result else "FAIL"
            print(f"[{status}] {name}")
        
        # 检查是否有错误信息
        if "error" in content.lower():
            print("\n发现错误信息:")
            print(content[content.find("error"):content.find("error")+200])
        
        # 检查是否有成功消息
        if "success" in content.lower():
            print("\n发现成功消息:")
            print(content[content.find("success"):content.find("success")+200])
            
    else:
        print(f"页面访问失败: {response.status_code}")
        print(f"错误信息: {response.text[:500]}")

if __name__ == "__main__":
    test_template_ui()
