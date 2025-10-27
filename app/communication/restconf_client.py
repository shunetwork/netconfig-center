"""
RESTCONF客户端模块
基于HTTP/HTTPS的RESTCONF API连接管理
"""

import requests
import json
import base64
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urljoin

from app.models import Device, DeviceConnection, DeviceStatus
from app import db

logger = logging.getLogger(__name__)

class RESTCONFClient:
    """RESTCONF客户端类"""
    
    def __init__(self, device: Device, timeout: int = 30):
        """
        初始化RESTCONF客户端
        
        Args:
            device: 设备对象
            timeout: 连接超时时间（秒）
        """
        self.device = device
        self.timeout = timeout
        self.session = None
        self.connection_record = None
        self.base_url = f"http{'s' if device.port == 443 else ''}://{device.ip_address}:{device.port}/restconf/"
    
    def connect(self) -> Dict[str, Any]:
        """
        建立RESTCONF连接
        
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
            
            # 创建会话
            self.session = requests.Session()
            self.session.timeout = self.timeout
            
            # 设置认证
            username = self.device.username
            password = self.device.get_password()
            if username and password:
                credentials = f"{username}:{password}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                self.session.headers.update({
                    'Authorization': f'Basic {encoded_credentials}',
                    'Accept': 'application/yang-data+json',
                    'Content-Type': 'application/yang-data+json'
                })
            
            # 测试连接
            test_url = urljoin(self.base_url, 'data/ietf-system:system-state')
            response = self.session.get(test_url)
            
            if response.status_code in [200, 404]:  # 404也可能表示连接成功但资源不存在
                result = {
                    'success': True,
                    'message': 'RESTCONF连接建立成功',
                    'connection_id': self.connection_record.id
                }
                
                # 更新设备状态
                self.device.update_status(DeviceStatus.ONLINE)
                
                logger.info(f"RESTCONF连接成功: {self.device.name} ({self.device.ip_address})")
                return result
            else:
                raise Exception(f"RESTCONF连接失败: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectTimeout:
            error_msg = f"RESTCONF连接超时"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"RESTCONF连接失败: 无法连接到服务器 - {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"RESTCONF HTTP错误: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
            
        except Exception as e:
            error_msg = f"RESTCONF连接失败: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return self._handle_connection_error(error_msg)
    
    def disconnect(self) -> None:
        """断开RESTCONF连接"""
        try:
            if self.session:
                self.session.close()
                logger.info(f"RESTCONF连接已断开: {self.device.name}")
        except Exception as e:
            logger.warning(f"断开RESTCONF连接时出错: {str(e)}")
        finally:
            # 更新连接记录
            if self.connection_record:
                self.connection_record.close_connection()
                self.connection_record = None
            self.session = None
    
    def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行GET请求
        
        Args:
            path: RESTCONF路径
            params: 查询参数
            
        Returns:
            请求结果字典
        """
        if not self.session:
            return {
                'success': False,
                'error': 'RESTCONF连接未建立或已断开',
                'data': None
            }
        
        try:
            url = urljoin(self.base_url, path)
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json() if response.content else {}
                logger.info(f"RESTCONF GET请求成功: {self.device.name} - {path}")
                
                return {
                    'success': True,
                    'data': data,
                    'status_code': response.status_code,
                    'path': path
                }
            else:
                error_msg = f"RESTCONF GET请求失败: HTTP {response.status_code}"
                logger.warning(f"{self.device.name}: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'data': None,
                    'status_code': response.status_code,
                    'path': path
                }
                
        except Exception as e:
            error_msg = f"RESTCONF GET请求异常: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'data': None,
                'path': path
            }
    
    def post(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行POST请求
        
        Args:
            path: RESTCONF路径
            data: 请求数据
            
        Returns:
            请求结果字典
        """
        if not self.session:
            return {
                'success': False,
                'error': 'RESTCONF连接未建立或已断开',
                'data': None
            }
        
        try:
            url = urljoin(self.base_url, path)
            response = self.session.post(url, json=data)
            
            if response.status_code in [200, 201, 204]:
                response_data = response.json() if response.content else {}
                logger.info(f"RESTCONF POST请求成功: {self.device.name} - {path}")
                
                return {
                    'success': True,
                    'data': response_data,
                    'status_code': response.status_code,
                    'path': path
                }
            else:
                error_msg = f"RESTCONF POST请求失败: HTTP {response.status_code}"
                logger.warning(f"{self.device.name}: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'data': None,
                    'status_code': response.status_code,
                    'path': path
                }
                
        except Exception as e:
            error_msg = f"RESTCONF POST请求异常: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'data': None,
                'path': path
            }
    
    def put(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行PUT请求
        
        Args:
            path: RESTCONF路径
            data: 请求数据
            
        Returns:
            请求结果字典
        """
        if not self.session:
            return {
                'success': False,
                'error': 'RESTCONF连接未建立或已断开',
                'data': None
            }
        
        try:
            url = urljoin(self.base_url, path)
            response = self.session.put(url, json=data)
            
            if response.status_code in [200, 201, 204]:
                response_data = response.json() if response.content else {}
                logger.info(f"RESTCONF PUT请求成功: {self.device.name} - {path}")
                
                return {
                    'success': True,
                    'data': response_data,
                    'status_code': response.status_code,
                    'path': path
                }
            else:
                error_msg = f"RESTCONF PUT请求失败: HTTP {response.status_code}"
                logger.warning(f"{self.device.name}: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'data': None,
                    'status_code': response.status_code,
                    'path': path
                }
                
        except Exception as e:
            error_msg = f"RESTCONF PUT请求异常: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'data': None,
                'path': path
            }
    
    def delete(self, path: str) -> Dict[str, Any]:
        """
        执行DELETE请求
        
        Args:
            path: RESTCONF路径
            
        Returns:
            请求结果字典
        """
        if not self.session:
            return {
                'success': False,
                'error': 'RESTCONF连接未建立或已断开',
                'data': None
            }
        
        try:
            url = urljoin(self.base_url, path)
            response = self.session.delete(url)
            
            if response.status_code in [200, 204]:
                response_data = response.json() if response.content else {}
                logger.info(f"RESTCONF DELETE请求成功: {self.device.name} - {path}")
                
                return {
                    'success': True,
                    'data': response_data,
                    'status_code': response.status_code,
                    'path': path
                }
            else:
                error_msg = f"RESTCONF DELETE请求失败: HTTP {response.status_code}"
                logger.warning(f"{self.device.name}: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'data': None,
                    'status_code': response.status_code,
                    'path': path
                }
                
        except Exception as e:
            error_msg = f"RESTCONF DELETE请求异常: {str(e)}"
            logger.error(f"{self.device.name}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'data': None,
                'path': path
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

class RESTCONFConnectionManager:
    """RESTCONF连接管理器"""
    
    def __init__(self, max_connections: int = 10):
        """
        初始化连接管理器
        
        Args:
            max_connections: 最大连接数
        """
        self.max_connections = max_connections
        self.active_connections = {}
        self._lock = None  # 可以添加线程锁
    
    def get_connection(self, device: Device, timeout: int = 30) -> RESTCONFClient:
        """
        获取设备连接
        
        Args:
            device: 设备对象
            timeout: 连接超时时间
            
        Returns:
            RESTCONFClient: RESTCONF客户端对象
        """
        client = RESTCONFClient(device, timeout)
        result = client.connect()
        
        if result['success']:
            self.active_connections[device.id] = client
            return client
        else:
            raise Exception(result['error'])
    
    def close_connection(self, device_id: int) -> None:
        """关闭指定设备的连接"""
        if device_id in self.active_connections:
            try:
                self.active_connections[device_id].disconnect()
            except Exception as e:
                logger.warning(f"关闭RESTCONF连接时出错: {str(e)}")
            finally:
                del self.active_connections[device_id]
    
    def get_active_connections_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)
    
    def close_all_connections(self) -> None:
        """关闭所有连接"""
        for client in self.active_connections.values():
            try:
                client.disconnect()
            except Exception as e:
                logger.warning(f"关闭RESTCONF连接时出错: {str(e)}")
        
        self.active_connections.clear()

