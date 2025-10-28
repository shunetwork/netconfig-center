#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetManagerX 完整功能测试套件
测试所有功能模块：设备管理、分组管理、模板管理、任务管理、任务执行
"""

import os
import sys
import requests
import json
import time
import threading
from datetime import datetime

# 设置UTF-8编码输出
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')

BASE_URL = 'http://localhost:5001'
LOGIN_URL = f'{BASE_URL}/login'
DEVICES_URL = f'{BASE_URL}/devices'
TEMPLATES_URL = f'{BASE_URL}/templates'
TASKS_URL = f'{BASE_URL}/tasks'
GROUPS_URL = f'{BASE_URL}/devices/groups'

# 登录凭证
USERNAME = 'admin'
PASSWORD = 'admin123'

class TestLogger:
    """测试日志记录器"""
    def __init__(self):
        self.log_file = f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.results = []
    
    def log(self, level, message, test_name="", details=""):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] [{test_name}] {message}"
        if details:
            log_entry += f"\n详情: {details}"
        
        print(log_entry)
        
        # 写入文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
        
        # 记录结果
        self.results.append({
            'timestamp': timestamp,
            'level': level,
            'test_name': test_name,
            'message': message,
            'details': details
        })
    
    def success(self, message, test_name="", details=""):
        self.log("SUCCESS", message, test_name, details)
    
    def error(self, message, test_name="", details=""):
        self.log("ERROR", message, test_name, details)
    
    def info(self, message, test_name="", details=""):
        self.log("INFO", message, test_name, details)
    
    def warning(self, message, test_name="", details=""):
        self.log("WARNING", message, test_name, details)

logger = TestLogger()

def login():
    """登录并返回session"""
    try:
        session = requests.Session()
        response = session.post(LOGIN_URL, data={
            'username': USERNAME,
            'password': PASSWORD
        })
        if response.status_code == 200 or response.status_code == 302:
            logger.success("登录成功", "AUTH")
            return session
        else:
            logger.error(f"登录失败: {response.status_code}", "AUTH")
            return None
    except Exception as e:
        logger.error(f"登录异常: {str(e)}", "AUTH")
        return None

def test_health_check(session):
    """测试健康检查"""
    logger.info("开始测试健康检查", "HEALTH")
    try:
        response = session.get(f'{BASE_URL}/health')
        if response.status_code == 200:
            data = response.json()
            logger.success("健康检查通过", "HEALTH", f"状态: {data.get('status')}")
            return True
        else:
            logger.error(f"健康检查失败: {response.status_code}", "HEALTH")
            return False
    except Exception as e:
        logger.error(f"健康检查异常: {str(e)}", "HEALTH")
        return False

def test_device_management(session):
    """测试设备管理功能"""
    logger.info("开始测试设备管理", "DEVICE")
    results = []
    
    try:
        # 1. 获取设备列表
        response = session.get(DEVICES_URL)
        if response.status_code == 200:
            logger.success("设备列表获取成功", "DEVICE")
            results.append(True)
        else:
            logger.error(f"设备列表获取失败: {response.status_code}", "DEVICE")
            results.append(False)
        
        # 2. 添加设备
        device_data = {
            'name': f'TestDevice_{int(time.time())}',
            'ip_address': '192.168.1.100',
            'hostname': 'test-device',
            'device_type': 'cisco',
            'connection_type': 'ssh',
            'port': 22,
            'username': 'admin',
            'password': 'password123',
            'description': '测试设备'
        }
        
        response = session.post(f'{DEVICES_URL}/add', data=device_data)
        if response.status_code in [200, 302]:
            logger.success("设备添加成功", "DEVICE", f"设备名: {device_data['name']}")
            results.append(True)
        else:
            logger.error(f"设备添加失败: {response.status_code}", "DEVICE")
            results.append(False)
        
        # 3. 获取设备API
        response = session.get(f'{BASE_URL}/api/devices')
        if response.status_code == 200:
            devices = response.json()
            # 处理不同的API响应格式
            if isinstance(devices, list):
                device_count = len(devices)
            elif isinstance(devices, dict) and 'devices' in devices:
                device_count = len(devices['devices'])
            else:
                device_count = 0
            logger.success(f"设备API获取成功，共{device_count}个设备", "DEVICE")
            results.append(True)
        else:
            logger.error(f"设备API获取失败: {response.status_code}", "DEVICE")
            results.append(False)
        
        # 4. 设备状态检查
        response = session.post(f'{BASE_URL}/api/devices/status/check-all')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.success("设备状态检查成功", "DEVICE")
                results.append(True)
            else:
                logger.warning("设备状态检查返回失败", "DEVICE", data.get('message', ''))
                results.append(False)
        else:
            logger.error(f"设备状态检查失败: {response.status_code}", "DEVICE")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        logger.info(f"设备管理测试完成，成功率: {success_rate:.1f}%", "DEVICE")
        return success_rate >= 75
        
    except Exception as e:
        logger.error(f"设备管理测试异常: {str(e)}", "DEVICE")
        return False

def test_template_management(session):
    """测试模板管理功能"""
    logger.info("开始测试模板管理", "TEMPLATE")
    results = []
    
    try:
        # 1. 获取模板列表
        response = session.get(TEMPLATES_URL)
        if response.status_code == 200:
            logger.success("模板列表获取成功", "TEMPLATE")
            results.append(True)
        else:
            logger.error(f"模板列表获取失败: {response.status_code}", "TEMPLATE")
            results.append(False)
        
        # 2. 添加模板
        template_data = {
            'name': f'TestTemplate_{int(time.time())}',
            'description': '测试模板',
            'content': 'show version\nshow running-config',
            'template_type': 'command',
            'category': 'general',
            'variables': '{}',
            'is_active': 'on'
        }
        
        response = session.post(f'{TEMPLATES_URL}/add', data=template_data)
        if response.status_code in [200, 302]:
            logger.success("模板添加成功", "TEMPLATE", f"模板名: {template_data['name']}")
            results.append(True)
        else:
            logger.error(f"模板添加失败: {response.status_code}", "TEMPLATE")
            results.append(False)
        
        # 3. 获取模板API
        response = session.get(f'{BASE_URL}/api/templates')
        if response.status_code == 200:
            templates = response.json()
            # 处理不同的API响应格式
            if isinstance(templates, list):
                template_count = len(templates)
            elif isinstance(templates, dict) and 'templates' in templates:
                template_count = len(templates['templates'])
            else:
                template_count = 0
            logger.success(f"模板API获取成功，共{template_count}个模板", "TEMPLATE")
            results.append(True)
        else:
            logger.error(f"模板API获取失败: {response.status_code}", "TEMPLATE")
            results.append(False)
        
        # 4. 测试模板变量API
        response = session.get(f'{BASE_URL}/api/templates/1/variables')
        if response.status_code == 200:
            logger.success("模板变量API获取成功", "TEMPLATE")
            results.append(True)
        else:
            logger.warning(f"模板变量API获取失败: {response.status_code}", "TEMPLATE")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        logger.info(f"模板管理测试完成，成功率: {success_rate:.1f}%", "TEMPLATE")
        return success_rate >= 75
        
    except Exception as e:
        logger.error(f"模板管理测试异常: {str(e)}", "TEMPLATE")
        return False

def test_task_management(session):
    """测试任务管理功能"""
    logger.info("开始测试任务管理", "TASK")
    results = []
    
    try:
        # 1. 获取任务列表
        response = session.get(TASKS_URL)
        if response.status_code == 200:
            logger.success("任务列表获取成功", "TASK")
            results.append(True)
        else:
            logger.error(f"任务列表获取失败: {response.status_code}", "TASK")
            results.append(False)
        
        # 2. 创建任务
        task_data = {
            'name': f'TestTask_{int(time.time())}',
            'description': '测试任务',
            'task_type': 'command',
            'command': 'show version',
            'device_id': '1'
        }
        
        response = session.post(f'{TASKS_URL}/create', data=task_data)
        if response.status_code in [200, 302]:
            logger.success("任务创建成功", "TASK", f"任务名: {task_data['name']}")
            results.append(True)
        else:
            logger.error(f"任务创建失败: {response.status_code}", "TASK")
            results.append(False)
        
        # 3. 获取任务API
        response = session.get(f'{BASE_URL}/api/tasks')
        if response.status_code == 200:
            tasks = response.json()
            logger.success(f"任务API获取成功，共{len(tasks)}个任务", "TASK")
            results.append(True)
        else:
            logger.error(f"任务API获取失败: {response.status_code}", "TASK")
            results.append(False)
        
        # 4. 获取任务详情
        response = session.get(f'{BASE_URL}/api/tasks/1')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.success("任务详情获取成功", "TASK")
                results.append(True)
            else:
                logger.warning("任务详情获取失败", "TASK", data.get('message', ''))
                results.append(False)
        else:
            logger.warning(f"任务详情获取失败: {response.status_code}", "TASK")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        logger.info(f"任务管理测试完成，成功率: {success_rate:.1f}%", "TASK")
        return success_rate >= 75
        
    except Exception as e:
        logger.error(f"任务管理测试异常: {str(e)}", "TASK")
        return False

def test_task_execution(session):
    """测试任务执行功能"""
    logger.info("开始测试任务执行", "EXECUTION")
    results = []
    
    try:
        # 0. 重置任务状态
        response = session.post(f'{BASE_URL}/api/tasks/1/reset')
        if response.status_code == 200:
            logger.info("任务状态已重置", "EXECUTION")
        else:
            logger.warning(f"任务重置失败: {response.status_code}", "EXECUTION")
        
        # 1. 执行任务
        response = session.post(f'{BASE_URL}/api/tasks/1/execute')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.success("任务执行启动成功", "EXECUTION", f"状态: {data.get('status')}")
                results.append(True)
            else:
                logger.warning("任务执行启动失败", "EXECUTION", data.get('message', ''))
                results.append(False)
        else:
            logger.error(f"任务执行启动失败: {response.status_code}", "EXECUTION")
            results.append(False)
        
        # 2. 等待执行完成
        logger.info("等待任务执行完成...", "EXECUTION")
        time.sleep(5)
        
        # 3. 检查执行结果
        response = session.get(f'{BASE_URL}/api/tasks/1')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                task = data['task']
                logger.success(f"任务执行完成，状态: {task.get('status')}, 进度: {task.get('progress')}%", "EXECUTION")
                results.append(True)
                
                # 检查设备执行结果
                if 'device_results' in task and task['device_results']:
                    for result in task['device_results']:
                        logger.info(f"设备 {result['device_name']}: {result['status']}", "EXECUTION")
            else:
                logger.warning("任务执行结果获取失败", "EXECUTION", data.get('message', ''))
                results.append(False)
        else:
            logger.error(f"任务执行结果获取失败: {response.status_code}", "EXECUTION")
            results.append(False)
        
        # 4. 获取任务日志
        response = session.get(f'{BASE_URL}/api/tasks/1/logs')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logs = data.get('logs', [])
                logger.success(f"任务日志获取成功，共{len(logs)}条日志", "EXECUTION")
                results.append(True)
            else:
                logger.warning("任务日志获取失败", "EXECUTION", data.get('message', ''))
                results.append(False)
        else:
            logger.warning(f"任务日志获取失败: {response.status_code}", "EXECUTION")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        logger.info(f"任务执行测试完成，成功率: {success_rate:.1f}%", "EXECUTION")
        return success_rate >= 50  # 执行测试要求较低
        
    except Exception as e:
        logger.error(f"任务执行测试异常: {str(e)}", "EXECUTION")
        return False

def test_device_groups(session):
    """测试设备分组功能"""
    logger.info("开始测试设备分组", "GROUP")
    results = []
    
    try:
        # 1. 获取分组列表
        response = session.get(GROUPS_URL)
        if response.status_code == 200:
            logger.success("分组列表获取成功", "GROUP")
            results.append(True)
        else:
            logger.error(f"分组列表获取失败: {response.status_code}", "GROUP")
            results.append(False)
        
        # 2. 添加分组
        group_data = {
            'name': f'TestGroup_{int(time.time())}',
            'description': '测试分组'
        }
        
        response = session.post(f'{GROUPS_URL}/add', data=group_data)
        if response.status_code in [200, 302]:
            logger.success("分组添加成功", "GROUP", f"分组名: {group_data['name']}")
            results.append(True)
        else:
            logger.error(f"分组添加失败: {response.status_code}", "GROUP")
            results.append(False)
        
        # 3. 获取分组API
        response = session.get(f'{BASE_URL}/api/device-groups')
        if response.status_code == 200:
            groups = response.json()
            # 处理不同的API响应格式
            if isinstance(groups, list):
                group_count = len(groups)
            elif isinstance(groups, dict) and 'groups' in groups:
                group_count = len(groups['groups'])
            else:
                group_count = 0
            logger.success(f"分组API获取成功，共{group_count}个分组", "GROUP")
            results.append(True)
        else:
            logger.error(f"分组API获取失败: {response.status_code}", "GROUP")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        logger.info(f"设备分组测试完成，成功率: {success_rate:.1f}%", "GROUP")
        return success_rate >= 75
        
    except Exception as e:
        logger.error(f"设备分组测试异常: {str(e)}", "GROUP")
        return False

def test_vlan_template_execution(session):
    """测试VLAN模板执行（重点测试）"""
    logger.info("开始测试VLAN模板执行", "VLAN_TEST")
    results = []
    
    try:
        # 1. 创建VLAN任务
        vlan_task_data = {
            'name': f'VLANTest_{int(time.time())}',
            'description': 'VLAN测试任务',
            'task_type': 'config',
            'template_id': '1',  # 使用批量添加VLAN模板
            'template_variables': json.dumps({'vlans': '200:TestVLAN200\n300:TestVLAN300'}),
            'device_id': '1'
        }
        
        response = session.post(f'{TASKS_URL}/create', data=vlan_task_data)
        if response.status_code in [200, 302]:
            logger.success("VLAN任务创建成功", "VLAN_TEST", f"任务名: {vlan_task_data['name']}")
            results.append(True)
        else:
            logger.error(f"VLAN任务创建失败: {response.status_code}", "VLAN_TEST")
            results.append(False)
            return False
        
        # 2. 重置并执行VLAN任务
        response = session.post(f'{BASE_URL}/api/tasks/1/reset')
        if response.status_code == 200:
            logger.info("VLAN任务状态已重置", "VLAN_TEST")
        
        response = session.post(f'{BASE_URL}/api/tasks/1/execute')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.success("VLAN任务执行启动成功", "VLAN_TEST")
                results.append(True)
            else:
                logger.error("VLAN任务执行启动失败", "VLAN_TEST", data.get('message', ''))
                results.append(False)
        else:
            logger.error(f"VLAN任务执行启动失败: {response.status_code}", "VLAN_TEST")
            results.append(False)
        
        # 3. 监控执行过程
        logger.info("监控VLAN任务执行过程...", "VLAN_TEST")
        for i in range(10):  # 监控10次，每次间隔2秒
            time.sleep(2)
            response = session.get(f'{BASE_URL}/api/tasks/1')
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    task = data['task']
                    status = task.get('status')
                    progress = task.get('progress', 0)
                    logger.info(f"任务状态: {status}, 进度: {progress}%", "VLAN_TEST")
                    
                    if status in ['completed', 'failed']:
                        break
        
        # 4. 检查最终结果
        response = session.get(f'{BASE_URL}/api/tasks/1')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                task = data['task']
                final_status = task.get('status')
                final_progress = task.get('progress', 0)
                
                if final_status == 'completed' and final_progress == 100:
                    logger.success("VLAN任务执行成功完成", "VLAN_TEST", f"进度: {final_progress}%")
                    results.append(True)
                elif final_status == 'failed':
                    logger.error("VLAN任务执行失败", "VLAN_TEST", f"进度: {final_progress}%")
                    results.append(False)
                else:
                    logger.warning(f"VLAN任务状态异常: {final_status}, 进度: {final_progress}%", "VLAN_TEST")
                    results.append(False)
                
                # 检查设备执行结果
                if 'device_results' in task and task['device_results']:
                    for result in task['device_results']:
                        device_status = result['status']
                        device_name = result['device_name']
                        if device_status == 'success':
                            logger.success(f"设备 {device_name} 执行成功", "VLAN_TEST")
                        else:
                            logger.error(f"设备 {device_name} 执行失败", "VLAN_TEST", result.get('error_message', ''))
            else:
                logger.error("VLAN任务结果获取失败", "VLAN_TEST", data.get('message', ''))
                results.append(False)
        else:
            logger.error(f"VLAN任务结果获取失败: {response.status_code}", "VLAN_TEST")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        logger.info(f"VLAN模板执行测试完成，成功率: {success_rate:.1f}%", "VLAN_TEST")
        return success_rate >= 75
        
    except Exception as e:
        logger.error(f"VLAN模板执行测试异常: {str(e)}", "VLAN_TEST")
        return False

def generate_test_report():
    """生成测试报告"""
    logger.info("生成测试报告", "REPORT")
    
    # 统计结果
    total_tests = len(logger.results)
    success_count = len([r for r in logger.results if r['level'] == 'SUCCESS'])
    error_count = len([r for r in logger.results if r['level'] == 'ERROR'])
    warning_count = len([r for r in logger.results if r['level'] == 'WARNING'])
    
    # 按测试模块统计
    modules = {}
    for result in logger.results:
        test_name = result['test_name']
        if test_name not in modules:
            modules[test_name] = {'success': 0, 'error': 0, 'warning': 0, 'info': 0}
        modules[test_name][result['level'].lower()] += 1
    
    # 生成报告
    report = f"""
