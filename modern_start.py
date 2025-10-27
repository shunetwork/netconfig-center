#!/usr/bin/env python3
"""
NetManagerX现代化启动脚本
使用新的模板文件
"""

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# 创建Flask应用
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'netmanagerx-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///modern_netmanagerx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化扩展
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录以访问此页面。'

# 简化的用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 简化的设备模型
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    hostname = db.Column(db.String(100))
    device_type = db.Column(db.String(50), default='cisco')
    connection_type = db.Column(db.String(20), default='ssh')
    port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(100))
    password = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 设备状态相关字段
    status = db.Column(db.String(20), default='unknown')  # online, offline, unknown
    last_check = db.Column(db.DateTime)
    last_response_time = db.Column(db.Float)  # 响应时间（毫秒）
    
    def __repr__(self):
        return f'<Device {self.name} ({self.ip_address})>'
    
    def check_status(self):
        """检查设备状态"""
        import socket
        import time
        
        try:
            start_time = time.time()
            # 尝试连接设备端口
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5秒超时
            result = sock.connect_ex((self.ip_address, self.port))
            sock.close()
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            if result == 0:
                self.status = 'online'
                self.last_response_time = response_time
            else:
                self.status = 'offline'
                self.last_response_time = None
                
        except Exception as e:
            self.status = 'offline'
            self.last_response_time = None
            
        self.last_check = datetime.utcnow()
        return self.status
    
    def get_status_display(self):
        """获取状态显示信息"""
        if self.status == 'online':
            return {'text': '在线', 'class': 'status-active'}
        elif self.status == 'offline':
            return {'text': '离线', 'class': 'status-inactive'}
        else:
            return {'text': '未知', 'class': 'status-inactive'}

