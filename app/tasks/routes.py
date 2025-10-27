"""
任务管理模块路由
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.tasks import bp
from app.tasks.network_tasks import execute_device_command, execute_device_commands, test_device_connection, batch_test_connections
from app.tasks.template_tasks import render_and_apply_template, batch_render_and_apply_template, render_template_only
from app.tasks.backup_tasks import backup_device_config, batch_backup_configs, restore_device_config
from app.models import Task, TaskResult, TaskStatus, TaskType, Device, ConfigTemplate, ConfigBackup, AuditLog
from app import db

@bp.route('/')
@login_required
def index():
    """任务列表页面"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    task_type = request.args.get('task_type')
    
    query = Task.query
    
    if status:
        query = query.filter_by(status=status)
    if task_type:
        query = query.filter_by(task_type=task_type)
    
    tasks = query.order_by(Task.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('tasks/index.html', tasks=tasks, current_status=status, current_task_type=task_type)

@bp.route('/<int:task_id>')
@login_required
def detail(task_id):
    """任务详情页面"""
    task = Task.query.get_or_404(task_id)
    return render_template('tasks/detail.html', task=task)

@bp.route('/api/tasks')
@login_required
def api_tasks():
    """API: 获取任务列表"""
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([task.to_dict() for task in tasks])

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建任务"""
    if request.method == 'POST':
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '缺少任务数据'}), 400
        
        try:
            # 创建任务记录
            task = Task(
                name=data.get('name', '未命名任务'),
                description=data.get('description', ''),
                task_type=TaskType(data.get('task_type', 'command')),
                command=data.get('command'),
                user=current_user
            )
            
            # 设置设备
            if data.get('device_id'):
                device = Device.query.get(data['device_id'])
                if device:
                    task.device = device
            
            # 设置模板
            if data.get('template_id'):
                template = ConfigTemplate.query.get(data['template_id'])
                if template:
                    task.template = template
            
            # 设置模板变量
            if data.get('template_variables'):
                task.set_template_variables(data['template_variables'])
            
            db.session.add(task)
            db.session.commit()
            
            # 根据任务类型启动相应的异步任务
            task_type = data.get('task_type', 'command')
            
            if task_type == 'command' and task.device and task.command:
                # 单命令执行
                async_task = execute_device_command.delay(
                    task.id, task.device.id, task.command, data.get('timeout', 30)
                )
            elif task_type == 'batch_command' and task.device and data.get('commands'):
                # 批量命令执行
                async_task = execute_device_commands.delay(
                    task.id, task.device.id, data['commands'], data.get('timeout', 30)
                )
            elif task_type == 'config_template' and task.template and task.device:
                # 模板应用
                async_task = render_and_apply_template.delay(
                    task.id, task.template.id, task.device.id, 
                    data.get('template_variables', {}), data.get('timeout', 30)
                )
            elif task_type == 'backup_config' and task.device:
                # 配置备份
                async_task = backup_device_config.delay(
                    task.id, task.device.id, data.get('backup_name'), data.get('timeout', 30)
                )
            elif task_type == 'restore_config' and task.device and data.get('backup_id'):
                # 配置恢复
                async_task = restore_device_config.delay(
                    task.id, task.device.id, data['backup_id'], data.get('timeout', 30)
                )
            else:
                return jsonify({'success': False, 'error': '无效的任务参数'}), 400
            
            # 记录任务创建日志
            AuditLog.log_action(
                user=current_user,
                action='create_task',
                resource_type='task',
                resource_id=task.id,
                resource_name=task.name,
                success=True,
                details={
                    'task_type': task.task_type.value,
                    'device_name': task.device.name if task.device else None,
                    'template_name': task.template.name if task.template else None
                }
            )
            
            return jsonify({
                'success': True,
                'task_id': task.id,
                'message': '任务创建成功'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET请求：显示任务创建表单
    devices = Device.query.filter_by(is_active=True).order_by(Device.name).all()
    templates = ConfigTemplate.query.filter_by(is_active=True).order_by(ConfigTemplate.name).all()
    
    return render_template('tasks/create.html', devices=devices, templates=templates)

@bp.route('/<int:task_id>/cancel', methods=['POST'])
@login_required
def cancel_task(task_id):
    """取消任务"""
    task = Task.query.get_or_404(task_id)
    
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        return jsonify({'success': False, 'error': '任务已完成，无法取消'}), 400
    
    try:
        # 取消Celery任务（如果正在运行）
        if hasattr(task, 'celery_task_id') and task.celery_task_id:
            from app.tasks.celery_app import celery
            celery.control.revoke(task.celery_task_id, terminate=True)
        
        # 更新任务状态
        task.cancel('用户手动取消')
        
        # 记录取消日志
        AuditLog.log_action(
            user=current_user,
            action='cancel_task',
            resource_type='task',
            resource_id=task.id,
            resource_name=task.name,
            success=True
        )
        
        return jsonify({'success': True, 'message': '任务已取消'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:task_id>/retry', methods=['POST'])
@login_required
def retry_task(task_id):
    """重试任务"""
    task = Task.query.get_or_404(task_id)
    
    if not task.retry():
        return jsonify({'success': False, 'error': '任务已达到最大重试次数'}), 400
    
    try:
        # 重新启动异步任务
        if task.task_type == TaskType.COMMAND and task.device and task.command:
            execute_device_command.delay(task.id, task.device.id, task.command, 30)
        elif task.task_type == TaskType.CONFIG_TEMPLATE and task.template and task.device:
            variables = task.get_template_variables()
            render_and_apply_template.delay(task.id, task.template.id, task.device.id, variables, 30)
        # 可以添加其他任务类型的重试逻辑
        
        # 记录重试日志
        AuditLog.log_action(
            user=current_user,
            action='retry_task',
            resource_type='task',
            resource_id=task.id,
            resource_name=task.name,
            success=True
        )
        
        return jsonify({'success': True, 'message': '任务已重新启动'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:task_id>/results')
@login_required
def task_results(task_id):
    """任务结果页面"""
    task = Task.query.get_or_404(task_id)
    results = task.results.order_by(TaskResult.created_at.desc()).all()
    
    return render_template('tasks/results.html', task=task, results=results)

@bp.route('/api/task/<int:task_id>/status')
@login_required
def api_task_status(task_id):
    """API: 获取任务状态"""
    task = Task.query.get_or_404(task_id)
    
    # 如果任务正在运行，尝试获取Celery任务状态
    celery_status = None
    if task.status == TaskStatus.RUNNING and hasattr(task, 'celery_task_id') and task.celery_task_id:
        try:
            from app.tasks.celery_app import celery
            celery_result = celery.AsyncResult(task.celery_task_id)
            celery_status = {
                'state': celery_result.state,
                'progress': getattr(celery_result.info, 'progress', 0) if celery_result.info else 0,
                'status': getattr(celery_result.info, 'status', '') if celery_result.info else ''
            }
        except:
            pass
    
    return jsonify({
        'task_id': task.id,
        'status': task.status.value,
        'celery_status': celery_status,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'duration': task.duration,
        'retry_count': task.retry_count,
        'max_retries': task.max_retries
    })

@bp.route('/api/tasks/stats')
@login_required
def api_tasks_stats():
    """API: 获取任务统计信息"""
    stats = {
        'total': Task.query.count(),
        'pending': Task.query.filter_by(status=TaskStatus.PENDING).count(),
        'running': Task.query.filter_by(status=TaskStatus.RUNNING).count(),
        'success': Task.query.filter_by(status=TaskStatus.SUCCESS).count(),
        'failed': Task.query.filter_by(status=TaskStatus.FAILED).count(),
        'cancelled': Task.query.filter_by(status=TaskStatus.CANCELLED).count()
    }
    
    return jsonify(stats)

@bp.route('/api/task/<int:task_id>')
@login_required
def api_task_detail(task_id):
    """API: 获取任务详情"""
    task = Task.query.get_or_404(task_id)
    return jsonify(task.to_dict(include_details=True))
