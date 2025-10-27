"""
Telnet客户端模块
基于Python telnetlib的网络设备Telnet连接管理
"""

import telnetlib3
import socket
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager

from app.models import Device, DeviceConnection, DeviceStatus
from app import db

logger = logging.getLogger(__name__)

class TelnetClient:
    """Telnet客户端类"""
    
    def __init__(self, device: Device, timeout: int = 30):
        """
        初始化Telnet客户端
        
        Args:
            device: 设备对象
            timeout: 连接超时时间（秒）
        """
        self.device = device
        self.timeout = timeout
        self.telnet = None
        self.connection_record = None
    
    def connect(self) -> Dict[str, Any]:
        """
        建立Telnet连接
        
        Returns:
            连接结果字典
        """
        try:
            # 创建连接记录
            self.connection_record = DeviceConnection(
                device=self.device,
                status='active'
            )
            db.session.add(self.connection_record)
            db.session.commit()
            
            # 建立Telnet连接
            self.telnet = telnetlib.Telnet(self.device.ip_address, self.device.port, timeout=self.timeout)
            
            # 等待登录提示
            self.telnet.read_until(b"Username:", timeout=10)
            
            # 发送用户名
            username = self.device.username.encode('ascii') + b'\n'
            self.telnet.write(username)
            
            # 等待密码提示
            self.telnet.read_until(b"Password:", timeout=10)
            
            # 发送密码
            password = self.device.get_password()
            if password:
                password_bytes = password.encode('ascii') + b'\n'
                self.telnet.write(password_bytes)
            
            # 等待登录完成
            time.sleep(2)
            
            # 检查连接是否成功
            if self.telnet.get_socket():
                result = {
                    'success': True,
                    'message': 'Telnet连接建立成功',
                    'connection_id': self.connection_record.id
                }
                
                # 更新设备状态
                self.device.update_status(DeviceStatus.ONLINE)
                
                logger.info(f"Telnet连接成功: {self.device.name} ({self.device.ip_address})")
                return result
            else:
                raise Exception("连接建立失败")
                
        except socket.timeout:
            error_msg = f"Telnet连接超时"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except socket.gaierror as e:
            error_msg = f"Telnet连接失败: 无法解析主机名 - {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except ConnectionRefusedError:
            error_msg = f"Telnet连接被拒绝: 端口{self.device.port}可能未开放"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except Exception as e:
            error_msg = f"Telnet连接失败: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
    
    def disconnect(self) -> None:
        """断开Telnet连接"""
        try:
            if self.telnet:
                self.telnet.close()
                logger.info(f"Telnet连接已断开: {self.device.name}")
        except Exception as e:
            logger.warning(f"断开Telnet连接时出错: {str(e)}")
        finally:
            # 更新连接记录
            if self.connection_record:
                self.connection_record.close_connection()
                self.connection_record = None
            self.telnet = None
    
    def execute_command(self, command: str, wait_time: float = 1.0) -> Dict[str, Any]:
        """
        执行Telnet命令
        
        Args:
            command: 要执行的命令
            wait_time: 等待时间
            
        Returns:
            执行结果字典
        """
        if not self.telnet:
            return {
                'success': False,
                'error': 'Telnet连接未建立或已断开',
                'output': None
            }
        
        try:
            start_time = time.time()
            
            # 发送命令
            command_bytes = command.encode('ascii') + b'\n'
            self.telnet.write(command_bytes)
            
            # 等待命令执行
            time.sleep(wait_time)
            
            # 读取输出
            output_bytes = self.telnet.read_very_eager()
            output = output_bytes.decode('ascii', errors='ignore')
            
            execution_time = time.time() - start_time
            
            logger.info(f"Telnet命令执行成功: {self.device.name} - {command}")
            
            return {
                'success': True,
                'output': output,
                'execution_time': execution_time,
                'command': command
            }
            
        except Exception as e:
            error_msg = f"Telnet命令执行失败: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'output': None,
                'command': command
            }
    
    def execute_commands(self, commands: List[str], wait_time: float = 1.0) -> List[Dict[str, Any]]:
        """
        批量执行Telnet命令
        
        Args:
            commands: 命令列表
            wait_time: 等待时间
            
        Returns:
            执行结果列表
        """
        results = []
        
        for command in commands:
            result = self.execute_command(command, wait_time)
            results.append(result)
            
            # 如果命令执行失败，可以选择是否继续
            if not result['success']:
                logger.warning(f"Telnet命令执行失败，停止后续命令: {command}")
                break
        
        return results
    
    def send_config_commands(self, config_commands: List[str], wait_time: float = 1.0) -> Dict[str, Any]:
        """
        发送配置命令
        
        Args:
            config_commands: 配置命令列表
            wait_time: 等待时间
            
        Returns:
            执行结果字典
        """
        if not self.telnet:
            return {
                'success': False,
                'error': 'Telnet连接未建立或已断开',
                'output': None
            }
        
        try:
            start_time = time.time()
            all_output = []
            
            for command in config_commands:
                result = self.execute_command(command, wait_time)
                if result['success']:
                    all_output.append(result['output'])
                else:
                    return {
                        'success': False,
                        'error': f"配置命令执行失败: {result['error']}",
                        'output': '\n'.join(all_output),
                        'commands': config_commands
                    }
            
            execution_time = time.time() - start_time
            
            logger.info(f"Telnet配置命令执行成功: {self.device.name} - {len(config_commands)}条命令")
            
            return {
                'success': True,
                'output': '\n'.join(all_output),
                'execution_time': execution_time,
                'commands': config_commands
            }
            
        except Exception as e:
            error_msg = f"Telnet配置命令执行失败: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'output': None,
                'commands': config_commands
            }
    
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

class TelnetConnectionManager:
    """Telnet连接管理器"""
    
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
            TelnetClient: Telnet客户端对象
        """
        client = TelnetClient(device, timeout)
        
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
                logger.warning(f"关闭Telnet连接时出错: {str(e)}")
        
        self.active_connections.clear()

# 全局连接管理器实例
telnet_manager = TelnetConnectionManager()

class TelnetService:
    """Telnet服务类"""
    
    @staticmethod
    def test_connection(device: Device, timeout: int = 30) -> Dict[str, Any]:
        """
        测试Telnet连接
        
        Args:
            device: 设备对象
            timeout: 连接超时时间
            
        Returns:
            测试结果字典
        """
        with telnet_manager.get_connection(device, timeout) as client:
            # 执行简单命令测试连接
            result = client.execute_command('show version')
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'Telnet连接测试成功',
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
        with telnet_manager.get_connection(device, timeout) as client:
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
        with telnet_manager.get_connection(device, timeout) as client:
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
        with telnet_manager.get_connection(device, timeout) as client:
            return client.send_config_commands(config_commands)
