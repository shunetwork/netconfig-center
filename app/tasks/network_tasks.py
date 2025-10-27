"""
网络任务模块
包含设备连接、命令执行等异步任务
"""

import time
import traceback
from datetime import datetime
from celery import current_task
from app.tasks.celery_app import celery
from app.models import Device, Task, TaskResult, TaskStatus, TaskType, AuditLog
from app.communication.ssh_client import SSHService
from app.communication.telnet_client import TelnetService
from app.communication.restconf_client import RESTCONFService
from app import db

@celery.task(bind=True)
def execute_device_command(self, task_id, device_id, command, timeout=30):
    """
    执行设备命令任务
    
    Args:
        task_id: 任务ID
        device_id: 设备ID
        command: 要执行的命令
        timeout: 超时时间
        
    Returns:
        执行结果字典
    """
    try:
        # 更新任务状态
        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        
        task.start()
        db.session.commit()
        
        # 获取设备
        device = Device.query.get(device_id)
        if not device:
            task.complete(False, error='设备不存在')
            db.session.commit()
            return {'success': False, 'error': '设备不存在'}
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': '连接设备中...'})
        
        # 根据连接类型选择相应的服务
        if device.connection_type.value == 'ssh':
            result = SSHService.execute_command(device, command, timeout)
        elif device.connection_type.value == 'telnet':
            result = TelnetService.execute_command(device, command, timeout)
        elif device.connection_type.value == 'restconf':
            # RESTCONF需要根据命令类型处理
            if command.startswith('GET '):
                result = RESTCONFService.get_system_info(device, timeout)
            else:
                result = {'success': False, 'error': f'RESTCONF不支持命令: {command}'}
        else:
            result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 90, 'status': '处理结果中...'})
        
        # 创建任务结果记录
        task_result = TaskResult(
            device_name=device.name,
            device_ip=device.ip_address,
            command=command,
            output=result.get('output'),
            error=result.get('error'),
            exit_code=0 if result['success'] else 1,
            execution_time=result.get('execution_time'),
            task=task,
            device=device
        )
        db.session.add(task_result)
        
        # 完成任务
        task.complete(result['success'], result.get('output', ''), result.get('error', ''))
        db.session.commit()
        
        # 记录审计日志
        AuditLog.log_action(
            user_id=task.user_id,
            action='execute_device_command_task',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            task=task,
            details={
                'command': command,
                'connection_type': device.connection_type.value,
                'execution_time': result.get('execution_time')
            }
        )
        
        return {
            'success': result['success'],
            'output': result.get('output'),
            'error': result.get('error'),
            'execution_time': result.get('execution_time')
        }
        
    except Exception as e:
        error_msg = f'任务执行异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}

@celery.task(bind=True)
def execute_device_commands(self, task_id, device_id, commands, timeout=30):
    """
    批量执行设备命令任务
    
    Args:
        task_id: 任务ID
        device_id: 设备ID
        commands: 命令列表
        timeout: 超时时间
        
    Returns:
        执行结果字典
    """
    try:
        # 更新任务状态
        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        
        task.start()
        db.session.commit()
        
        # 获取设备
        device = Device.query.get(device_id)
        if not device:
            task.complete(False, error='设备不存在')
            db.session.commit()
            return {'success': False, 'error': '设备不存在'}
        
        results = []
        total_commands = len(commands)
        
        for i, command in enumerate(commands):
            # 更新任务进度
            progress = int((i / total_commands) * 80) + 10
            self.update_state(state='PROGRESS', meta={
                'progress': progress, 
                'status': f'执行命令 {i+1}/{total_commands}: {command[:50]}...'
            })
            
            # 执行命令
            if device.connection_type.value == 'ssh':
                result = SSHService.execute_command(device, command, timeout)
            elif device.connection_type.value == 'telnet':
                result = TelnetService.execute_command(device, command, timeout)
            else:
                result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
            
            results.append(result)
            
            # 创建任务结果记录
            task_result = TaskResult(
                device_name=device.name,
                device_ip=device.ip_address,
                command=command,
                output=result.get('output'),
                error=result.get('error'),
                exit_code=0 if result['success'] else 1,
                execution_time=result.get('execution_time'),
                task=task,
                device=device
            )
            db.session.add(task_result)
            
            # 如果命令执行失败，可以选择是否继续
            if not result['success']:
                break
        
        # 计算总体结果
        success_count = sum(1 for r in results if r['success'])
        overall_success = success_count > 0
        
        # 完成任务
        task.complete(overall_success, f'成功执行 {success_count}/{total_commands} 条命令')
        db.session.commit()
        
        # 记录审计日志
        AuditLog.log_action(
            user_id=task.user_id,
            action='execute_device_commands_task',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=overall_success,
            task=task,
            details={
                'commands': commands,
                'total_commands': total_commands,
                'success_count': success_count,
                'connection_type': device.connection_type.value
            }
        )
        
        return {
            'success': overall_success,
            'results': results,
            'total_commands': total_commands,
            'success_count': success_count
        }
        
    except Exception as e:
        error_msg = f'批量命令执行异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}

