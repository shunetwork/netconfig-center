"""
SSH客户端模块
基于Netmiko和Paramiko的网络设备SSH连接管理
"""

import socket
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager

try:
    from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
    from netmiko.ssh_exception import SSHException
    import paramiko
except ImportError:
    ConnectHandler = None
    NetMikoTimeoutException = Exception
    NetMikoAuthenticationException = Exception
    SSHException = Exception
    paramiko = None

from app.models import Device, DeviceConnection, DeviceStatus, AuditLog
from app import db

logger = logging.getLogger(__name__)

class SSHClient:
    """SSH客户端类"""
    
    def __init__(self, device: Device, timeout: int = 30):
        """
        初始化SSH客户端
        
        Args:
            device: 设备对象
            timeout: 连接超时时间（秒）
        """
        self.device = device
        self.timeout = timeout
        self.connection = None
        self.connection_record = None
    
    def connect(self) -> Dict[str, Any]:
        """
        建立SSH连接
        
        Returns:
            连接结果字典
        """
        try:
            if not ConnectHandler:
                raise Exception("Netmiko未安装，请安装netmiko包")
            
            # 准备连接参数
            connection_params = self._prepare_connection_params()
            
            # 创建连接记录
            self.connection_record = DeviceConnection(
                device=self.device,
                status='active'
            )
            db.session.add(self.connection_record)
            db.session.commit()
            
            # 建立连接
            self.connection = ConnectHandler(**connection_params)
            
            # 测试连接
            if self.connection.is_alive():
                result = {
                    'success': True,
                    'message': 'SSH连接建立成功',
                    'connection_id': self.connection_record.id
                }
                
                # 更新设备状态
                self.device.update_status(DeviceStatus.ONLINE)
                
                logger.info(f"SSH连接成功: {self.device.name} ({self.device.ip_address})")
                return result
            else:
                raise Exception("连接建立失败")
                
        except NetMikoAuthenticationException as e:
            error_msg = f"SSH认证失败: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except NetMikoTimeoutException as e:
            error_msg = f"SSH连接超时: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except SSHException as e:
            error_msg = f"SSH连接异常: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except Exception as e:
            error_msg = f"SSH连接失败: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
    
    def disconnect(self) -> None:
        """断开SSH连接"""
        try:
            if self.connection and self.connection.is_alive():
                self.connection.disconnect()
                logger.info(f"SSH连接已断开: {self.device.name}")
        except Exception as e:
            logger.warning(f"断开SSH连接时出错: {str(e)}")
        finally:
            # 更新连接记录
            if self.connection_record:
                self.connection_record.close_connection()
                self.connection_record = None
            self.connection = None
    
    def execute_command(self, command: str, delay_factor: float = 1.0) -> Dict[str, Any]:
        """
        执行SSH命令
        
        Args:
            command: 要执行的命令
            delay_factor: 延迟因子
            
        Returns:
            执行结果字典
        """
        if not self.connection or not self.connection.is_alive():
            return {
                'success': False,
                'error': 'SSH连接未建立或已断开',
                'output': None
            }
        
        try:
            start_time = time.time()
            
            # 执行命令
            output = self.connection.send_command(command, delay_factor=delay_factor)
            
            execution_time = time.time() - start_time
            
            logger.info(f"命令执行成功: {self.device.name} - {command}")
            
            return {
                'success': True,
                'output': output,
                'execution_time': execution_time,
                'command': command
            }
            
        except Exception as e:
            error_msg = f"命令执行失败: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'output': None,
                'command': command
            }
    
    def execute_commands(self, commands: List[str], delay_factor: float = 1.0) -> List[Dict[str, Any]]:
        """
        批量执行SSH命令
        
        Args:
            commands: 命令列表
            delay_factor: 延迟因子
            
        Returns:
            执行结果列表
        """
        results = []
        
        for command in commands:
            result = self.execute_command(command, delay_factor)
            results.append(result)
            
            # 如果命令执行失败，可以选择是否继续
            if not result['success']:
                logger.warning(f"命令执行失败，停止后续命令: {command}")
                break
        
        return results
    
    def send_config_commands(self, config_commands: List[str], delay_factor: float = 1.0) -> Dict[str, Any]:
        """
        发送配置命令
        
        Args:
            config_commands: 配置命令列表
            delay_factor: 延迟因子
            
        Returns:
            执行结果字典
        """
        if not self.connection or not self.connection.is_alive():
            return {
                'success': False,
                'error': 'SSH连接未建立或已断开',
                'output': None
            }
        
        try:
            start_time = time.time()
            
            # 发送配置命令
            output = self.connection.send_config_set(config_commands, delay_factor=delay_factor)
            
            execution_time = time.time() - start_time
            
            logger.info(f"配置命令执行成功: {self.device.name} - {len(config_commands)}条命令")
            
            return {
                'success': True,
                'output': output,
                'execution_time': execution_time,
                'commands': config_commands
            }
            
        except Exception as e:
            error_msg = f"配置命令执行失败: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'output': None,
                'commands': config_commands
            }
    
    def get_prompt(self) -> str:
        """获取设备提示符"""
        if not self.connection or not self.connection.is_alive():
            return ""
        
        try:
            return self.connection.find_prompt()
        except Exception as e:
            logger.warning(f"获取提示符失败: {str(e)}")
            return ""
    
    def _prepare_connection_params(self) -> Dict[str, Any]:
        """准备连接参数"""
        params = {
            'device_type': self._get_device_type(),
            'host': self.device.ip_address,
            'username': self.device.username,
            'port': self.device.port,
            'timeout': self.timeout,
            'banner_timeout': 30,
            'auth_timeout': 30,
        }
        
        # 添加密码
        password = self.device.get_password()
        if password:
            params['password'] = password
        
        # 添加SSH密钥
        if self.device.ssh_key_path:
            params['key_file'] = self.device.ssh_key_path
        
        # 添加enable密码
        enable_password = self.device.get_enable_password()
        if enable_password:
            params['secret'] = enable_password
        
        return params
    
    def _get_device_type(self) -> str:
        """获取Netmiko设备类型"""
        device_type_mapping = {
            'cisco_router': 'cisco_ios',
            'cisco_switch': 'cisco_ios',
            'cisco_asa': 'cisco_asa',
            'cisco_wlc': 'cisco_wlc',
            'other': 'cisco_ios'
        }
        
        return device_type_mapping.get(self.device.device_type.value, 'cisco_ios')
    
    def _handle_connection_error(self, error_msg: str) -> Dict[str, Any]:
        """处理连接错误"""
        # 更新设备状态
        self.device.update_status(DeviceStatus.ERROR)
        
        # 关闭连接记录
        if self.connection_record:
            self.connection_record.status = 'failed'
            self.connection_record.error_message = error_msg
            self.connection_record.close_connection()
        
        return {
            'success': False,
            'error': error_msg,
            'connection_id': self.connection_record.id if self.connection_record else None
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

class SSHConnectionManager:
    """SSH连接管理器"""
    
    def __init__(self, max_connections: int = 10):
        """
        初始化连接管理器
        
        Args:
            max_connections: 最大连接数
        """
        self.max_connections = max_connections
        self.active_connections = {}
        self._lock = None  # 可以添加线程锁
    
    @contextmanager
    def get_connection(self, device: Device, timeout: int = 30):
        """
        获取设备连接的上下文管理器
        
        Args:
            device: 设备对象
            timeout: 连接超时时间
            
        Yields:
            SSHClient: SSH客户端对象
        """
        client = SSHClient(device, timeout)
        
        try:
            result = client.connect()
            if result['success']:
                self.active_connections[device.id] = client
                yield client
            else:
                raise Exception(result['error'])
        finally:
            client.disconnect()
            if device.id in self.active_connections:
                del self.active_connections[device.id]
    
    def get_active_connections_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)
    
    def close_all_connections(self) -> None:
        """关闭所有连接"""
        for client in self.active_connections.values():
            try:
                client.disconnect()
            except Exception as e:
                logger.warning(f"关闭连接时出错: {str(e)}")
        
        self.active_connections.clear()

