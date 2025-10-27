"""
备份任务模块
包含配置备份、恢复等异步任务
"""

import traceback
from datetime import datetime
from app.tasks.celery_app import celery
from app.models import Device, Task, TaskResult, TaskStatus, TaskType, ConfigBackup, AuditLog
from app.communication.ssh_client import SSHService
from app.communication.telnet_client import TelnetService
from app import db

@celery.task(bind=True)
def backup_device_config(self, task_id, device_id, backup_name=None, timeout=30):
    """
    备份设备配置任务
    
    Args:
        task_id: 任务ID
        device_id: 设备ID
        backup_name: 备份名称
        timeout: 超时时间
        
    Returns:
        备份结果字典
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
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': '连接设备中...'})
        
        # 根据连接类型获取配置
        if device.connection_type.value == 'ssh':
            result = SSHService.execute_command(device, 'show running-config', timeout)
        elif device.connection_type.value == 'telnet':
            result = TelnetService.execute_command(device, 'show running-config', timeout)
        else:
            result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
        
        if not result['success']:
            task.complete(False, error=f'获取配置失败: {result.get("error")}')
            db.session.commit()
            return {'success': False, 'error': f'获取配置失败: {result.get("error")}'}
        
        config_content = result['output']
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 60, 'status': '创建备份记录中...'})
        
        # 创建备份记录
        if not backup_name:
            backup_name = f'{device.name}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        backup = ConfigBackup(
            name=backup_name,
            description=f'设备 {device.name} 的配置备份',
            backup_type='manual',
            config_content=config_content,
            config_size=len(config_content),
            device=device,
            user_id=task.user_id
        )
        backup.calculate_hash()
        backup.mark_as_current()
        
        db.session.add(backup)
        
        # 更新设备最后备份时间
        device.last_config_backup = datetime.utcnow()
        db.session.add(device)
        
        # 创建任务结果记录
        task_result = TaskResult(
            device_name=device.name,
            device_ip=device.ip_address,
            command='show running-config',
            output=config_content[:500] + '...' if len(config_content) > 500 else config_content,
            error=None,
            exit_code=0,
            execution_time=result.get('execution_time'),
            task=task,
            device=device
        )
        db.session.add(task_result)
        
        # 完成任务
        task.complete(True, f'配置备份成功，备份ID: {backup.id}')
        db.session.commit()
        
        # 记录审计日志
        AuditLog.log_action(
            user_id=task.user_id,
            action='backup_device_config_task',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=True,
            task=task,
            details={
                'backup_id': backup.id,
                'backup_name': backup.name,
                'config_size': backup.config_size,
                'connection_type': device.connection_type.value,
                'execution_time': result.get('execution_time')
            }
        )
        
        return {
            'success': True,
            'backup_id': backup.id,
            'backup_name': backup.name,
            'config_size': backup.config_size,
            'config_content': config_content[:500] + '...' if len(config_content) > 500 else config_content,
            'execution_time': result.get('execution_time')
        }
        
    except Exception as e:
        error_msg = f'配置备份异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}

@celery.task(bind=True)
def batch_backup_configs(self, task_id, device_ids, backup_prefix=None, timeout=30):
    """
    批量备份设备配置任务
    
    Args:
        task_id: 任务ID
        device_ids: 设备ID列表
        backup_prefix: 备份名称前缀
        timeout: 超时时间
        
    Returns:
        备份结果字典
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
                'status': f'备份设备 {i+1}/{total_devices}: {device.name}'
            })
            
            try:
                # 获取配置
                if device.connection_type.value == 'ssh':
                    result = SSHService.execute_command(device, 'show running-config', timeout)
                elif device.connection_type.value == 'telnet':
                    result = TelnetService.execute_command(device, 'show running-config', timeout)
                else:
                    result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
                
                if result['success']:
                    config_content = result['output']
                    
                    # 创建备份记录
                    backup_name = f'{backup_prefix}_{device.name}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}' if backup_prefix else f'{device.name}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                    
                    backup = ConfigBackup(
                        name=backup_name,
                        description=f'批量备份 - 设备 {device.name} 的配置',
                        backup_type='manual',
                        config_content=config_content,
                        config_size=len(config_content),
                        device=device,
                        user_id=task.user_id
                    )
                    backup.calculate_hash()
                    backup.mark_as_current()
                    
                    db.session.add(backup)
                    
                    # 更新设备最后备份时间
                    device.last_config_backup = datetime.utcnow()
                    db.session.add(device)
                    
                    results[device.id] = {
                        'device_name': device.name,
                        'device_ip': device.ip_address,
                        'result': {
                            'success': True,
                            'backup_id': backup.id,
                            'backup_name': backup.name,
                            'config_size': backup.config_size
                        }
                    }
                else:
                    results[device.id] = {
                        'device_name': device.name,
                        'device_ip': device.ip_address,
                        'result': {
                            'success': False,
                            'error': result.get('error')
                        }
                    }
                
                # 创建任务结果记录
                task_result = TaskResult(
                    device_name=device.name,
                    device_ip=device.ip_address,
                    command='show running-config',
                    output=result.get('output', '')[:500] + '...' if result.get('output') and len(result.get('output')) > 500 else result.get('output'),
                    error=result.get('error'),
                    exit_code=0 if result['success'] else 1,
                    execution_time=result.get('execution_time'),
                    task=task,
                    device=device
                )
                db.session.add(task_result)
                
            except Exception as e:
                error_msg = f'设备 {device.name} 备份失败: {str(e)}'
                
                # 创建失败的任务结果记录
                task_result = TaskResult(
                    device_name=device.name,
                    device_ip=device.ip_address,
                    command='show running-config',
                    output=None,
                    error=error_msg,
                    exit_code=1,
                    execution_time=0,
                    task=task,
                    device=device
                )
                db.session.add(task_result)
                
                results[device.id] = {
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'result': {
                        'success': False,
                        'error': error_msg
                    }
                }
        
        # 计算总体结果
        success_count = sum(1 for r in results.values() if r['result']['success'])
        overall_success = success_count > 0
        
        # 完成任务
        task.complete(overall_success, f'成功备份 {success_count}/{total_devices} 个设备的配置')
        db.session.commit()
        
        # 记录审计日志
        AuditLog.log_action(
            user_id=task.user_id,
            action='batch_backup_configs_task',
            resource_type='device',
            success=overall_success,
            task=task,
            details={
                'device_count': total_devices,
                'success_count': success_count,
                'backup_prefix': backup_prefix,
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
        error_msg = f'批量配置备份异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}

@celery.task(bind=True)
def restore_device_config(self, task_id, device_id, backup_id, timeout=30):
    """
    恢复设备配置任务
    
    Args:
        task_id: 任务ID
        device_id: 设备ID
        backup_id: 备份ID
        timeout: 超时时间
        
    Returns:
        恢复结果字典
    """
    try:
        # 更新任务状态
        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        
        task.start()
        db.session.commit()
        
        # 获取设备和备份
        device = Device.query.get(device_id)
        backup = ConfigBackup.query.get(backup_id)
        
        if not device:
            task.complete(False, error='设备不存在')
            db.session.commit()
            return {'success': False, 'error': '设备不存在'}
        
        if not backup:
            task.complete(False, error='备份不存在')
            db.session.commit()
            return {'success': False, 'error': '备份不存在'}
        
        if backup.device_id != device_id:
            task.complete(False, error='备份与设备不匹配')
            db.session.commit()
            return {'success': False, 'error': '备份与设备不匹配'}
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': '准备恢复配置中...'})
        
        # 将配置按行分割为命令
        config_lines = [line.strip() for line in backup.config_content.split('\n') if line.strip()]
        
        # 过滤掉不需要的命令（如注释、版本信息等）
        config_commands = []
        skip_patterns = ['!', 'version', 'boot-start-marker', 'boot-end-marker']
        
        for line in config_lines:
            if not any(line.startswith(pattern) for pattern in skip_patterns):
                config_commands.append(line)
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': '应用配置中...'})
        
        # 根据连接类型应用配置
        if device.connection_type.value == 'ssh':
            result = SSHService.send_config(device, config_commands, timeout)
        elif device.connection_type.value == 'telnet':
            result = TelnetService.send_config(device, config_commands, timeout)
        else:
            result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 80, 'status': '更新备份状态中...'})
        
        # 标记备份为已恢复
        backup.restore(task.user)
        
        # 创建任务结果记录
        task_result = TaskResult(
            device_name=device.name,
            device_ip=device.ip_address,
            command=f'恢复配置备份: {backup.name}',
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
            action='restore_device_config_task',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            task=task,
            details={
                'backup_id': backup.id,
                'backup_name': backup.name,
                'connection_type': device.connection_type.value,
                'execution_time': result.get('execution_time')
            }
        )
        
        return {
            'success': result['success'],
            'output': result.get('output'),
            'error': result.get('error'),
            'backup_name': backup.name,
            'execution_time': result.get('execution_time')
        }
        
    except Exception as e:
        error_msg = f'配置恢复异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}
