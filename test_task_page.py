import requests
import time

base_url = "http://localhost:5001"

def test_task_creation_page():
    """测试任务创建页面"""
    session = requests.Session()
    
    print("=" * 60)
    print("NetManagerX 任务创建页面测试")
    print("=" * 60)
    
    # 1. 登录
    print("\n1. 登录系统...")
    login_data = {'username': 'admin', 'password': 'admin123'}
    login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"登录状态: {login_response.status_code}")
    
    if login_response.status_code not in [200, 302]:
        print("登录失败！")
        return
    
    # 2. 访问任务列表页面
    print("\n2. 访问任务列表页面...")
    tasks_response = session.get(f"{base_url}/tasks")
    print(f"状态码: {tasks_response.status_code}")
    
    if tasks_response.status_code == 200 and "任务管理" in tasks_response.text:
        print("[PASS] 任务列表页面加载成功")
    else:
        print("[FAIL] 任务列表页面加载失败")
        return
    
    # 3. 访问任务创建页面
    print("\n3. 访问任务创建页面...")
    create_response = session.get(f"{base_url}/tasks/create")
    print(f"状态码: {create_response.status_code}")
    
    if create_response.status_code == 200:
        if "创建任务" in create_response.text:
            print("[PASS] 任务创建页面加载成功")
            
            # 检查关键元素
            checks = [
                ("任务名称", "任务名称" in create_response.text and "name" in create_response.text),
                ("任务类型", "任务类型" in create_response.text and "task_type" in create_response.text),
                ("任务描述", "任务描述" in create_response.text and "description" in create_response.text),
                ("目标设备", "目标设备" in create_response.text and "device_id" in create_response.text),
                ("配置模板", "配置模板" in create_response.text and "template_id" in create_response.text),
                ("执行命令", "执行命令" in create_response.text and "command" in create_response.text),
                ("创建按钮", "创建任务" in create_response.text),
            ]
            
            print("\n页面元素检查:")
            for name, check in checks:
                status = "[PASS]" if check else "[FAIL]"
                print(f"  {status} {name}")
        else:
            print("[FAIL] 页面内容不正确")
    else:
        print("[FAIL] 任务创建页面访问失败")
        return
    
    # 4. 提交任务创建表单（测试）
    print("\n4. 提交任务创建表单（测试）...")
    task_data = {
        'name': f'测试任务_{int(time.time())}',
        'description': '这是一个测试任务',
        'task_type': 'command',
        'device_id': '1',
        'template_id': '',
        'command': 'show version'
    }
    
    submit_response = session.post(f"{base_url}/tasks/create", data=task_data, allow_redirects=False)
    print(f"状态码: {submit_response.status_code}")
    
    if submit_response.status_code == 302:
        print("[PASS] 任务创建表单提交成功（预期会重定向）")
        location = submit_response.headers.get('Location', '')
        print(f"重定向到: {location}")
    elif submit_response.status_code == 200:
        print("[INFO] 任务创建表单提交成功（返回200）")
        if "任务创建成功" in submit_response.text or "success" in submit_response.text.lower():
            print("[PASS] 包含成功消息")
        else:
            print("[INFO] 未找到成功消息（可能需要检查flash消息）")
    else:
        print(f"[FAIL] 任务创建表单提交失败，状态码: {submit_response.status_code}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_task_creation_page()
