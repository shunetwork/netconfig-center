"""
模板任务模块
包含配置模板渲染、应用等异步任务
"""

import traceback
from datetime import datetime
from app.tasks.celery_app import celery
from app.models import Device, Task, TaskResult, TaskStatus, TaskType, ConfigTemplate, AuditLog
from app.communication.ssh_client import SSHService
from app.communication.telnet_client import TelnetService
from app.templates.services import TemplateService
from app import db

@celery.task(bind=True)
def render_and_apply_template(self, task_id, template_id, device_id, variables, timeout=30):
    """
    渲染并应用配置模板任务
    
    Args:
        task_id: 任务ID
        template_id: 模板ID
        device_id: 设备ID
        variables: 模板变量
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
        
        # 获取模板和设备
        template = ConfigTemplate.query.get(template_id)
        device = Device.query.get(device_id)
        
        if not template:
            task.complete(False, error='模板不存在')
            db.session.commit()
            return {'success': False, 'error': '模板不存在'}
        
        if not device:
            task.complete(False, error='设备不存在')
            db.session.commit()
            return {'success': False, 'error': '设备不存在'}
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': '渲染模板中...'})
        
        # 渲染模板
        render_result = TemplateService.render_template(template, variables)
        
        if not render_result['success']:
            task.complete(False, error=f'模板渲染失败: {render_result["error"]}')
            db.session.commit()
            return {'success': False, 'error': f'模板渲染失败: {render_result["error"]}'}
        
        rendered_config = render_result['rendered_content']
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 40, 'status': '应用配置中...'})
        
        # 将配置按行分割为命令
        config_commands = [line.strip() for line in rendered_config.split('\n') if line.strip()]
        
        # 根据连接类型应用配置
        if device.connection_type.value == 'ssh':
            result = SSHService.send_config(device, config_commands, timeout)
        elif device.connection_type.value == 'telnet':
            result = TelnetService.send_config(device, config_commands, timeout)
        else:
            result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 90, 'status': '处理结果中...'})
        
        # 创建任务结果记录
        task_result = TaskResult(
            device_name=device.name,
            device_ip=device.ip_address,
            command=f"应用模板: {template.name}",
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
            action='apply_config_template_task',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            task=task,
            details={
                'template_name': template.name,
                'template_id': template.id,
                'variables': variables,
                'rendered_config': rendered_config[:500],  # 只记录前500字符
                'connection_type': device.connection_type.value,
                'execution_time': result.get('execution_time')
            }
        )
        
        return {
            'success': result['success'],
            'output': result.get('output'),
            'error': result.get('error'),
            'rendered_config': rendered_config,
            'execution_time': result.get('execution_time')
        }
        
    except Exception as e:
        error_msg = f'模板应用异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}

@celery.task(bind=True)
def batch_render_and_apply_template(self, task_id, template_id, device_ids, variables, timeout=30):
    """
    批量渲染并应用配置模板任务
    
    Args:
        task_id: 任务ID
        template_id: 模板ID
        device_ids: 设备ID列表
        variables: 模板变量
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
        
        # 获取模板
        template = ConfigTemplate.query.get(template_id)
        if not template:
            task.complete(False, error='模板不存在')
            db.session.commit()
            return {'success': False, 'error': '模板不存在'}
        
        devices = Device.query.filter(Device.id.in_(device_ids)).all()
        results = {}
        total_devices = len(devices)
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': '渲染模板中...'})
        
        # 渲染模板
        render_result = TemplateService.render_template(template, variables)
        
        if not render_result['success']:
            task.complete(False, error=f'模板渲染失败: {render_result["error"]}')
            db.session.commit()
            return {'success': False, 'error': f'模板渲染失败: {render_result["error"]}'}
        
        rendered_config = render_result['rendered_content']
        config_commands = [line.strip() for line in rendered_config.split('\n') if line.strip()]
        
        for i, device in enumerate(devices):
            # 更新任务进度
            progress = int((i / total_devices) * 70) + 20
            self.update_state(state='PROGRESS', meta={
                'progress': progress, 
                'status': f'应用配置到设备 {i+1}/{total_devices}: {device.name}'
            })
            
            try:
                # 应用配置
                if device.connection_type.value == 'ssh':
                    result = SSHService.send_config(device, config_commands, timeout)
                elif device.connection_type.value == 'telnet':
                    result = TelnetService.send_config(device, config_commands, timeout)
                else:
                    result = {'success': False, 'error': f'不支持的连接类型: {device.connection_type.value}'}
                
                # 创建任务结果记录
                task_result = TaskResult(
                    device_name=device.name,
                    device_ip=device.ip_address,
                    command=f"批量应用模板: {template.name}",
                    output=result.get('output'),
                    error=result.get('error'),
                    exit_code=0 if result['success'] else 1,
                    execution_time=result.get('execution_time'),
                    task=task,
                    device=device
                )
                db.session.add(task_result)
                
                results[device.id] = {
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'connection_type': device.connection_type.value,
                    'result': result
                }
                
            except Exception as e:
                error_msg = f'设备 {device.name} 配置应用失败: {str(e)}'
                
                # 创建失败的任务结果记录
                task_result = TaskResult(
                    device_name=device.name,
                    device_ip=device.ip_address,
                    command=f"批量应用模板: {template.name}",
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
                    'connection_type': device.connection_type.value,
                    'result': {
                        'success': False,
                        'error': error_msg
                    }
                }
        
        # 计算总体结果
        success_count = sum(1 for r in results.values() if r['result']['success'])
        overall_success = success_count > 0
        
        # 完成任务
        task.complete(overall_success, f'成功应用模板到 {success_count}/{total_devices} 个设备')
        db.session.commit()
        
        # 记录审计日志
        AuditLog.log_action(
            user_id=task.user_id,
            action='batch_apply_config_template_task',
            resource_type='device',
            success=overall_success,
            task=task,
            details={
                'template_name': template.name,
                'template_id': template.id,
                'variables': variables,
                'device_count': total_devices,
                'success_count': success_count,
                'results': results
            }
        )
        
        return {
            'success': overall_success,
            'results': results,
            'total_devices': total_devices,
            'success_count': success_count,
            'rendered_config': rendered_config
        }
        
    except Exception as e:
        error_msg = f'批量模板应用异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}