class ConfigTemplate(db.Model):
    """配置模板模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    template_type = db.Column(db.String(50), default='config')  # config, script, backup
    category = db.Column(db.String(100), default='general')
    variables = db.Column(db.Text)  # JSON格式的变量定义
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConfigTemplate {self.name}>'
    
    def get_variables_dict(self):
        """获取变量字典"""
        if not self.variables:
            return {}
        try:
            import json
            return json.loads(self.variables)
        except:
            return {}
    
    def set_variables_dict(self, variables):
        """设置变量字典"""
        import json
        self.variables = json.dumps(variables) if variables else None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 路由定义
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            flash(f'欢迎回来，{user.username}！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已退出登录。', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    devices = Device.query.filter_by(is_active=True).all()
    return render_template('dashboard.html', devices=devices)

@app.route('/devices')
@login_required
def devices():
    devices = Device.query.filter_by(is_active=True).all()
    return render_template('devices.html', devices=devices)

@app.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'GET':
        # 清除之前的flash消息
        get_flashed_messages()
    
    if request.method == 'POST':
        device = Device(
            name=request.form.get('name'),
            ip_address=request.form.get('ip_address'),
            hostname=request.form.get('hostname'),
            device_type=request.form.get('device_type', 'cisco'),
            connection_type=request.form.get('connection_type', 'ssh'),
            port=int(request.form.get('port', 22)),
            username=request.form.get('username'),
            password=request.form.get('password'),
            description=request.form.get('description'),
            status='unknown'  # 设置初始状态
        )
        db.session.add(device)
        db.session.commit()
        
        # 添加成功后自动检查设备状态
        try:
            device.check_status()
            db.session.commit()
        except Exception as e:
            print(f"自动状态检查失败: {e}")
        
        flash('设备添加成功！', 'success')
        return redirect(url_for('devices'))
    
    return render_template('add_device.html')

@app.route('/api/devices')
@login_required
def api_devices():
    devices = Device.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': device.id,
        'name': device.name,
        'ip_address': device.ip_address,
        'hostname': device.hostname,
        'device_type': device.device_type,
        'connection_type': device.connection_type,
        'port': device.port,
        'is_active': device.is_active
    } for device in devices])

@app.route('/api/devices/<int:device_id>/delete', methods=['DELETE'])
@login_required
def delete_device(device_id):
    try:
        device = Device.query.get_or_404(device_id)
        device_name = device.name
        db.session.delete(device)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'设备 "{device_name}" 已成功删除'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除设备失败: {str(e)}'
        }), 500

@app.route('/api/devices/<int:device_id>/status', methods=['GET'])
@login_required
def check_device_status(device_id):
    """检查单个设备状态"""
    try:
        device = Device.query.get_or_404(device_id)
        status = device.check_status()
        db.session.commit()
        
        status_info = device.get_status_display()
        return jsonify({
            'success': True,
            'status': status,
            'status_text': status_info['text'],
            'status_class': status_info['class'],
            'last_check': device.last_check.isoformat() if device.last_check else None,
            'response_time': device.last_response_time
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检查设备状态失败: {str(e)}'
        }), 500

@app.route('/api/devices/status/check-all', methods=['POST'])
@login_required
def check_all_devices_status():
    """检查所有设备状态"""
    try:
        devices = Device.query.filter_by(is_active=True).all()
        results = []
        
        for device in devices:
            status = device.check_status()
            status_info = device.get_status_display()
            results.append({
                'id': device.id,
                'name': device.name,
                'status': status,
                'status_text': status_info['text'],
                'status_class': status_info['class'],
                'last_check': device.last_check.isoformat() if device.last_check else None,
                'response_time': device.last_response_time
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'devices': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检查设备状态失败: {str(e)}'
        }), 500

@app.route('/templates')
@login_required
def templates():
    # 获取所有模板
    templates = ConfigTemplate.query.filter_by(is_active=True).order_by(ConfigTemplate.created_at.desc()).all()
    return render_template('templates.html', templates=templates)

@app.route('/templates/add', methods=['GET', 'POST'])
@login_required
def add_template():
    if request.method == 'GET':
        # 清除之前的flash消息
        get_flashed_messages()
        return render_template('add_template.html')
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            template_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'content': request.form.get('content'),
                'template_type': request.form.get('template_type', 'config'),
                'category': request.form.get('category', 'general'),
                'variables': request.form.get('variables', ''),
                'is_active': True
            }
            
            # 验证必填字段
            if not template_data['name'] or not template_data['content']:
                flash('模板名称和内容不能为空', 'error')
                return render_template('add_template.html')
            
            # 创建模板记录
            template = ConfigTemplate(
                name=template_data['name'],
                description=template_data['description'],
                content=template_data['content'],
                template_type=template_data['template_type'],
                category=template_data['category'],
                variables=template_data['variables'],
                is_active=template_data['is_active']
            )
            
            db.session.add(template)
            db.session.commit()
            
            flash('模板添加成功！', 'success')
            return redirect(url_for('templates'))
            
        except Exception as e:
            flash(f'模板添加失败: {str(e)}', 'error')
            return render_template('add_template.html')

@app.route('/templates/<int:template_id>')
@login_required
def view_template(template_id):
    """查看模板详情"""
    template = ConfigTemplate.query.get_or_404(template_id)
    return render_template('view_template.html', template=template)

@app.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    """编辑模板"""
    template = ConfigTemplate.query.get_or_404(template_id)
    
    if request.method == 'GET':
        # 清除之前的flash消息
        get_flashed_messages()
        return render_template('edit_template.html', template=template)
    
    if request.method == 'POST':
        try:
            # 更新模板数据
            template.name = request.form.get('name', template.name)
            template.description = request.form.get('description', template.description)
            template.content = request.form.get('content', template.content)
            template.template_type = request.form.get('template_type', template.template_type)
            template.category = request.form.get('category', template.category)
            template.variables = request.form.get('variables', template.variables)
            
            # 验证必填字段
            if not template.name or not template.content:
                flash('模板名称和内容不能为空', 'error')
                return render_template('edit_template.html', template=template)
            
            db.session.commit()
            flash('模板更新成功！', 'success')
            return redirect(url_for('templates'))
            
        except Exception as e:
            flash(f'模板更新失败: {str(e)}', 'error')
            return render_template('edit_template.html', template=template)

@app.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(template_id):
    """删除模板"""
    template = ConfigTemplate.query.get_or_404(template_id)
    
    try:
        # 软删除：设置is_active为False
        template.is_active = False
        db.session.commit()
        flash('模板删除成功！', 'success')
    except Exception as e:
        flash(f'模板删除失败: {str(e)}', 'error')
    
    return redirect(url_for('templates'))

@app.route('/api/templates/<int:template_id>/delete', methods=['POST'])
@login_required
def api_delete_template(template_id):
    """API删除模板"""
    template = ConfigTemplate.query.get_or_404(template_id)
    
    try:
        # 软删除：设置is_active为False
        template.is_active = False
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '模板删除成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/tasks')
@login_required
def tasks():
    return render_template('tasks.html')

@app.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'GET':
        # 清除之前的flash消息
        get_flashed_messages()
        # 获取所有设备和模板用于下拉选择
        devices = Device.query.filter_by(is_active=True).all()
        templates = ConfigTemplate.query.filter_by(is_active=True).all()
        return render_template('create_task.html', devices=devices, templates=templates)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            task_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'task_type': request.form.get('task_type', 'command'),
                'device_id': request.form.get('device_id'),
                'template_id': request.form.get('template_id'),
                'command': request.form.get('command'),
                'is_active': True
            }
            
            # 验证必填字段
            if not task_data['name']:
                flash('任务名称不能为空', 'error')
                devices = Device.query.filter_by(is_active=True).all()
                templates = ConfigTemplate.query.filter_by(is_active=True).all()
                return render_template('create_task.html', devices=devices, templates=templates)
            
            # TODO: 这里可以添加更多验证逻辑
            # 例如验证设备是否存在、模板是否存在等
            
            flash('任务创建成功！', 'success')
            return redirect(url_for('tasks'))
            
        except Exception as e:
            flash(f'任务创建失败: {str(e)}', 'error')
            devices = Device.query.filter_by(is_active=True).all()
            templates = ConfigTemplate.query.filter_by(is_active=True).all()
            return render_template('create_task.html', devices=devices, templates=templates)

@app.route('/api/templates/<int:template_id>/variables', methods=['GET'])
@login_required
def get_template_variables(template_id):
    """获取模板变量"""
    try:
        template = ConfigTemplate.query.get_or_404(template_id)
        variables_dict = template.get_variables_dict()
        
        # 将字典转换为列表格式，以便前端处理
        variables_list = []
        if isinstance(variables_dict, dict):
            # 如果是字典，转换为列表
            for key, value in variables_dict.items():
                if isinstance(value, dict):
                    # 处理 JSON Schema 格式
                    var_type = value.get('type', 'string')
                    description = value.get('description', '')
                    
                    # 如果是 array 类型，转换为 textarea
                    if var_type == 'array':
                        var_type = 'textarea'
                    
                    # 获取默认值或空值
                    default_value = value.get('default', '')
                    if not default_value and var_type == 'textarea':
                        default_value = ''  # textarea 默认为空
                    
                    # 检查是否必需
                    required = value.get('required', False)
                    if not isinstance(required, bool):
                        required = key in value.get('required', [])
                    
                    variables_list.append({
                        'name': key,
                        'type': var_type,
                        'default': default_value,
                        'description': description,
                        'required': required
                    })
                elif isinstance(value, str) and value == 'string':
                    # 处理简单格式：{"variable": "string"}
                    variables_list.append({
                        'name': key,
                        'type': 'string',
                        'default': '',
                        'description': '',
                        'required': False
                    })
                else:
                    # 如果值只是字符串（默认值）
                    variables_list.append({
                        'name': key,
                        'type': 'string',
                        'default': value if isinstance(value, str) else '',
                        'description': '',
                        'required': False
                    })
        elif isinstance(variables_dict, list):
            # 如果已经是列表格式，直接使用
            variables_list = variables_dict
        
        return jsonify({
            'success': True,
            'variables': variables_list
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health_check():
    return jsonify({"status": "OK", "message": "NetManagerX is running"})

# 数据库初始化
def init_db():
    """初始化数据库"""
    print("正在初始化数据库...")
    
    # 强制删除旧数据库并重新创建
    import os
    db_file = 'netmanagerx.db'
    if os.path.exists(db_file):
        print("删除旧数据库文件...")
        os.remove(db_file)
    
    db.create_all()
    
    # 检查用户是否已存在
    existing_user = User.query.filter_by(username='admin').first()
    if not existing_user:
        # 创建默认用户
        admin_user = User(
            username='admin',
            email='admin@example.com'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        print("默认用户已创建")
    else:
        print("默认用户已存在")
    
    # 检查设备是否已存在（只有在数据库表存在时才检查）
    try:
        existing_device = Device.query.filter_by(name='测试路由器').first()
    except Exception:
        existing_device = None
    
    if not existing_device:
        # 创建测试设备
        test_device = Device(
            name='测试路由器',
            ip_address='192.168.1.1',
            hostname='router-01',
            device_type='cisco',
            connection_type='ssh',
            port=22,
            username='admin',
            password='password',
            description='测试设备',
            status='unknown'  # 设置初始状态
        )
        db.session.add(test_device)
        print("测试设备已创建")
    else:
        print("测试设备已存在")
    
    db.session.commit()
    print("数据库初始化完成！")
    print("默认管理员账户: admin / admin123")

if __name__ == '__main__':
    # 检查数据库是否存在，如果不存在则初始化
    if not os.path.exists('modern_netmanagerx.db'):
        print("数据库不存在，正在初始化...")
        with app.app_context():
            init_db()
    
    print("NetManagerX现代化服务启动中...")
    print("访问地址: http://localhost:5001")
    print("默认管理员账户: admin / admin123")
    print("按 Ctrl+C 停止服务器")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True)
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
