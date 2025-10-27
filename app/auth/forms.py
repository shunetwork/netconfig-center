"""
认证模块表单
包含登录、注册、密码修改等表单
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User, Role

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=64, message='用户名长度必须在3-64个字符之间')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码')
    ])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class ChangePasswordForm(FlaskForm):
    """修改密码表单"""
    current_password = PasswordField('当前密码', validators=[
        DataRequired(message='请输入当前密码')
    ])
    new_password = PasswordField('新密码', validators=[
        DataRequired(message='请输入新密码'),
        Length(min=6, max=128, message='密码长度必须在6-128个字符之间')
    ])
    confirm_password = PasswordField('确认新密码', validators=[
        DataRequired(message='请确认新密码'),
        EqualTo('new_password', message='两次输入的密码不一致')
    ])
    submit = SubmitField('修改密码')

class UserForm(FlaskForm):
    """用户表单"""
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=64, message='用户名长度必须在3-64个字符之间')
    ])
    email = StringField('邮箱', validators=[
        DataRequired(message='请输入邮箱'),
        Email(message='请输入有效的邮箱地址')
    ])
    password = PasswordField('密码', validators=[
        Length(min=6, max=128, message='密码长度必须在6-128个字符之间')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        EqualTo('password', message='两次输入的密码不一致')
    ])
    role_id = SelectField('角色', coerce=int, validators=[
        DataRequired(message='请选择角色')
    ])
    is_active = BooleanField('激活状态', default=True)
    submit = SubmitField('保存')
    
    def __init__(self, user=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        # 动态加载角色选项
        self.role_id.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        
        if user:
            self.username.data = user.username
            self.email.data = user.email
            self.role_id.data = user.role_id
            self.is_active.data = user.is_active
    
    def validate_username(self, username):
        """验证用户名唯一性"""
        user = User.query.filter_by(username=username.data).first()
        if user and (not hasattr(self, 'user') or user.id != self.user.id):
            raise ValidationError('用户名已存在')
    
    def validate_email(self, email):
        """验证邮箱唯一性"""
        user = User.query.filter_by(email=email.data).first()
        if user and (not hasattr(self, 'user') or user.id != self.user.id):
            raise ValidationError('邮箱已存在')

class RoleForm(FlaskForm):
    """角色表单"""
    name = StringField('角色名称', validators=[
        DataRequired(message='请输入角色名称'),
        Length(min=2, max=64, message='角色名称长度必须在2-64个字符之间')
    ])
    description = TextAreaField('描述')
    permissions = SelectField('权限', choices=[
        ('view', '查看权限'),
        ('execute', '执行权限'),
        ('configure', '配置权限'),
        ('admin', '管理员权限')
    ], multiple=True)
    submit = SubmitField('保存')
    
    def __init__(self, role=None, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        
        if role:
            self.name.data = role.name
            self.description.data = role.description
            # 设置权限选择
            selected_permissions = []
            if role.has_permission(Role.PERMISSION_VIEW):
                selected_permissions.append('view')
            if role.has_permission(Role.PERMISSION_EXECUTE):
                selected_permissions.append('execute')
            if role.has_permission(Role.PERMISSION_CONFIGURE):
                selected_permissions.append('configure')
            if role.has_permission(Role.PERMISSION_ADMIN):
                selected_permissions.append('admin')
            self.permissions.data = selected_permissions
    
    def validate_name(self, name):
        """验证角色名称唯一性"""
        role = Role.query.filter_by(name=name.data).first()
        if role and (not hasattr(self, 'role') or role.id != self.role.id):
            raise ValidationError('角色名称已存在')