# 全局连接管理器实例
ssh_manager = SSHConnectionManager()

class SSHService:
    """SSH服务类"""
    
    @staticmethod
    def test_connection(device: Device, timeout: int = 30) -> Dict[str, Any]:
        """
        测试SSH连接
        
        Args:
            device: 设备对象
            timeout: 连接超时时间
            
        Returns:
            测试结果字典
        """
        with ssh_manager.get_connection(device, timeout) as client:
            # 执行简单命令测试连接
            result = client.execute_command('show version')
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'SSH连接测试成功',
                    'output': result['output'][:500]  # 只返回前500字符
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
    
    @staticmethod
    def execute_command(device: Device, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        在设备上执行命令
        
        Args:
            device: 设备对象
            command: 要执行的命令
            timeout: 连接超时时间
            
        Returns:
            执行结果字典
        """
        with ssh_manager.get_connection(device, timeout) as client:
            return client.execute_command(command)
    
    @staticmethod
    def execute_commands(device: Device, commands: List[str], timeout: int = 30) -> List[Dict[str, Any]]:
        """
        在设备上批量执行命令
        
        Args:
            device: 设备对象
            commands: 命令列表
            timeout: 连接超时时间
            
        Returns:
            执行结果列表
        """
        with ssh_manager.get_connection(device, timeout) as client:
            return client.execute_commands(commands)
    
    @staticmethod
    def send_config(device: Device, config_commands: List[str], timeout: int = 30) -> Dict[str, Any]:
        """
        发送配置命令到设备
        
        Args:
            device: 设备对象
            config_commands: 配置命令列表
            timeout: 连接超时时间
            
        Returns:
            执行结果字典
        """
        with ssh_manager.get_connection(device, timeout) as client:
            return client.send_config_commands(config_commands)