@celery.task(bind=True)
def render_template_only(self, task_id, template_id, variables):
    """
    仅渲染模板任务（不应用配置）
    
    Args:
        task_id: 任务ID
        template_id: 模板ID
        variables: 模板变量
        
    Returns:
        渲染结果字典
    """
    try:
        # 更新任务状态
        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        
        task.start()
        db.session.commit()
        
        # 获取模板
        template = ConfigTemplate.query.get(template_id)
        if not template:
            task.complete(False, error='模板不存在')
            db.session.commit()
            return {'success': False, 'error': '模板不存在'}
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': '渲染模板中...'})
        
        # 渲染模板
        result = TemplateService.render_template(template, variables)
        
        # 完成任务
        task.complete(result['success'], result.get('rendered_content', ''), result.get('error', ''))
        db.session.commit()
        
        # 记录审计日志
        AuditLog.log_action(
            user_id=task.user_id,
            action='render_template_only_task',
            resource_type='config_template',
            resource_id=template.id,
            resource_name=template.name,
            success=result['success'],
            error_message=result.get('error'),
            task=task,
            details={
                'variables': variables,
                'template_name': template.name
            }
        )
        
        return result
        
    except Exception as e:
        error_msg = f'模板渲染异常: {str(e)}'
        traceback.print_exc()
        
        # 更新任务状态
        if 'task' in locals():
            task.complete(False, error=error_msg)
            db.session.commit()
        
        return {'success': False, 'error': error_msg}
