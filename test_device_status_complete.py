#!/usr/bin/env python3
"""
设备状态检查功能完整测试实例
"""

import requests
import json
import time
import socket
import threading
from datetime import datetime

class DeviceStatusTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message="", details=None):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"    详情: {details}")
    
    def login(self):
        """登录系统"""
        print("正在登录系统...")
        
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        try:
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            if response.status_code == 302:  # 重定向表示登录成功
                self.log_test("用户登录", True, "登录成功")
                return True
            else:
                self.log_test("用户登录", False, f"登录失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("用户登录", False, f"登录异常: {str(e)}")
            return False
    
    def test_device_model(self):
        """测试设备模型功能"""
        print("\n测试设备模型功能...")
        
        try:
            # 导入设备模型
            import sys
            sys.path.append('.')
            
            from modern_start import app, Device, db
            import time
            
            with app.app_context():
                # 获取所有设备
                devices = Device.query.all()
                
                if not devices:
                    self.log_test("设备模型查询", False, "没有找到设备")
                    return False
                
                self.log_test("设备模型查询", True, f"找到 {len(devices)} 个设备")
                
                # 测试状态检查功能
                for device in devices:
                    print(f"\n检查设备: {device.name} ({device.ip_address}:{device.port})")
                    
                    # 检查状态
                    start_time = time.time()
                    status = device.check_status()
                    end_time = time.time()
                    
                    # 验证状态检查结果
                    if status in ['online', 'offline', 'unknown']:
                        self.log_test(f"设备状态检查-{device.name}", True, f"状态: {status}")
                    else:
                        self.log_test(f"设备状态检查-{device.name}", False, f"无效状态: {status}")
                    
                    # 验证响应时间
                    if device.last_response_time is not None and device.last_response_time >= 0:
                        self.log_test(f"响应时间测量-{device.name}", True, f"响应时间: {device.last_response_time:.1f}ms")
                    else:
                        self.log_test(f"响应时间测量-{device.name}", False, "响应时间无效")
                    
                    # 验证状态显示
                    status_info = device.get_status_display()
                    if 'text' in status_info and 'class' in status_info:
                        self.log_test(f"状态显示-{device.name}", True, f"显示: {status_info['text']}")
                    else:
                        self.log_test(f"状态显示-{device.name}", False, "状态显示信息不完整")
                
                # 保存状态到数据库
                db.session.commit()
                self.log_test("数据库保存", True, "设备状态已保存到数据库")
                
                return True
                
        except Exception as e:
            self.log_test("设备模型测试", False, f"模型测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_api_endpoints(self):
        """测试API接口"""
        print("\n测试API接口...")
        
        try:
            # 测试批量状态检查API
            response = self.session.post(f"{self.base_url}/api/devices/status/check-all")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    devices = result.get('devices', [])
                    self.log_test("批量状态检查API", True, f"检查了 {len(devices)} 个设备")
                    
                    # 验证返回数据格式
                    for device in devices:
                        required_fields = ['id', 'name', 'status', 'status_text', 'status_class']
                        if all(field in device for field in required_fields):
                            self.log_test(f"API数据格式-{device['name']}", True, "数据格式正确")
                        else:
                            missing_fields = [f for f in required_fields if f not in device]
                            self.log_test(f"API数据格式-{device['name']}", False, f"缺少字段: {missing_fields}")
                else:
                    self.log_test("批量状态检查API", False, f"API返回失败: {result.get('message')}")
            else:
                self.log_test("批量状态检查API", False, f"HTTP状态码: {response.status_code}")
            
            # 测试单个设备状态检查API（如果有设备的话）
            devices_response = self.session.get(f"{self.base_url}/devices")
            if devices_response.status_code == 200:
                self.log_test("设备列表页面", True, "设备列表页面访问成功")
            else:
                self.log_test("设备列表页面", False, f"设备列表页面访问失败: {devices_response.status_code}")
                
            return True
            
        except Exception as e:
            self.log_test("API接口测试", False, f"API测试异常: {str(e)}")
            return False
    
    def test_socket_connection(self):
        """测试Socket连接功能"""
        print("\n测试Socket连接功能...")
        
        # 测试常见的网络设备端口
        test_hosts = [
            ('127.0.0.1', 22),    # 本地SSH
            ('127.0.0.1', 23),    # 本地Telnet
            ('8.8.8.8', 53),      # Google DNS
            ('1.1.1.1', 53),      # Cloudflare DNS
        ]
        
        for host, port in test_hosts:
            try:
                start_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                
                if result == 0:
                    self.log_test(f"Socket连接-{host}:{port}", True, f"连接成功，响应时间: {response_time:.1f}ms")
                else:
                    self.log_test(f"Socket连接-{host}:{port}", False, f"连接失败，错误码: {result}")
                    
            except Exception as e:
                self.log_test(f"Socket连接-{host}:{port}", False, f"连接异常: {str(e)}")
    
    def test_web_interface(self):
        """测试Web界面功能"""
        print("\n测试Web界面功能...")
        
        try:
            # 测试设备管理页面
            response = self.session.get(f"{self.base_url}/devices")
            if response.status_code == 200:
                self.log_test("设备管理页面", True, "页面访问成功")
                
                # 检查页面内容
                content = response.text
                if '检查状态' in content:
                    self.log_test("状态检查按钮", True, "页面包含状态检查按钮")
                else:
                    self.log_test("状态检查按钮", False, "页面缺少状态检查按钮")
                
                if 'status-badge' in content:
                    self.log_test("状态徽章样式", True, "页面包含状态徽章样式")
                else:
                    self.log_test("状态徽章样式", False, "页面缺少状态徽章样式")
                    
            else:
                self.log_test("设备管理页面", False, f"页面访问失败: {response.status_code}")
            
            # 测试配置模板页面
            response = self.session.get(f"{self.base_url}/templates")
            if response.status_code == 200:
                self.log_test("配置模板页面", True, "页面访问成功")
            else:
                self.log_test("配置模板页面", False, f"页面访问失败: {response.status_code}")
            
            # 测试任务管理页面
            response = self.session.get(f"{self.base_url}/tasks")
            if response.status_code == 200:
                self.log_test("任务管理页面", True, "页面访问成功")
            else:
                self.log_test("任务管理页面", False, f"页面访问失败: {response.status_code}")
                
            return True
            
        except Exception as e:
            self.log_test("Web界面测试", False, f"界面测试异常: {str(e)}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("NetManagerX 设备状态检查功能完整测试")
        print("=" * 60)
        
        start_time = time.time()
        
        # 1. 登录测试
        if not self.login():
            print("❌ 登录失败，无法继续测试")
            return
        
        # 2. 设备模型测试
        self.test_device_model()
        
        # 3. API接口测试
        self.test_api_endpoints()
        
        # 4. Socket连接测试
        self.test_socket_connection()
        
        # 5. Web界面测试
        self.test_web_interface()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 生成测试报告
        self.generate_report(total_time)
    
    def generate_report(self, total_time):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        print(f"测试耗时: {total_time:.2f}秒")
        
        if failed_tests > 0:
            print(f"\n❌ 失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test_name']}: {result['message']}")
        
        print(f"\n✅ 通过的测试:")
        for result in self.test_results:
            if result['success']:
                print(f"  - {result['test_name']}: {result['message']}")
        
        # 保存详细报告到文件
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'total_time': total_time,
                    'timestamp': datetime.now().isoformat()
                },
                'results': self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细报告已保存到: {report_file}")
        
        print("\n" + "=" * 60)
        if failed_tests == 0:
            print("所有测试通过！设备状态检查功能运行正常！")
        else:
            print(f"有 {failed_tests} 个测试失败，请检查相关功能。")
        print("=" * 60)

def main():
    """主函数"""
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(3)
    
    # 创建测试实例
    tester = DeviceStatusTester()
    
    # 运行所有测试
    tester.run_all_tests()

if __name__ == "__main__":
    main()
