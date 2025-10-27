"""
设备相关数据模型
包含设备信息、设备组、连接状态等
"""

from datetime import datetime
from enum import Enum
from app import db

class DeviceType(Enum):
    """设备类型枚举"""
    CISCO_ROUTER = 'cisco_router'
    CISCO_SWITCH = 'cisco_switch'
    CISCO_ASA = 'cisco_asa'
    CISCO_WLC = 'cisco_wlc'
    OTHER = 'other'

class ConnectionType(Enum):
    """连接类型枚举"""
    SSH = 'ssh'
    TELNET = 'telnet'
    RESTCONF = 'restconf'

class DeviceStatus(Enum):
    """设备状态枚举"""
    ONLINE = 'online'
    OFFLINE = 'offline'
    UNKNOWN = 'unknown'
    ERROR = 'error'

class DeviceGroup(db.Model):
    """设备组模型"""
    __tablename__ = 'device_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    devices = db.relationship('Device', backref='group', lazy='dynamic')
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'device_count': self.devices.count(),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<DeviceGroup {self.name}>'

class Device(db.Model):
    """设备模型"""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)  # 支持IPv6
    hostname = db.Column(db.String(255))
    device_type = db.Column(db.Enum(DeviceType), default=DeviceType.CISCO_ROUTER)
    connection_type = db.Column(db.Enum(ConnectionType), default=ConnectionType.SSH)
    port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(100), nullable=False)
    password_encrypted = db.Column(db.Text)  # 加密存储的密码
    ssh_key_path = db.Column(db.String(255))  # SSH密钥路径
    enable_password_encrypted = db.Column(db.Text)  # 加密存储的enable密码
    description = db.Column(db.Text)
    location = db.Column(db.String(255))
    vendor = db.Column(db.String(100), default='Cisco')
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    software_version = db.Column(db.String(100))
    status = db.Column(db.Enum(DeviceStatus), default=DeviceStatus.UNKNOWN)
    last_checked = db.Column(db.DateTime)
    last_config_backup = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    group_id = db.Column(db.Integer, db.ForeignKey('device_groups.id'))
    
    # 关系
    connections = db.relationship('DeviceConnection', backref='device', lazy='dynamic')
    tasks = db.relationship('Task', backref='device', lazy='dynamic')
    config_backups = db.relationship('ConfigBackup', backref='device', lazy='dynamic')
    
    def set_password(self, password):
        """设置密码（加密存储）"""
        from cryptography.fernet import Fernet
        from app import current_app
        
        key = current_app.config['SECRET_KEY'].encode()[:32].ljust(32, b'0')
        cipher = Fernet(Fernet.generate_key())
        self.password_encrypted = cipher.encrypt(password.encode()).decode()
    
    def get_password(self):
        """获取密码（解密）"""
        if not self.password_encrypted:
            return None
        
        from cryptography.fernet import Fernet
        from app import current_app
        
        try:
            key = current_app.config['SECRET_KEY'].encode()[:32].ljust(32, b'0')
            cipher = Fernet(Fernet.generate_key())
            return cipher.decrypt(self.password_encrypted.encode()).decode()
        except:
            return None
    
    def set_enable_password(self, password):
        """设置enable密码（加密存储）"""
        from cryptography.fernet import Fernet
        from app import current_app
        
        key = current_app.config['SECRET_KEY'].encode()[:32].ljust(32, b'0')
        cipher = Fernet(Fernet.generate_key())
        self.enable_password_encrypted = cipher.encrypt(password.encode()).decode()
    
    def get_enable_password(self):
        """获取enable密码（解密）"""
        if not self.enable_password_encrypted:
            return None
        
        from cryptography.fernet import Fernet
        from app import current_app
        
        try:
            key = current_app.config['SECRET_KEY'].encode()[:32].ljust(32, b'0')
            cipher = Fernet(Fernet.generate_key())
            return cipher.decrypt(self.enable_password_encrypted.encode()).decode()
        except:
            return None
    
    def update_status(self, status):
        """更新设备状态"""
        self.status = status
        self.last_checked = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
    
    def to_dict(self, include_credentials=False):
        """转换为字典格式"""
        data = {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'hostname': self.hostname,
            'device_type': self.device_type.value if self.device_type else None,
            'connection_type': self.connection_type.value if self.connection_type else None,
            'port': self.port,
            'username': self.username,
            'description': self.description,
            'location': self.location,
            'vendor': self.vendor,
            'model': self.model,
            'serial_number': self.serial_number,
            'software_version': self.software_version,
            'status': self.status.value if self.status else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'last_config_backup': self.last_config_backup.isoformat() if self.last_config_backup else None,
            'is_active': self.is_active,
            'group_name': self.group.name if self.group else None,
            'created_at': self.created_at.isoformat()
        }
        
        if include_credentials:
            data['password'] = self.get_password()
            data['enable_password'] = self.get_enable_password()
            data['ssh_key_path'] = self.ssh_key_path
        
        return data
    
    def __repr__(self):
        return f'<Device {self.name} ({self.ip_address})>'

class DeviceConnection(db.Model):
    """设备连接记录模型"""
    __tablename__ = 'device_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    disconnected_at = db.Column(db.DateTime)
    connection_duration = db.Column(db.Integer)  # 连接持续时间（秒）
    status = db.Column(db.String(20), default='active')  # active, closed, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 外键
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    
    def close_connection(self):
        """关闭连接"""
        if self.status == 'active':
            self.disconnected_at = datetime.utcnow()
            if self.connected_at:
                self.connection_duration = int(
                    (self.disconnected_at - self.connected_at).total_seconds()
                )
            self.status = 'closed'
            db.session.add(self)
            db.session.commit()
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'device_name': self.device.name,
            'connected_at': self.connected_at.isoformat(),
            'disconnected_at': self.disconnected_at.isoformat() if self.disconnected_at else None,
            'connection_duration': self.connection_duration,
            'status': self.status,
            'error_message': self.error_message
        }
    
    def __repr__(self):
        return f'<DeviceConnection {self.device.name} ({self.status})>'
