"""
任务相关数据模型
包含任务、任务结果、审计日志等
"""

from datetime import datetime
from enum import Enum
from app import db

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = 'pending'      # 等待执行
    RUNNING = 'running'      # 执行中
    SUCCESS = 'success'      # 执行成功
    FAILED = 'failed'        # 执行失败
    CANCELLED = 'cancelled'  # 已取消
    TIMEOUT = 'timeout'      # 执行超时

class TaskType(Enum):
    """任务类型枚举"""
    COMMAND = 'command'           # 单命令执行
    BATCH_COMMAND = 'batch_command'  # 批量命令执行
    CONFIG_TEMPLATE = 'config_template'  # 配置模板执行
    BACKUP_CONFIG = 'backup_config'      # 配置备份
    RESTORE_CONFIG = 'restore_config'    # 配置恢复
    DEVICE_DISCOVERY = 'device_discovery'  # 设备发现

class Task(db.Model):
    """任务模型"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    task_type = db.Column(db.Enum(TaskType), nullable=False, index=True)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    priority = db.Column(db.Integer, default=0)  # 优先级，数字越大优先级越高
    
    # 任务配置
    command = db.Column(db.Text)  # 要执行的命令
    template_variables = db.Column(db.Text)  # JSON格式的模板变量
    
    # 执行时间
    scheduled_at = db.Column(db.DateTime)  # 计划执行时间
    started_at = db.Column(db.DateTime)   # 开始执行时间
    completed_at = db.Column(db.DateTime) # 完成时间
    duration = db.Column(db.Integer)      # 执行持续时间（秒）
    
    # 结果信息
    result_message = db.Column(db.Text)   # 执行结果消息
    error_message = db.Column(db.Text)    # 错误信息
    retry_count = db.Column(db.Integer, default=0)  # 重试次数
    max_retries = db.Column(db.Integer, default=3)  # 最大重试次数
    
    # 元数据
    task_metadata = db.Column(db.Text)  # JSON格式的额外元数据
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    template_id = db.Column(db.Integer, db.ForeignKey('config_templates.id'))
    
    # 关系
    results = db.relationship('TaskResult', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='task', lazy='dynamic')
    
    def start(self):
        """开始执行任务"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
    
    def complete(self, success=True, message='', error=''):
        """完成任务"""
        self.status = TaskStatus.SUCCESS if success else TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.result_message = message
        self.error_message = error
        
        if self.started_at:
            self.duration = int((self.completed_at - self.started_at).total_seconds())
        
        db.session.add(self)
        db.session.commit()
    
    def cancel(self, reason=''):
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.result_message = f"任务已取消: {reason}"
        
        if self.started_at:
            self.duration = int((self.completed_at - self.started_at).total_seconds())
        
        db.session.add(self)
        db.session.commit()
    
    def retry(self):
        """重试任务"""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.status = TaskStatus.PENDING
            self.started_at = None
            self.completed_at = None
            self.duration = None
            self.error_message = None
            db.session.add(self)
            db.session.commit()
            return True
        return False
    
    def get_metadata(self):
        """获取元数据"""
        if not self.task_metadata:
            return {}
        try:
            import json
            return json.loads(self.task_metadata)
        except:
            return {}
    
    def set_metadata(self, data):
        """设置元数据"""
        import json
        self.task_metadata = json.dumps(data) if data else None
    
    def get_template_variables(self):
        """获取模板变量"""
        if not self.template_variables:
            return {}
        try:
            import json
            return json.loads(self.template_variables)
        except:
            return {}
    
    def set_template_variables(self, variables):
        """设置模板变量"""
        import json
        self.template_variables = json.dumps(variables) if variables else None
    
    def to_dict(self, include_details=False):
        """转换为字典格式"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'task_type': self.task_type.value if self.task_type else None,
            'status': self.status.value if self.status else None,
            'priority': self.priority,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'user_name': self.user.username if self.user else None,
            'device_name': self.device.name if self.device else None,
            'template_name': self.template.name if self.template else None,
            'created_at': self.created_at.isoformat()
        }
        
        if include_details:
            data.update({
                'command': self.command,
                'result_message': self.result_message,
                'error_message': self.error_message,
                'template_variables': self.get_template_variables(),
                'metadata': self.get_metadata(),
                'results_count': self.results.count()
            })
        
        return data
    
    def __repr__(self):
        return f'<Task {self.name} ({self.status.value})>'

class TaskResult(db.Model):
    """任务结果模型"""
    __tablename__ = 'task_results'
    
    id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(100), nullable=False, index=True)
    device_ip = db.Column(db.String(45), nullable=False)
    command = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text)  # 命令输出
    error = db.Column(db.Text)   # 错误输出
    exit_code = db.Column(db.Integer, default=0)  # 退出代码
    execution_time = db.Column(db.Float)  # 执行时间（秒）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 外键
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    
    def is_success(self):
        """判断是否执行成功"""
        return self.exit_code == 0 and not self.error
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'device_name': self.device_name,
            'device_ip': self.device_ip,
            'command': self.command,
            'output': self.output,
            'error': self.error,
            'exit_code': self.exit_code,
            'execution_time': self.execution_time,
            'success': self.is_success(),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<TaskResult {self.device_name} ({self.exit_code})>'

class AuditLog(db.Model):
    """审计日志模型"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False, index=True)  # 操作类型
    resource_type = db.Column(db.String(50), nullable=False, index=True)  # 资源类型
    resource_id = db.Column(db.Integer, index=True)  # 资源ID
    resource_name = db.Column(db.String(200), index=True)  # 资源名称
    
    # 操作详情
    details = db.Column(db.Text)  # 操作详情（JSON格式）
    ip_address = db.Column(db.String(45))  # 用户IP地址
    user_agent = db.Column(db.Text)  # 用户代理
    
    # 结果信息
    success = db.Column(db.Boolean, default=True)  # 操作是否成功
    error_message = db.Column(db.Text)  # 错误信息
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 外键
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    
    def get_details(self):
        """获取操作详情"""
        if not self.details:
            return {}
        try:
            import json
            return json.loads(self.details)
        except:
            return {}
    
    def set_details(self, data):
        """设置操作详情"""
        import json
        self.details = json.dumps(data) if data else None
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'details': self.get_details(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'success': self.success,
            'error_message': self.error_message,
            'user_name': self.user.username if self.user else None,
            'task_name': self.task.name if self.task else None,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user.username if self.user else "unknown"}>'

    @staticmethod
    def log_action(user, action, resource_type=None, resource_id=None, 
                   resource_name=None, details=None, ip_address=None, 
                   user_agent=None, success=True, error_message=None, task=None):
        """记录审计日志"""
        log = AuditLog(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            task=task
        )
        
        if details:
            log.set_details(details)
        
        db.session.add(log)
        db.session.commit()
        return log
