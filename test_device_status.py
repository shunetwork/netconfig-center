#!/usr/bin/env python3
"""
设备状态检查功能测试脚本
"""

import requests
import json
import time

def test_device_status_api():
    """测试设备状态检查API"""
    base_url = "http://localhost:5000"
    
    # 登录获取session
    session = requests.Session()
    
    # 登录
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    print("正在登录...")
    login_response = session.post(f"{base_url}/login", data=login_data)
    
    if login_response.status_code == 302:  # 重定向表示登录成功
        print("登录成功")
    else:
        print("登录失败")
        return
    
    # 测试单个设备状态检查
    print("\n测试单个设备状态检查...")
    
    # 先获取设备列表
    devices_response = session.get(f"{base_url}/devices")
    if devices_response.status_code == 200:
        print("设备列表页面访问成功")
    else:
        print("设备列表页面访问失败")
        return
    
    # 测试批量状态检查
    print("\n测试批量设备状态检查...")
    
    status_response = session.post(f"{base_url}/api/devices/status/check-all")
    
    if status_response.status_code == 200:
        result = status_response.json()
        if result['success']:
            print("批量状态检查成功")
            print(f"检查了 {len(result['devices'])} 个设备:")
            
            for device in result['devices']:
                status_icon = "[在线]" if device['status'] == 'online' else "[离线]" if device['status'] == 'offline' else "[未知]"
                response_time = f" ({device['response_time']:.1f}ms)" if device['response_time'] else ""
                print(f"  {status_icon} {device['name']}: {device['status_text']}{response_time}")
        else:
            print(f"批量状态检查失败: {result['message']}")
    else:
        print(f"批量状态检查请求失败: {status_response.status_code}")
    
    print("\n设备状态检查功能测试完成!")

def test_device_status_model():
    """测试设备状态检查模型"""
    print("\n测试设备状态检查模型...")
    
    try:
        # 导入设备模型
        import sys
        sys.path.append('.')
        
        from modern_start import app, Device, db
        
        with app.app_context():
            # 获取所有设备
            devices = Device.query.all()
            
            if not devices:
                print("没有找到设备，请先添加一些设备")
                return
            
            print(f"找到 {len(devices)} 个设备:")
            
            for device in devices:
                print(f"\n检查设备: {device.name} ({device.ip_address}:{device.port})")
                
                # 检查状态
                start_time = time.time()
                status = device.check_status()
                end_time = time.time()
                
                print(f"  状态: {status}")
                print(f"  响应时间: {device.last_response_time:.1f}ms" if device.last_response_time else "  响应时间: N/A")
                print(f"  最后检查: {device.last_check}")
                
                # 获取显示信息
                status_info = device.get_status_display()
                print(f"  显示文本: {status_info['text']}")
                print(f"  CSS类: {status_info['class']}")
            
            # 保存状态到数据库
            db.session.commit()
            print("\n设备状态已保存到数据库")
            
    except Exception as e:
        print(f"模型测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("NetManagerX 设备状态检查功能测试")
    print("=" * 50)
    
    # 测试API功能
    test_device_status_api()
    
    # 测试模型功能
    test_device_status_model()
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("\n使用说明:")
    print("1. 访问 http://localhost:5000/devices")
    print("2. 点击'检查状态'按钮进行批量检查")
    print("3. 点击单个设备的'检查状态'按钮进行单独检查")
    print("4. 状态会实时更新并显示响应时间")