# 全局连接管理器实例
restconf_manager = RESTCONFConnectionManager()

class RESTCONFService:
    """RESTCONF服务类"""
    
    @staticmethod
    def test_connection(device: Device, timeout: int = 30) -> Dict[str, Any]:
        """
        测试RESTCONF连接
        
        Args:
            device: 设备对象
            timeout: 连接超时时间
            
        Returns:
            测试结果字典
        """
        try:
            client = restconf_manager.get_connection(device, timeout)
            
            # 测试获取系统信息
            result = client.get('data/ietf-system:system-state')
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'RESTCONF连接测试成功',
                    'data': result['data']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if device.id in restconf_manager.active_connections:
                restconf_manager.close_connection(device.id)
    
    @staticmethod
    def get_system_info(device: Device, timeout: int = 30) -> Dict[str, Any]:
        """
        获取系统信息
        
        Args:
            device: 设备对象
            timeout: 连接超时时间
            
        Returns:
            系统信息字典
        """
        try:
            client = restconf_manager.get_connection(device, timeout)
            
            # 获取系统信息
            result = client.get('data/ietf-system:system-state')
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if device.id in restconf_manager.active_connections:
                restconf_manager.close_connection(device.id)
    
    @staticmethod
    def get_interfaces(device: Device, timeout: int = 30) -> Dict[str, Any]:
        """
        获取接口信息
        
        Args:
            device: 设备对象
            timeout: 连接超时时间
            
        Returns:
            接口信息字典
        """
        try:
            client = restconf_manager.get_connection(device, timeout)
            
            # 获取接口信息
            result = client.get('data/ietf-interfaces:interfaces')
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if device.id in restconf_manager.active_connections:
                restconf_manager.close_connection(device.id)
