#!/usr/bin/env python3
"""
NetManagerX 应用启动文件
用于开发环境启动Flask应用
"""

import os
from app import create_app, db
from app.models import User, Role

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Shell上下文处理器，提供调试时的变量"""
    return {
        'db': db,
        'User': User,
        'Role': Role
    }

@app.cli.command()
def init_db():
    """初始化数据库"""
    print("正在初始化数据库...")
    db.create_all()
    
    # 创建默认角色
    print("创建默认角色...")
    User.create_default_roles()
    
    # 创建默认管理员用户
    print("创建默认管理员用户...")
    admin_user = User.create_admin_user()
    print(f"管理员用户已创建: {admin_user.username}")
    
    # 创建默认模板分类
    print("创建默认模板分类...")
    from app.models.template import TemplateCategory
    TemplateCategory.create_default_categories()
    print("默认模板分类创建完成")
    
    print("数据库初始化完成！")

@app.cli.command()
def create_admin():
    """创建管理员用户"""
    username = input("请输入管理员用户名 (默认: admin): ").strip() or 'admin'
    email = input("请输入管理员邮箱 (默认: admin@netmanagerx.local): ").strip() or 'admin@netmanagerx.local'
    password = input("请输入管理员密码 (默认: admin123): ").strip() or 'admin123'
    
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        print("错误: 未找到管理员角色，请先运行 'flask init-db'")
        return
    
    admin_user = User.query.filter_by(username=username).first()
    if admin_user:
        print(f"用户 {username} 已存在")
        return
    
    admin_user = User(
        username=username,
        email=email,
        password=password,
        role=admin_role,
        is_admin=True
    )
    db.session.add(admin_user)
    db.session.commit()
    
    print(f"管理员用户 {username} 创建成功！")

if __name__ == '__main__':
    # 开发环境启动
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
