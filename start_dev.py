#!/usr/bin/env python3
"""
NetManagerX开发环境启动脚本
使用SQLite数据库，简化依赖
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

# 设置环境变量
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'
os.environ['DATABASE_URL'] = 'sqlite:///netmanagerx.db'

# 创建Flask应用
app = Flask(__name__)

# 基础配置
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///netmanagerx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True

# 初始化扩展
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'info'

mail = Mail(app)
csrf = CSRFProtect(app)

# 导入模型
from app.models import User, Role, Device, DeviceGroup, ConfigTemplate, Task, AuditLog

# 配置用户加载器
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 注册蓝图
from app.auth import bp as auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

from app.main import bp as main_bp
app.register_blueprint(main_bp)

from app.devices import bp as devices_bp
app.register_blueprint(devices_bp, url_prefix='/devices')

from app.templates import bp as templates_bp
app.register_blueprint(templates_bp, url_prefix='/templates')

from app.tasks import bp as tasks_bp
app.register_blueprint(tasks_bp, url_prefix='/tasks')

from app.communication import bp as communication_bp
app.register_blueprint(communication_bp, url_prefix='/communication')

from app.api import bp as api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# 错误处理
from app.errors import bp as errors_bp
app.register_blueprint(errors_bp)

# 初始化数据库
@app.cli.command()
def init_db():
    """初始化数据库"""
    print("正在初始化数据库...")
    db.create_all()
    
    # 创建默认角色
    print("创建默认角色...")
    admin_role = Role(name='admin', description='管理员')
    admin_role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE | Role.PERMISSION_CONFIGURE | Role.PERMISSION_ADMIN)
    
    user_role = Role(name='user', description='普通用户')
    user_role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE)
    
    db.session.add(admin_role)
    db.session.add(user_role)
    db.session.commit()
    
    # 创建默认管理员用户
    print("创建默认管理员用户...")
    admin_user = User(
        username='admin',
        email='admin@example.com',
        role=admin_role
    )
    admin_user.password = 'admin123'
    db.session.add(admin_user)
    db.session.commit()
    
    print(f"管理员用户已创建: {admin_user.username}")
    print("数据库初始化完成！")

# 健康检查端点
@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    # 检查数据库是否存在，如果不存在则初始化
    if not os.path.exists('netmanagerx.db'):
        print("数据库不存在，正在初始化...")
        with app.app_context():
            init_db()
    
    print("NetManagerX开发服务器启动中...")
    print("访问地址: http://localhost:5000")
    print("默认管理员账户: admin / admin123")
    print("按 Ctrl+C 停止服务器")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
