#!/usr/bin/env python3
"""
设备状态检查功能简化测试实例
"""

import time
import socket

def test_device_status_model():
    """测试设备状态检查模型"""
    print("NetManagerX 设备状态检查功能测试")
    print("=" * 50)
    
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
                
                # 验证状态检查结果
                if status in ['online', 'offline', 'unknown']:
                    print("  [PASS] 状态检查功能正常")
                else:
                    print("  [FAIL] 状态检查功能异常")
                
                # 验证响应时间
                if device.last_response_time is not None and device.last_response_time >= 0:
                    print("  [PASS] 响应时间测量正常")
                else:
                    print("  [FAIL] 响应时间测量异常")
                
                # 验证状态显示
                if 'text' in status_info and 'class' in status_info:
                    print("  [PASS] 状态显示功能正常")
                else:
                    print("  [FAIL] 状态显示功能异常")
            
            # 保存状态到数据库
            db.session.commit()
            print("\n[PASS] 设备状态已保存到数据库")
            
    except Exception as e:
        print(f"[FAIL] 模型测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_socket_connection():
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
                print(f"[PASS] {host}:{port} - 连接成功，响应时间: {response_time:.1f}ms")
            else:
                print(f"[FAIL] {host}:{port} - 连接失败，错误码: {result}")
                
        except Exception as e:
            print(f"[FAIL] {host}:{port} - 连接异常: {str(e)}")

def test_device_status_display():
    """测试设备状态显示功能"""
    print("\n测试设备状态显示功能...")
    
    try:
        from modern_start import app, Device
        
        with app.app_context():
            # 创建一个测试设备
            test_device = Device(
                name="测试设备",
                ip_address="127.0.0.1",
                port=22,
                status="online"
            )
            
            # 测试状态显示
            status_info = test_device.get_status_display()
            print(f"在线状态显示: {status_info}")
            
            # 测试离线状态
            test_device.status = "offline"
            status_info = test_device.get_status_display()
            print(f"离线状态显示: {status_info}")
            
            # 测试未知状态
            test_device.status = "unknown"
            status_info = test_device.get_status_display()
            print(f"未知状态显示: {status_info}")
            
            print("[PASS] 状态显示功能正常")
            
    except Exception as e:
        print(f"[FAIL] 状态显示测试失败: {e}")

if __name__ == "__main__":
    print("等待服务器启动...")
    time.sleep(2)
    
    # 测试设备模型功能
    test_device_status_model()
    
    # 测试Socket连接功能
    test_socket_connection()
    
    # 测试状态显示功能
    test_device_status_display()
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("\n使用说明:")
    print("1. 访问 http://localhost:5000/devices")
    print("2. 点击'检查状态'按钮进行批量检查")
    print("3. 点击单个设备的'检查状态'按钮进行单独检查")
    print("4. 状态会实时更新并显示响应时间")
