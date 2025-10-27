"""
配置备份相关数据模型
包含配置备份、版本管理、回滚功能等
"""

from datetime import datetime
from app import db

class ConfigBackup(db.Model):
    """配置备份模型"""
    __tablename__ = 'config_backups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    backup_type = db.Column(db.String(50), default='manual')  # manual, auto, scheduled
    
    # 备份内容
    config_content = db.Column(db.Text, nullable=False)  # 配置内容
    config_size = db.Column(db.Integer)  # 配置大小（字节）
    config_hash = db.Column(db.String(64), index=True)  # 配置哈希值
    
    # 备份信息
    backup_version = db.Column(db.String(20), default='1.0')
    is_current = db.Column(db.Boolean, default=False)  # 是否为当前配置
    is_restored = db.Column(db.Boolean, default=False)  # 是否已恢复
    
    # 设备信息快照
    device_info = db.Column(db.Text)  # JSON格式的设备信息快照
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    restored_at = db.Column(db.DateTime)  # 恢复时间
    
    # 外键
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))  # 关联的任务
    
    def get_device_info(self):
        """获取设备信息快照"""
        if not self.device_info:
            return {}
        try:
            import json
            return json.loads(self.device_info)
        except:
            return {}
    
    def set_device_info(self, info):
        """设置设备信息快照"""
        import json
        self.device_info = json.dumps(info) if info else None
    
    def calculate_hash(self):
        """计算配置哈希值"""
        import hashlib
        if self.config_content:
            self.config_hash = hashlib.sha256(self.config_content.encode()).hexdigest()
        return self.config_hash
    
    def mark_as_current(self):
        """标记为当前配置"""
        # 先将同设备的所有备份标记为非当前
        ConfigBackup.query.filter_by(device_id=self.device_id).update({'is_current': False})
        # 标记当前备份为当前配置
        self.is_current = True
        db.session.add(self)
        db.session.commit()
    
    def restore(self, user=None):
        """恢复配置"""
        self.is_restored = True
        self.restored_at = datetime.utcnow()
        if user:
            self.user_id = user.id
        db.session.add(self)
        db.session.commit()
    
    def get_diff(self, other_backup):
        """获取与另一个备份的差异"""
        if not other_backup or not other_backup.config_content:
            return None
        
        try:
            import difflib
            diff = list(difflib.unified_diff(
                other_backup.config_content.splitlines(keepends=True),
                self.config_content.splitlines(keepends=True),
                fromfile=f'backup_{other_backup.id}',
                tofile=f'backup_{self.id}',
                lineterm=''
            ))
            return ''.join(diff)
        except Exception as e:
            return f"差异计算失败: {str(e)}"
    
    def to_dict(self, include_content=False):
        """转换为字典格式"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'backup_type': self.backup_type,
            'config_size': self.config_size,
            'config_hash': self.config_hash,
            'backup_version': self.backup_version,
            'is_current': self.is_current,
            'is_restored': self.is_restored,
            'device_name': self.device.name if self.device else None,
            'user_name': self.user.username if self.user else None,
            'created_at': self.created_at.isoformat(),
            'restored_at': self.restored_at.isoformat() if self.restored_at else None
        }
        
        if include_content:
            data.update({
                'config_content': self.config_content,
                'device_info': self.get_device_info()
            })
        
        return data
    
    def __repr__(self):
        return f'<ConfigBackup {self.name} ({self.device.name if self.device else "unknown"})>'

class BackupSchedule(db.Model):
    """备份计划模型"""
    __tablename__ = 'backup_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    
    # 计划配置
    schedule_type = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly
    schedule_time = db.Column(db.Time)  # 执行时间
    schedule_day = db.Column(db.Integer)  # 星期几（1-7）或每月几号（1-31）
    
    # 备份配置
    backup_name_template = db.Column(db.String(200), default='{device_name}_{date}')
    keep_backups = db.Column(db.Integer, default=10)  # 保留备份数量
    compress_backup = db.Column(db.Boolean, default=True)  # 是否压缩备份
    
    # 状态
    is_active = db.Column(db.Boolean, default=True)
    last_run = db.Column(db.DateTime)  # 上次运行时间
    next_run = db.Column(db.DateTime)  # 下次运行时间
    
    # 统计信息
    total_runs = db.Column(db.Integer, default=0)
    success_runs = db.Column(db.Integer, default=0)
    failed_runs = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 关系
    device_groups = db.relationship('BackupScheduleDeviceGroup', backref='schedule', lazy='dynamic', cascade='all, delete-orphan')
    devices = db.relationship('BackupScheduleDevice', backref='schedule', lazy='dynamic', cascade='all, delete-orphan')
    
    def add_device_group(self, group):
        """添加设备组"""
        if not BackupScheduleDeviceGroup.query.filter_by(schedule_id=self.id, device_group_id=group.id).first():
            schedule_group = BackupScheduleDeviceGroup(schedule=self, device_group=group)
            db.session.add(schedule_group)
            db.session.commit()
    
    def add_device(self, device):
        """添加设备"""
        if not BackupScheduleDevice.query.filter_by(schedule_id=self.id, device_id=device.id).first():
            schedule_device = BackupScheduleDevice(schedule=self, device=device)
            db.session.add(schedule_device)
            db.session.commit()
    
    def get_target_devices(self):
        """获取目标设备列表"""
        devices = set()
        
        # 添加设备组中的设备
        for schedule_group in self.device_groups:
            for device in schedule_group.device_group.devices:
                devices.add(device)
        
        # 添加直接指定的设备
        for schedule_device in self.devices:
            devices.add(schedule_device.device)
        
        return list(devices)
    
    def calculate_next_run(self):
        """计算下次运行时间"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        if self.schedule_type == 'daily':
            next_run = datetime.combine(now.date(), self.schedule_time or datetime.min.time())
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif self.schedule_type == 'weekly':
            days_ahead = self.schedule_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = datetime.combine(now.date() + timedelta(days=days_ahead), 
                                      self.schedule_time or datetime.min.time())
        
        elif self.schedule_type == 'monthly':
            # 简化处理，每月1号执行
            if now.day >= self.schedule_day:
                # 下个月
                if now.month == 12:
                    next_run = datetime(now.year + 1, 1, self.schedule_day)
                else:
                    next_run = datetime(now.year, now.month + 1, self.schedule_day)
            else:
                # 本月
                next_run = datetime(now.year, now.month, self.schedule_day)
            
            next_run = datetime.combine(next_run.date(), self.schedule_time or datetime.min.time())
        
        self.next_run = next_run
        db.session.add(self)
        db.session.commit()
        return next_run
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'schedule_type': self.schedule_type,
            'schedule_time': self.schedule_time.strftime('%H:%M') if self.schedule_time else None,
            'schedule_day': self.schedule_day,
            'backup_name_template': self.backup_name_template,
            'keep_backups': self.keep_backups,
            'compress_backup': self.compress_backup,
            'is_active': self.is_active,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'total_runs': self.total_runs,
            'success_runs': self.success_runs,
            'failed_runs': self.failed_runs,
            'success_rate': (self.success_runs / self.total_runs * 100) if self.total_runs > 0 else 0,
            'target_devices_count': len(self.get_target_devices()),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<BackupSchedule {self.name} ({self.schedule_type})>'

class BackupScheduleDeviceGroup(db.Model):
    """备份计划设备组关联模型"""
    __tablename__ = 'backup_schedule_device_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('backup_schedules.id'), nullable=False)
    device_group_id = db.Column(db.Integer, db.ForeignKey('device_groups.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BackupScheduleDeviceGroup schedule_id={self.schedule_id} group_id={self.device_group_id}>'

class BackupScheduleDevice(db.Model):
    """备份计划设备关联模型"""
    __tablename__ = 'backup_schedule_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('backup_schedules.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BackupScheduleDevice schedule_id={self.schedule_id} device_id={self.device_id}>'
