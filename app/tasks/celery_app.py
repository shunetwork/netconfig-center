"""
Celery应用配置
用于异步任务处理
"""

from celery import Celery
from app import create_app

def make_celery(app=None):
    """创建Celery应用"""
    app = app or create_app()
    
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    
    class ContextTask(celery.Task):
        """确保任务在Flask应用上下文中运行"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# 创建Celery实例
celery = make_celery()

# 导入任务模块
from app.tasks import network_tasks, template_tasks, backup_tasks
