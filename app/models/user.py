"""
用户相关数据模型
包含用户、角色、权限管理
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Role(db.Model):
    """用户角色模型"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    permissions = db.Column(db.Integer, default=0)  # 位掩码存储权限
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    # 权限常量
    PERMISSION_VIEW = 1
    PERMISSION_EXECUTE = 2
    PERMISSION_CONFIGURE = 4
    PERMISSION_ADMIN = 8
    
    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0
    
    def add_permission(self, perm):
        """添加权限"""
        if not self.has_permission(perm):
            self.permissions += perm
    
    def remove_permission(self, perm):
        """移除权限"""
        if self.has_permission(perm):
            self.permissions -= perm
    
    def reset_permissions(self):
        """重置权限"""
        self.permissions = 0
    
    def has_permission(self, perm):
        """检查是否有权限"""
        return self.permissions & perm == perm
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    
    # 关系
    tasks = db.relationship('Task', backref='user', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            # 默认角色
            default_role = Role.query.filter_by(name='user').first()
            if default_role:
                self.role = default_role
    
    @property
    def password(self):
        """密码属性，不允许读取"""
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """设置密码，自动加密"""
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """检查用户权限"""
        if self.is_admin:
            return True
        return self.role and self.role.has_permission(permission)
    
    def can_view(self):
        """检查查看权限"""
        return self.has_permission(Role.PERMISSION_VIEW)
    
    def can_execute(self):
        """检查执行权限"""
        return self.has_permission(Role.PERMISSION_EXECUTE)
    
    def can_configure(self):
        """检查配置权限"""
        return self.has_permission(Role.PERMISSION_CONFIGURE)
    
    def ping(self):
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'role_name': self.role.name if self.role else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

    @staticmethod
    def create_default_roles():
        """创建默认角色"""
        roles_data = [
            {
                'name': 'admin',
                'description': '系统管理员',
                'permissions': Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE | 
                             Role.PERMISSION_CONFIGURE | Role.PERMISSION_ADMIN
            },
            {
                'name': 'operator',
                'description': '操作员',
                'permissions': Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE
            },
            {
                'name': 'viewer',
                'description': '查看员',
                'permissions': Role.PERMISSION_VIEW
            }
        ]
        
        for role_data in roles_data:
            role = Role.query.filter_by(name=role_data['name']).first()
            if not role:
                role = Role(**role_data)
                db.session.add(role)
        
        db.session.commit()
    
    @staticmethod
    def create_admin_user(username='admin', email='admin@netmanagerx.local', password='admin123'):
        """创建默认管理员用户"""
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            User.create_default_roles()
            admin_role = Role.query.filter_by(name='admin').first()
        
        admin_user = User.query.filter_by(username=username).first()
        if not admin_user:
            admin_user = User(
                username=username,
                email=email,
                password=password,
                role=admin_role,
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
        
        return admin_user
