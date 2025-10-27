"""
设备管理服务模块
包含设备连接测试、状态检测、批量操作等服务
"""

import socket
import subprocess
import platform
from datetime import datetime
from typing import List, Dict, Any, Optional
from app import db
from app.models import Device, DeviceGroup, DeviceConnection, DeviceStatus, AuditLog

class DeviceConnectionService:
    """设备连接服务"""
    
    @staticmethod
    def test_ping(ip_address: str, timeout: int = 5) -> Dict[str, Any]:
        """测试Ping连通性"""
        try:
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip_address]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), ip_address]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            success = result.returncode == 0
            
            return {
                'success': success,
                'message': 'Ping成功' if success else f'Ping失败: {result.stderr}',
                'details': result.stdout
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': f'Ping超时 (>{timeout}秒)',
                'details': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Ping测试异常: {str(e)}',
                'details': None
            }
    
    @staticmethod
    def test_tcp_port(ip_address: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """测试TCP端口连通性"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            
            success = result == 0
            return {
                'success': success,
                'message': f'端口{port}连接成功' if success else f'端口{port}连接失败',
                'details': f'连接结果代码: {result}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'端口连接测试异常: {str(e)}',
                'details': None
            }

class DeviceStatusService:
    """设备状态服务"""
    
    @staticmethod
    def update_device_status(device: Device, status: DeviceStatus, message: str = '') -> None:
        """更新设备状态"""
        device.status = status
        device.last_checked = datetime.utcnow()
        db.session.add(device)
        
        # 记录状态变更日志
        AuditLog.log_action(
            user=None,  # 系统自动更新
            action='device_status_update',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=True,
            details={'status': status.value, 'message': message}
        )
        db.session.commit()
    
    @staticmethod
    def check_device_status(device: Device) -> Dict[str, Any]:
        """检查设备状态"""
        results = {}
        
        # Ping测试
        ping_result = DeviceConnectionService.test_ping(device.ip_address)
        results['ping'] = ping_result
        
        # 端口连接测试
        port_result = DeviceConnectionService.test_tcp_port(device.ip_address, device.port)
        results['port'] = port_result
        
        # 综合状态判断
        if ping_result['success'] and port_result['success']:
            status = DeviceStatus.ONLINE
            message = '设备在线'
        elif ping_result['success']:
            status = DeviceStatus.ERROR
            message = '设备可达但端口不通'
        else:
            status = DeviceStatus.OFFLINE
            message = '设备不可达'
        
        # 更新设备状态
        DeviceStatusService.update_device_status(device, status, message)
        
        return {
            'status': status.value,
            'message': message,
            'details': results
        }
    
    @staticmethod
    def batch_check_status(device_ids: List[int]) -> Dict[str, Any]:
        """批量检查设备状态"""
        devices = Device.query.filter(Device.id.in_(device_ids)).all()
        results = {}
        
        for device in devices:
            try:
                result = DeviceStatusService.check_device_status(device)
                results[device.id] = {
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'result': result
                }
            except Exception as e:
                results[device.id] = {
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'result': {
                        'status': 'error',
                        'message': f'状态检查异常: {str(e)}',
                        'details': None
                    }
                }
        
        return results

class DeviceManagementService:
    """设备管理服务"""
    
    @staticmethod
    def create_device(device_data: Dict[str, Any], user_id: int) -> Device:
        """创建设备"""
        device = Device(
            name=device_data['name'],
            ip_address=device_data['ip_address'],
            hostname=device_data.get('hostname'),
            device_type=device_data['device_type'],
            connection_type=device_data['connection_type'],
            port=device_data.get('port', 22),
            username=device_data['username'],
            description=device_data.get('description'),
            location=device_data.get('location'),
            vendor=device_data.get('vendor', 'Cisco'),
            model=device_data.get('model'),
            serial_number=device_data.get('serial_number'),
            software_version=device_data.get('software_version'),
            group_id=device_data.get('group_id')
        )
        
        # 设置密码
        if device_data.get('password'):
            device.set_password(device_data['password'])
        
        if device_data.get('enable_password'):
            device.set_enable_password(device_data['enable_password'])
        
        if device_data.get('ssh_key_path'):
            device.ssh_key_path = device_data['ssh_key_path']
        
        db.session.add(device)
        db.session.commit()
        
        # 记录创建日志
        AuditLog.log_action(
            user_id=user_id,
            action='create_device',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=True,
            details={'ip_address': device.ip_address, 'device_type': device.device_type.value}
        )
        
        return device
    
    @staticmethod
    def update_device(device: Device, device_data: Dict[str, Any], user_id: int) -> Device:
        """更新设备"""
        # 保存原始数据用于日志
        original_data = {
            'name': device.name,
            'ip_address': device.ip_address,
            'username': device.username
        }
        
        # 更新基本信息
        device.name = device_data['name']
        device.ip_address = device_data['ip_address']
        device.hostname = device_data.get('hostname')
        device.device_type = device_data['device_type']
        device.connection_type = device_data['connection_type']
        device.port = device_data.get('port', 22)
        device.username = device_data['username']
        device.description = device_data.get('description')
        device.location = device_data.get('location')
        device.vendor = device_data.get('vendor', 'Cisco')
        device.model = device_data.get('model')
        device.serial_number = device_data.get('serial_number')
        device.software_version = device_data.get('software_version')
        device.group_id = device_data.get('group_id')
        
        # 更新密码
        if device_data.get('password'):
            device.set_password(device_data['password'])
        
        if device_data.get('enable_password'):
            device.set_enable_password(device_data['enable_password'])
        
        if device_data.get('ssh_key_path'):
            device.ssh_key_path = device_data['ssh_key_path']
        
        db.session.add(device)
        db.session.commit()
        
        # 记录更新日志
        AuditLog.log_action(
            user_id=user_id,
            action='update_device',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=True,
            details={
                'original': original_data,
                'updated': {
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'username': device.username
                }
            }
        )
        
        return device
    
    @staticmethod
    def delete_device(device: Device, user_id: int) -> None:
        """删除设备"""
        device_name = device.name
        device_id = device.id
        
        # 记录删除日志
        AuditLog.log_action(
            user_id=user_id,
            action='delete_device',
            resource_type='device',
            resource_id=device_id,
            resource_name=device_name,
            success=True,
            details={'ip_address': device.ip_address}
        )
        
        db.session.delete(device)
        db.session.commit()

class DeviceGroupService:
    """设备组管理服务"""
    
    @staticmethod
    def create_group(group_data: Dict[str, Any], user_id: int) -> DeviceGroup:
        """创建设备组"""
        group = DeviceGroup(
            name=group_data['name'],
            description=group_data.get('description')
        )
        
        db.session.add(group)
        db.session.commit()
        
        # 记录创建日志
        AuditLog.log_action(
            user_id=user_id,
            action='create_device_group',
            resource_type='device_group',
            resource_id=group.id,
            resource_name=group.name,
            success=True
        )
        
        return group
    
    @staticmethod
    def update_group(group: DeviceGroup, group_data: Dict[str, Any], user_id: int) -> DeviceGroup:
        """更新设备组"""
        original_name = group.name
        
        group.name = group_data['name']
        group.description = group_data.get('description')
        
        db.session.add(group)
        db.session.commit()
        
        # 记录更新日志
        AuditLog.log_action(
            user_id=user_id,
            action='update_device_group',
            resource_type='device_group',
            resource_id=group.id,
            resource_name=group.name,
            success=True,
            details={'original_name': original_name}
        )
        
        return group
    
    @staticmethod
    def delete_group(group: DeviceGroup, user_id: int) -> None:
        """删除设备组"""
        group_name = group.name
        group_id = group.id
        device_count = group.devices.count()
        
        # 记录删除日志
        AuditLog.log_action(
            user_id=user_id,
            action='delete_device_group',
            resource_type='device_group',
            resource_id=group_id,
            resource_name=group_name,
            success=True,
            details={'device_count': device_count}
        )
        
        db.session.delete(group)
        db.session.commit()