========================================
NetManagerX 完整功能测试报告
========================================
测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
日志文件: {logger.log_file}

总体统计:
- 总测试项: {total_tests}
- 成功: {success_count}
- 错误: {error_count}
- 警告: {warning_count}
- 成功率: {(success_count/total_tests*100):.1f}%

模块统计:
"""
    
    for module, stats in modules.items():
        total = sum(stats.values())
        success_rate = (stats['success'] / total * 100) if total > 0 else 0
        report += f"- {module}: {stats['success']}/{total} ({success_rate:.1f}%)\n"
    
    report += f"""
详细日志请查看: {logger.log_file}

测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================
"""
    
    # 保存报告
    with open(f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    logger.info("测试报告已生成", "REPORT")

def main():
    """主测试函数"""
    logger.info("开始NetManagerX完整功能测试", "MAIN")
    
    # 登录
    session = login()
    if not session:
        logger.error("无法登录，测试终止", "MAIN")
        return
    
    # 执行各项测试
    test_results = {}
    
    # 1. 健康检查
    test_results['health'] = test_health_check(session)
    
    # 2. 设备管理
    test_results['device'] = test_device_management(session)
    
    # 3. 模板管理
    test_results['template'] = test_template_management(session)
    
    # 4. 任务管理
    test_results['task'] = test_task_management(session)
    
    # 5. 设备分组
    test_results['group'] = test_device_groups(session)
    
    # 6. 任务执行
    test_results['execution'] = test_task_execution(session)
    
    # 7. VLAN模板执行（重点测试）
    test_results['vlan'] = test_vlan_template_execution(session)
    
    # 生成报告
    generate_test_report()
    
    # 输出测试结果摘要
    logger.info("测试结果摘要:", "MAIN")
    for test_name, result in test_results.items():
        status = "通过" if result else "失败"
        logger.info(f"{test_name}: {status}", "MAIN")
    
    logger.info("NetManagerX完整功能测试完成", "MAIN")

if __name__ == '__main__':
    main()
