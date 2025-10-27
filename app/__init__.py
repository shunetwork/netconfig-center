"""
NetManagerX - 网络设备配置管理平台
基于 Flask + AdminLTE 的 Cisco 设备管理系统
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_debugtoolbar import DebugToolbarExtension
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化扩展
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cors = CORS()
debug_toolbar = DebugToolbarExtension()

def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 配置选择
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # 加载配置
    if config_name == 'development':
        app.config.from_object('config.DevelopmentConfig')
    elif config_name == 'production':
        app.config.from_object('config.ProductionConfig')
    elif config_name == 'testing':
        app.config.from_object('config.TestingConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # 开发环境启用调试工具栏
    if app.config['DEBUG']:
        debug_toolbar.init_app(app)
    
    # 配置登录管理器
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'info'
    
    # 注册蓝图
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.devices import bp as devices_bp
    app.register_blueprint(devices_bp, url_prefix='/devices')
    
    from app.templates import bp as templates_bp
    app.register_blueprint(templates_bp, url_prefix='/templates')
    
    from app.tasks import bp as tasks_bp
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 注册错误处理器
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)
    
    # 注册模板上下文处理器
    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return dict(current_user=current_user)
    
    return app
