#!/usr/bin/env python3
"""
简化的设备状态检查功能测试
"""

def test_device_status_model():
    """测试设备状态检查模型"""
    print("测试设备状态检查模型...")
    
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
    
    # 测试模型功能
    test_device_status_model()
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("\n使用说明:")
    print("1. 访问 http://localhost:5000/devices")
    print("2. 点击'检查状态'按钮进行批量检查")
    print("3. 点击单个设备的'检查状态'按钮进行单独检查")
    print("4. 状态会实时更新并显示响应时间")
