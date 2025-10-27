"""
数据库模型模块
包含所有数据表的模型定义
"""

from .user import User, Role
from .device import Device, DeviceGroup, DeviceConnection, DeviceType, ConnectionType, DeviceStatus
from .template import ConfigTemplate, TemplateVariable, TemplateCategory
from .task import Task, TaskResult, AuditLog, TaskStatus, TaskType
from .backup import ConfigBackup, BackupSchedule, BackupScheduleDeviceGroup, BackupScheduleDevice

__all__ = [
    'User', 'Role',
    'Device', 'DeviceGroup', 'DeviceConnection', 'DeviceType', 'ConnectionType', 'DeviceStatus',
    'ConfigTemplate', 'TemplateVariable', 'TemplateCategory',
    'Task', 'TaskResult', 'AuditLog', 'TaskStatus', 'TaskType',
    'ConfigBackup', 'BackupSchedule', 'BackupScheduleDeviceGroup', 'BackupScheduleDevice'
]