@celery.task(bind=True)
def test_device_connection(self, task_id, device_id, timeout=30):
    """
    测试设备连接任务
    
    Args:
        task_id: 任务ID
        device_id: 设备ID
        timeout: 超时时间
        
    Returns:
        测试结果字典
    """
    try:
        # 更新任务状态
        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        
        task.start()
        db.session.commit()
        
        # 获取设备
        device = Device.query.get(device_id)
        if not device:
            task.complete(False, error='设备不存在')
            db.session.commit()
            return {'success': False, 'error': '设备不存在'}
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': '测试连接中...'})
        
        # 根据连接类型选择相应的服务
        if device.connection_type.value == 'ssh':
            result = SSHService.test_connection(device, timeout)
        elif device.connection_type.value == 'telnet':
            result = TelnetService.test_connection(device, timeout)
        elif device.connection_type.value == 'restconf':
            result = RESTCONFService.test_connection(device, timeout)
        else:
            result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
        
        # 完成任务
        task.complete(result['success'], result.get('message', ''), result.get('error', ''))
        db.session.commit()
        
        # 记录审计日志
        AuditLog.log_action(
            user_id=task.user_id,
            action='test_device_connection_task',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            task=task,
            details={
                'connection_type': device.connection_type.value
            }
        )
        
        return result
        
    except Exception as e:
        error_msg = f'连接测试异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}

@celery.task(bind=True)
def batch_test_connections(self, task_id, device_ids, timeout=30):
    """
    批量测试设备连接任务
    
    Args:
        task_id: 任务ID
        device_ids: 设备ID列表
        timeout: 超时时间
        
    Returns:
        测试结果字典
    """
    try:
        # 更新任务状态
        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        
        task.start()
        db.session.commit()
        
        devices = Device.query.filter(Device.id.in_(device_ids)).all()
        results = {}
        total_devices = len(devices)
        
        for i, device in enumerate(devices):
            # 更新任务进度
            progress = int((i / total_devices) * 80) + 10
            self.update_state(state='PROGRESS', meta={
                'progress': progress, 
                'status': f'测试设备 {i+1}/{total_devices}: {device.name}'
            })
            
            try:
                # 测试连接
                if device.connection_type.value == 'ssh':
                    result = SSHService.test_connection(device, timeout)
                elif device.connection_type.value == 'telnet':
                    result = TelnetService.test_connection(device, timeout)
                elif device.connection_type.value == 'restconf':
                    result = RESTCONFService.test_connection(device, timeout)
                else:
                    result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
                
                results[device.id] = {
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'connection_type': device.connection_type.value,
                    'result': result
                }
                
            except Exception as e:
                results[device.id] = {
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'connection_type': device.connection_type.value,
                    'result': {
                        'success': False,
                        'error': str(e)
                    }
                }
        
        # 计算总体结果
        success_count = sum(1 for r in results.values() if r['result']['success'])
        overall_success = success_count > 0
        
        # 完成任务
        task.complete(overall_success, f'成功测试 {success_count}/{total_devices} 个设备')
        db.session.commit()
        
        # 记录审计日志
        AuditLog.log_action(
            user_id=task.user_id,
            action='batch_test_connections_task',
            resource_type='device',
            success=overall_success,
            task=task,
            details={
                'device_count': total_devices,
                'success_count': success_count,
                'results': results
            }
        )
        
        return {
            'success': overall_success,
            'results': results,
            'total_devices': total_devices,
            'success_count': success_count
        }
        
    except Exception as e:
        error_msg = f'批量连接测试异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}
