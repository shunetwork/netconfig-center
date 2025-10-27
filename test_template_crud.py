#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetManagerX 模板CRUD功能测试
测试模板的增删改查功能
"""

import requests
import json
import time
from datetime import datetime

class TemplateCRUDTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []

    def log_test(self, test_name, success, message="", details=None):
        """记录测试结果并打印"""
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}: {message}")
        self.test_results.append({
            'test_name': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def login(self):
        """登录系统"""
        print("正在登录系统...")
        
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        try:
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            if response.status_code in [200, 302]:
                self.log_test("用户登录", True, "登录成功")
                return True
            else:
                self.log_test("用户登录", False, f"登录失败: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError as e:
            self.log_test("用户登录", False, f"登录连接失败: {str(e)}")
            return False
        except Exception as e:
            self.log_test("用户登录", False, f"登录异常: {str(e)}")
            return False

    def test_template_list(self):
        """测试模板列表页面"""
        print("测试模板列表页面...")
        
        try:
            response = self.session.get(f"{self.base_url}/templates")
            if response.status_code == 200:
                if "配置模板" in response.text and "模板管理" in response.text:
                    self.log_test("模板列表页面", True, "页面加载成功")
                    return True
                else:
                    self.log_test("模板列表页面", False, "页面内容不正确")
                    return False
            else:
                self.log_test("模板列表页面", False, f"页面加载失败: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("模板列表页面", False, f"页面访问异常: {str(e)}")
            return False

    def test_add_template(self):
        """测试添加模板"""
        print("测试添加模板...")
        
        template_data = {
            'name': '测试配置模板',
            'description': '这是一个测试用的配置模板',
            'content': 'hostname {{ hostname }}\ninterface {{ interface }}\n  ip address {{ ip_address }} {{ subnet_mask }}\n  no shutdown',
            'template_type': 'config',
            'category': 'network',
            'variables': '{"hostname": {"type": "string", "description": "设备主机名", "required": true}, "interface": {"type": "string", "description": "接口名称", "required": true}, "ip_address": {"type": "string", "description": "IP地址", "required": true}, "subnet_mask": {"type": "string", "description": "子网掩码", "required": true}}'
        }
        
        try:
            response = self.session.post(f"{self.base_url}/templates/add", data=template_data)
            if response.status_code == 302:  # 成功添加后会重定向
                self.log_test("添加模板", True, "模板添加成功")
                return True
            else:
                self.log_test("添加模板", False, f"添加失败: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("添加模板", False, f"添加异常: {str(e)}")
            return False

    def test_view_template(self):
        """测试查看模板"""
        print("测试查看模板...")
        
        try:
            # 先获取模板列表，找到第一个模板
            list_response = self.session.get(f"{self.base_url}/templates")
            if list_response.status_code == 200:
                # 这里简化处理，直接访问ID为1的模板
                response = self.session.get(f"{self.base_url}/templates/1")
                if response.status_code == 200:
                    if "模板详情" in response.text:
                        self.log_test("查看模板", True, "模板详情页面加载成功")
                        return True
                    else:
                        self.log_test("查看模板", False, "页面内容不正确")
                        return False
                else:
                    self.log_test("查看模板", False, f"页面加载失败: {response.status_code}")
                    return False
            else:
                self.log_test("查看模板", False, "无法获取模板列表")
                return False
        except Exception as e:
            self.log_test("查看模板", False, f"查看异常: {str(e)}")
            return False

    def test_edit_template(self):
        """测试编辑模板"""
        print("测试编辑模板...")
        
        # 先访问编辑页面
        try:
            response = self.session.get(f"{self.base_url}/templates/1/edit")
            if response.status_code == 200:
                if "编辑模板" in response.text:
                    self.log_test("编辑模板页面", True, "编辑页面加载成功")
                    
                    # 测试提交编辑
                    edit_data = {
                        'name': '修改后的测试模板',
                        'description': '这是修改后的测试模板',
                        'content': 'hostname {{ hostname }}\ninterface {{ interface }}\n  ip address {{ ip_address }} {{ subnet_mask }}\n  no shutdown\n  description {{ description }}',
                        'template_type': 'config',
                        'category': 'network',
                        'variables': '{"hostname": {"type": "string", "description": "设备主机名", "required": true}, "interface": {"type": "string", "description": "接口名称", "required": true}, "ip_address": {"type": "string", "description": "IP地址", "required": true}, "subnet_mask": {"type": "string", "description": "子网掩码", "required": true}, "description": {"type": "string", "description": "接口描述", "required": false}}'
                    }
                    
                    edit_response = self.session.post(f"{self.base_url}/templates/1/edit", data=edit_data)
                    if edit_response.status_code == 302:  # 成功编辑后会重定向
                        self.log_test("编辑模板", True, "模板编辑成功")
                        return True
                    else:
                        self.log_test("编辑模板", False, f"编辑失败: {edit_response.status_code}")
                        return False
                else:
                    self.log_test("编辑模板", False, "编辑页面内容不正确")
                    return False
            else:
                self.log_test("编辑模板", False, f"编辑页面加载失败: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("编辑模板", False, f"编辑异常: {str(e)}")
            return False

    def test_delete_template(self):
        """测试删除模板"""
        print("测试删除模板...")
        
        try:
            # 使用API删除模板
            response = self.session.post(f"{self.base_url}/api/templates/1/delete")
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("删除模板", True, "模板删除成功")
                    return True
                else:
                    self.log_test("删除模板", False, f"删除失败: {result.get('error', '未知错误')}")
                    return False
            else:
                self.log_test("删除模板", False, f"删除请求失败: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("删除模板", False, f"删除异常: {str(e)}")
            return False

    def test_template_validation(self):
        """测试模板验证"""
        print("测试模板验证...")
        
        # 测试空名称
        try:
            invalid_data = {
                'name': '',  # 空名称
                'content': 'test content'
            }
            response = self.session.post(f"{self.base_url}/templates/add", data=invalid_data)
            if response.status_code == 200:  # 应该返回表单页面而不是重定向
                self.log_test("模板验证-空名称", True, "正确拒绝了空名称")
            else:
                self.log_test("模板验证-空名称", False, f"验证失败: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("模板验证-空名称", False, f"验证异常: {str(e)}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("NetManagerX 模板CRUD功能测试")
        print("=" * 50)
        
        # 登录
        if not self.login():
            print("登录失败，无法继续测试")
            return
        
        # 运行各项测试
        self.test_template_list()
        self.test_add_template()
        time.sleep(1)  # 等待数据库更新
        self.test_view_template()
        self.test_edit_template()
        time.sleep(1)  # 等待数据库更新
        self.test_delete_template()
        self.test_template_validation()
        
        # 生成测试报告
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 50)
        print("测试报告")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test_name']}: {result['message']}")
        
        print("\n测试完成！")

def main():
    """主函数"""
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(3)
    
    # 创建测试实例
    tester = TemplateCRUDTester()
    
    # 运行所有测试
    tester.run_all_tests()

if __name__ == "__main__":
    main()
