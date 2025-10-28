#!/usr/bin/env python3
"""
NetManagerX现代化启动脚本
使用新的模板文件
"""

import os
import sys
import json
import socket
import time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import netmiko
from netmiko import ConnectHandler
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException, ConnectionException

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
    
    # 设备分组
    group_id = db.Column(db.Integer, db.ForeignKey('device_group.id'), nullable=True)
    
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

class DeviceGroup(db.Model):
    """设备分组模型"""
    __tablename__ = 'device_group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(20), default='#007bff')  # 分组颜色标识
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系属性
    devices = db.relationship('Device', backref='group', lazy='dynamic')
    
    def __repr__(self):
        return f'<DeviceGroup {self.name}>'
    
    def get_device_count(self):
        """获取分组中的设备数量"""
        return self.devices.count()
    
    @property
    def device_list(self):
        """获取分组中的设备列表"""
        return self.devices.all()

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

class Task(db.Model):
    """任务模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    task_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联字段
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('device_group.id'))
    template_id = db.Column(db.Integer, db.ForeignKey('config_template.id'))
    
    # 任务配置
    command = db.Column(db.Text)
    template_variables = db.Column(db.Text)  # JSON格式
    result = db.Column(db.Text)
    error_message = db.Column(db.Text)
    
    # 执行相关字段
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    executed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    execution_log = db.Column(db.Text)
    progress = db.Column(db.Integer, default=0)  # 0-100
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    def __repr__(self):
        return f'<Task {self.name}>'
    
    def get_progress_display(self):
        """获取进度显示"""
        if self.status == 'completed':
            return 100
        elif self.status == 'running':
            return self.progress or 0
        elif self.status == 'failed':
            return self.progress or 0
        else:
            return 0

class TaskLog(db.Model):
    """任务日志模型"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(50), nullable=False)  # created, started, completed, failed, etc.
    message = db.Column(db.Text)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TaskLog {self.action} for task {self.task_id}>'

class DeviceExecutionResult(db.Model):
    """设备执行结果模型"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success, failed, timeout
    result = db.Column(db.Text)
    error_message = db.Column(db.Text)
    execution_time = db.Column(db.Float)  # 执行时间（秒）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DeviceExecutionResult {self.status} for device {self.device_id}>'

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
    # 获取查询参数
    group_id = request.args.get('group_id', type=int)
    
    # 查询设备
    query = Device.query.filter_by(is_active=True)
    
    if group_id:
        query = query.filter_by(group_id=group_id)
    
    devices = query.all()
    
    # 获取所有分组
    groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
    
    return render_template('devices.html', devices=devices, groups=groups, current_group_id=group_id)

@app.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'GET':
        # 清除之前的flash消息
        get_flashed_messages()
        # 获取所有分组供选择
        groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
        return render_template('add_device.html', groups=groups)
    
    if request.method == 'POST':
        # 获取分组ID
        group_id = request.form.get('group_id')
        if group_id == '' or group_id == '0':
            group_id = None
        elif group_id:
            group_id = int(group_id)
        
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
            group_id=group_id,
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

@app.route('/api/devices/<int:device_id>/test-connection', methods=['POST'])
@login_required
def test_device_connection(device_id):
    """测试设备连接（包括SSH认证）"""
    try:
        device = Device.query.get_or_404(device_id)
        
        # 尝试连接到设备
        connection = None
        try:
            connection = connect_to_device(device)
            
            # 测试基本命令
            output = connection.send_command('show version')
            
            return jsonify({
                'success': True,
                'message': '设备连接成功',
                'output': output[:200] + '...' if len(output) > 200 else output
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'设备连接失败: {str(e)}'
            })
            
        finally:
            if connection:
                try:
                    connection.disconnect()
                except:
                    pass
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试设备连接失败: {str(e)}'
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

# ========== 设备分组管理路由 ==========

@app.route('/devices/groups')
@login_required
def device_groups():
    """设备分组列表"""
    groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
    
    # 计算统计数据
    total_groups = len(groups)
    active_groups = len([g for g in groups if g.get_device_count() > 0])
    total_devices = sum(g.get_device_count() for g in groups)
    empty_groups = len([g for g in groups if g.get_device_count() == 0])
    
    return render_template('device_groups.html', 
                         groups=groups,
                         total_groups=total_groups,
                         active_groups=active_groups,
                         total_devices=total_devices,
                         empty_groups=empty_groups)

@app.route('/devices/groups/add', methods=['GET', 'POST'])
@login_required
def add_device_group():
    """添加设备分组"""
    if request.method == 'GET':
        # 清除之前的flash消息
        get_flashed_messages()
        return render_template('add_device_group.html')
    
    if request.method == 'POST':
        try:
            group = DeviceGroup(
                name=request.form.get('name'),
                description=request.form.get('description'),
                color=request.form.get('color', '#007bff')
            )
            db.session.add(group)
            db.session.commit()
            flash('设备分组添加成功！', 'success')
            return redirect(url_for('device_groups'))
        except Exception as e:
            flash(f'设备分组添加失败: {str(e)}', 'error')
            return render_template('add_device_group.html')

@app.route('/devices/groups/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_device_group(group_id):
    """编辑设备分组"""
    group = DeviceGroup.query.get_or_404(group_id)
    
    if request.method == 'GET':
        # 清除之前的flash消息
        get_flashed_messages()
        return render_template('edit_device_group.html', group=group)
    
    if request.method == 'POST':
        try:
            group.name = request.form.get('name', group.name)
            group.description = request.form.get('description', group.description)
            group.color = request.form.get('color', group.color)
            
            db.session.commit()
            flash('设备分组更新成功！', 'success')
            return redirect(url_for('device_groups'))
        except Exception as e:
            flash(f'设备分组更新失败: {str(e)}', 'error')
            return render_template('edit_device_group.html', group=group)

@app.route('/api/device-groups', methods=['GET'])
@login_required
def api_device_groups():
    """获取所有设备分组"""
    groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
    return jsonify([{
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'color': group.color,
        'device_count': group.get_device_count(),
        'created_at': group.created_at.isoformat() if group.created_at else None
    } for group in groups])

@app.route('/api/device-groups/<int:group_id>', methods=['DELETE'])
@login_required
def delete_device_group(group_id):
    """删除设备分组"""
    try:
        group = DeviceGroup.query.get_or_404(group_id)
        group_name = group.name
        
        # 将该分组下的设备移动到未分组
        devices = Device.query.filter_by(group_id=group_id).all()
        for device in devices:
            device.group_id = None
        
        db.session.delete(group)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'设备分组 "{group_name}" 已删除'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除设备分组失败: {str(e)}'
        }), 500

@app.route('/api/devices/<int:device_id>/group', methods=['PUT'])
@login_required
def update_device_group(device_id):
    """更新设备的分组"""
    try:
        device = Device.query.get_or_404(device_id)
        data = request.get_json()
        group_id = data.get('group_id')
        
        if group_id:
            # 验证分组存在
            group = DeviceGroup.query.get(group_id)
            if not group:
                return jsonify({
                    'success': False,
                    'message': '设备分组不存在'
                }), 400
            device.group_id = group_id
        else:
            device.group_id = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '设备分组更新成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'更新设备分组失败: {str(e)}'
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


@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks_api():
    """获取任务列表API"""
    try:
        tasks = Task.query.order_by(Task.created_at.desc()).all()
        return jsonify([{
            'id': task.id,
            'name': task.name,
            'description': task.description,
            'task_type': task.task_type,
            'status': task.status,
            'progress': task.progress,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        } for task in tasks])
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务列表失败: {str(e)}'
        }), 500

@app.route('/tasks')
@login_required
def tasks():
    # 获取所有任务
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'GET':
        # 清除之前的flash消息
        get_flashed_messages()
        # 获取所有设备、分组和模板用于下拉选择
        devices = Device.query.filter_by(is_active=True).all()
        groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
        templates = ConfigTemplate.query.filter_by(is_active=True).all()
        return render_template('create_task.html', devices=devices, groups=groups, templates=templates)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            task_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'task_type': request.form.get('task_type', 'command'),
                'target_type': request.form.get('target_type', 'devices'),
                'device_id': request.form.get('device_id'),
                'group_id': request.form.get('group_id'),
                'template_id': request.form.get('template_id'),
                'command': request.form.get('command'),
                'template_variables': request.form.get('template_variables'),
                'is_active': True
            }
            
            # 验证必填字段
            if not task_data['name']:
                flash('任务名称不能为空', 'error')
                devices = Device.query.filter_by(is_active=True).all()
                groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
                templates = ConfigTemplate.query.filter_by(is_active=True).all()
                return render_template('create_task.html', devices=devices, groups=groups, templates=templates)
            
            # 验证目标选择
            if task_data['target_type'] == 'devices' and not task_data['device_id']:
                flash('请选择目标设备', 'error')
                devices = Device.query.filter_by(is_active=True).all()
                groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
                templates = ConfigTemplate.query.filter_by(is_active=True).all()
                return render_template('create_task.html', devices=devices, groups=groups, templates=templates)
            
            if task_data['target_type'] == 'groups' and not task_data['group_id']:
                flash('请选择目标分组', 'error')
                devices = Device.query.filter_by(is_active=True).all()
                groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
                templates = ConfigTemplate.query.filter_by(is_active=True).all()
                return render_template('create_task.html', devices=devices, groups=groups, templates=templates)
            
            # 创建任务记录
            task = Task(
                name=task_data['name'],
                description=task_data['description'],
                task_type=task_data['task_type'],
                device_id=task_data['device_id'] if task_data['target_type'] == 'devices' else None,
                group_id=task_data['group_id'] if task_data['target_type'] == 'groups' else None,
                template_id=task_data['template_id'],
                command=task_data['command'],
                template_variables=task_data['template_variables'],
                user_id=current_user.id,
                status='pending'
            )
            
            db.session.add(task)
            db.session.commit()
            
            flash('任务创建成功！', 'success')
            return redirect(url_for('tasks'))
            
        except Exception as e:
            flash(f'任务创建失败: {str(e)}', 'error')
            devices = Device.query.filter_by(is_active=True).all()
            groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
            templates = ConfigTemplate.query.filter_by(is_active=True).all()
            return render_template('create_task.html', devices=devices, groups=groups, templates=templates)

# ========== 任务执行相关路由 ==========

@app.route('/api/tasks/<int:task_id>/execute', methods=['POST'])
@login_required
def execute_task(task_id):
    """执行任务"""
    try:
        task = Task.query.get_or_404(task_id)
        
        # 检查任务状态
        if task.status == 'running':
            return jsonify({
                'success': False,
                'message': '任务正在执行中'
            }), 400
        
        if task.status == 'completed':
            return jsonify({
                'success': False,
                'message': '任务已完成'
            }), 400
        
        # 更新任务状态
        task.status = 'running'
        task.started_at = datetime.utcnow()
        task.executed_by = current_user.id
        task.progress = 0
        
        # 记录日志
        log = TaskLog(
            task_id=task.id,
            user_id=current_user.id,
            action='started',
            message=f'用户 {current_user.username} 开始执行任务',
            details=f'任务类型: {task.task_type}'
        )
        db.session.add(log)
        db.session.commit()
        
        # 异步执行任务（这里先模拟同步执行）
        try:
            # 更新进度为10%
            task.progress = 10
            db.session.commit()
            
            result = execute_task_logic(task)
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            task.progress = 100
            task.result = result
            
            # 记录完成日志
            log = TaskLog(
                task_id=task.id,
                user_id=current_user.id,
                action='completed',
                message='任务执行完成',
                details=result
            )
            db.session.add(log)
            
        except Exception as e:
            task.status = 'failed'
            task.completed_at = datetime.utcnow()
            task.error_message = str(e)
            task.progress = 100  # 失败也要设置进度为100%
            
            # 记录失败日志
            log = TaskLog(
                task_id=task.id,
                user_id=current_user.id,
                action='failed',
                message='任务执行失败',
                details=str(e)
            )
            db.session.add(log)
            import traceback
            traceback.print_exc()  # 打印完整的错误堆栈
        
        db.session.commit()
        
        # 返回详细的执行结果
        success_msg = '成功' if task.status == 'completed' else '失败'
        return jsonify({
            'success': True,
            'message': f'任务执行{success_msg}',
            'status': task.status,
            'progress': task.progress,
            'error_message': task.error_message if hasattr(task, 'error_message') else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'执行任务失败: {str(e)}'
        }), 500

@app.template_filter('get_log_action_text')
def get_log_action_text(action):
    """获取日志操作文本"""
    actions = {
        'created': '任务创建',
        'started': '开始执行',
        'completed': '执行完成',
        'failed': '执行失败',
        'stopped': '任务停止',
        'deleted': '任务删除',
        'reset': '任务重置'
    }
    return actions.get(action, action)

@app.template_filter('get_log_action_color')
def get_log_action_color(action):
    """获取日志操作颜色"""
    colors = {
        'created': 'primary',
        'started': 'info',
        'completed': 'success',
        'failed': 'danger',
        'stopped': 'warning',
        'deleted': 'danger',
        'reset': 'secondary'
    }
    return colors.get(action, 'secondary')

@app.route('/logs')
@login_required
def system_logs():
    """系统日志页面"""
    # 获取当前用户相关的所有任务日志
    logs = TaskLog.query.filter_by(user_id=current_user.id).order_by(TaskLog.created_at.desc()).limit(50).all()
    
    # 获取任务信息
    task_logs = []
    for log in logs:
        task = Task.query.get(log.task_id)
        task_logs.append({
            'log': log,
            'task_name': task.name if task else '未知任务',
            'task_id': log.task_id
        })
    
    return render_template('system_logs.html', logs=task_logs)

@app.route('/api/tasks/<int:task_id>/logs', methods=['GET'])
@login_required
def get_task_logs(task_id):
    """获取任务日志"""
    try:
        task = Task.query.get_or_404(task_id)
        logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'logs': [{
                'id': log.id,
                'action': log.action,
                'message': log.message,
                'details': log.details,
                'created_at': log.created_at.isoformat() if log.created_at else None,
                'user_id': log.user_id
            } for log in logs]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务日志失败: {str(e)}'
        }), 500

@app.route('/api/tasks/<int:task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    """停止任务"""
    try:
        task = Task.query.get_or_404(task_id)

        if task.status != 'running':
            return jsonify({
                'success': False,
                'message': '任务未在运行中'
            }), 400

        # 更新任务状态
        task.status = 'failed'
        task.completed_at = datetime.utcnow()
        task.error_message = '任务被用户停止'

        # 记录停止日志
        log = TaskLog(
            task_id=task.id,
            user_id=current_user.id,
            action='stopped',
            message=f'用户 {current_user.username} 停止了任务',
            details='任务被手动停止'
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '任务已停止'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'停止任务失败: {str(e)}'
        }), 500

@app.route('/api/tasks/<int:task_id>/reset', methods=['POST'])
@login_required
def reset_task(task_id):
    """重置任务状态"""
    try:
        task = Task.query.get_or_404(task_id)

        # 重置任务状态
        task.status = 'pending'
        task.started_at = None
        task.completed_at = None
        task.progress = 0
        task.error_message = None
        task.result = None

        # 记录重置日志
        log = TaskLog(
            task_id=task.id,
            user_id=current_user.id,
            action='reset',
            message=f'用户 {current_user.username} 重置了任务',
            details='任务状态已重置为待执行'
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '任务已重置'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'重置任务失败: {str(e)}'
        }), 500

def execute_task_logic(task):
    """执行任务的核心逻辑"""
    import time
    import json
    
    result = {
        'task_id': task.id,
        'task_name': task.name,
        'execution_time': None,
        'device_results': []
    }
    
    start_time = time.time()
    
    try:
        # 获取目标设备
        devices = []
        if task.device_id:
            # 单个设备
            device = Device.query.get(task.device_id)
            if device:
                devices = [device]
        elif task.group_id:
            # 分组设备
            devices = Device.query.filter_by(group_id=task.group_id, is_active=True).all()
        
        if not devices:
            raise Exception('未找到目标设备')
        
        # 根据任务类型执行
        if task.task_type == 'command':
            result['device_results'] = execute_commands_on_devices(task, devices)
        elif task.task_type == 'config':
            result['device_results'] = execute_config_on_devices(task, devices)
        elif task.task_type == 'backup':
            result['device_results'] = execute_backup_on_devices(task, devices)
        else:
            raise Exception(f'不支持的任务类型: {task.task_type}')
        
        # 计算执行时间
        execution_time = time.time() - start_time
        result['execution_time'] = execution_time
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        raise Exception(f'任务执行失败: {str(e)}')

def connect_to_device(device):
    """连接到网络设备"""
    try:
        # 根据连接类型选择Netmiko设备类型
        # 注意：这里使用connection_type而不是device_type
        if device.connection_type == 'telnet':
            netmiko_type = 'cisco_ios_telnet'
        elif device.connection_type == 'ssh':
            # 根据设备类型选择Netmiko设备类型
            device_type_map = {
                'cisco_ios': 'cisco_ios',
                'cisco_xe': 'cisco_ios',
                'cisco_xr': 'cisco_xr',
                'cisco_nxos': 'cisco_nxos',
                'huawei': 'huawei',
                'hp_procurve': 'hp_procurve',
                'juniper': 'juniper_junos',
                'arista': 'arista_eos'
            }
            netmiko_type = device_type_map.get(device.device_type.lower(), 'cisco_ios')
        else:
            netmiko_type = 'cisco_ios'
        
        # 设备连接参数
        connection_params = {
            'device_type': netmiko_type,
            'host': device.ip_address,
            'username': device.username,
            'password': device.password,
            'port': device.port or 22,
            'timeout': 30,
            'session_timeout': 60,
            'banner_timeout': 15,
            'auth_timeout': 10,
            'read_timeout_override': 60,
            'fast_cli': False,
        }
        
        # 建立连接
        connection = ConnectHandler(**connection_params)
        return connection
        
    except NetMikoTimeoutException:
        raise Exception(f"连接超时: 无法连接到设备 {device.name} ({device.ip_address})")
    except NetMikoAuthenticationException:
        raise Exception(f"认证失败: 设备 {device.name} 的用户名或密码错误")
    except ConnectionException as e:
        raise Exception(f"连接错误: 设备 {device.name} 连接失败 - {str(e)}")
    except Exception as e:
        raise Exception(f"连接设备 {device.name} 时发生未知错误: {str(e)}")

def execute_commands_on_devices(task, devices):
    """在设备上执行命令"""
    results = []
    
    for i, device in enumerate(devices):
        device_result = {
            'device_id': device.id,
            'device_name': device.name,
            'status': 'success',
            'result': '',
            'error_message': None,
            'execution_time': 0.0
        }
        
        start_time = time.time()
        connection = None
        
        try:
            # 更新任务进度
            progress = 20 + (i * 60 // len(devices))
            task.progress = progress
            db.session.commit()
            
            # 连接到设备
            connection = connect_to_device(device)
            
            # 执行命令
            if task.command:
                # 执行单个命令
                output = connection.send_command(task.command)
                device_result['result'] = f'命令执行成功:\n{output}'
            else:
                # 如果没有指定命令，只测试连接
                output = connection.send_command('show version')
                device_result['result'] = f'设备连接成功:\n{output[:200]}...'  # 只显示前200个字符
            
            # 计算执行时间
            execution_time = time.time() - start_time
            device_result['execution_time'] = execution_time
            
            # 记录设备执行结果
            exec_result = DeviceExecutionResult(
                task_id=task.id,
                device_id=device.id,
                status='success',
                result=device_result['result'],
                execution_time=execution_time
            )
            db.session.add(exec_result)
            
        except Exception as e:
            device_result['status'] = 'failed'
            device_result['error_message'] = str(e)
            device_result['execution_time'] = time.time() - start_time
            
            # 记录失败结果
            exec_result = DeviceExecutionResult(
                task_id=task.id,
                device_id=device.id,
                status='failed',
                error_message=str(e),
                execution_time=device_result['execution_time']
            )
            db.session.add(exec_result)
            
        finally:
            # 确保关闭连接
            if connection:
                try:
                    connection.disconnect()
                except:
                    pass
        
        results.append(device_result)
    
    return results

def execute_config_on_devices(task, devices):
    """在设备上执行配置"""
    results = []
    
    for i, device in enumerate(devices):
        device_result = {
            'device_id': device.id,
            'device_name': device.name,
            'status': 'success',
            'result': '',
            'error_message': None,
            'execution_time': 0.0
        }
        
        start_time = time.time()
        connection = None
        
        try:
            # 更新任务进度
            progress = 20 + (i * 60 // len(devices))
            task.progress = progress
            db.session.commit()
            
            # 连接到设备
            connection = connect_to_device(device)
            output_lines = []
            output_lines.append(f"设备连接成功: {device.name} ({device.ip_address})")
            
            # 根据连接类型决定是否需要进入特权模式
            # Telnet连接可能不需要enable，直接尝试
            try:
                # 尝试进入特权模式
                connection.enable()
                output_lines.append("成功进入特权模式")
            except Exception as e:
                # 如果enable失败，记录但不影响后续执行
                output_lines.append(f"进入特权模式警告: {str(e)}")
                # 如果enable失败，尝试断开并重新连接
                try:
                    connection.disconnect()
                    connection = connect_to_device(device)
                    output_lines.append("重新连接成功")
                except Exception as reconnect_error:
                    raise Exception(f"重新连接失败: {str(reconnect_error)}")
            
            # 生成配置命令
            config_commands = []
            
            if task.template_id:
                # 使用模板生成配置
                template = ConfigTemplate.query.get(task.template_id)
                if template:
                    # 解析模板变量
                    template_vars = {}
                    if task.template_variables:
                        try:
                            template_vars = json.loads(task.template_variables)
                        except:
                            pass
                    
                    # 渲染模板
                    from jinja2 import Template
                    jinja_template = Template(template.content)
                    config_content = jinja_template.render(**template_vars)
                    
                    # 将配置内容按行分割
                    config_commands = [line.strip() for line in config_content.split('\n') if line.strip()]
                else:
                    raise Exception("模板不存在")
            else:
                # 使用直接命令
                if task.command:
                    config_commands = [task.command]
                else:
                    raise Exception("未指定配置命令或模板")
            
            # 执行配置命令 - 使用最简单稳定的方法
            if config_commands:
                # 先进入配置模式
                try:
                    connection.write_channel('configure terminal\n')
                    time.sleep(0.5)
                    config_mode_output = connection.read_channel()
                    output_lines.append(f"进入配置模式: {config_mode_output.strip()[:100]}")
                except Exception as e:
                    output_lines.append(f"进入配置模式失败: {str(e)}")
                
                # 逐条发送配置命令
                for cmd in config_commands:
                    if cmd.strip():
                        try:
                            # 使用write_channel直接写入命令，然后读取输出
                            connection.write_channel(cmd + '\n')
                            time.sleep(0.5)  # 等待命令执行
                            output = connection.read_channel()
                            output_lines.append(f"执行: {cmd}")
                            if output.strip():
                                # 只记录前100个字符，避免输出过长
                                output_lines.append(f"输出: {output.strip()[:100]}")
                        except Exception as e:
                            output_lines.append(f"命令失败: {cmd} - {str(e)}")
                
                # 退出配置模式
                try:
                    connection.write_channel('end\n')
                    time.sleep(0.5)
                    end_output = connection.read_channel()
                    output_lines.append(f"退出配置模式: {end_output.strip()[:100]}")
                except Exception as e:
                    output_lines.append(f"退出配置模式警告: {str(e)}")
            
            # 保存配置
            try:
                connection.write_channel('write memory\n')
                time.sleep(2)  # 等待保存完成
                save_output = connection.read_channel()
                output_lines.append(f"配置保存: {save_output.strip()[:100]}")
            except Exception as e:
                output_lines.append(f"配置保存警告: {str(e)}")
            
            # 计算执行时间
            execution_time = time.time() - start_time
            device_result['execution_time'] = execution_time
            device_result['result'] = f'配置执行成功:\n' + '\n'.join(output_lines)
            
            # 记录设备执行结果
            exec_result = DeviceExecutionResult(
                task_id=task.id,
                device_id=device.id,
                status='success',
                result=device_result['result'],
                execution_time=execution_time
            )
            db.session.add(exec_result)
            
        except Exception as e:
            device_result['status'] = 'failed'
            device_result['error_message'] = str(e)
            device_result['execution_time'] = time.time() - start_time
            
            # 记录失败结果
            exec_result = DeviceExecutionResult(
                task_id=task.id,
                device_id=device.id,
                status='failed',
                error_message=str(e),
                execution_time=device_result['execution_time']
            )
            db.session.add(exec_result)
            
        finally:
            # 确保关闭连接
            if connection:
                try:
                    connection.disconnect()
                except:
                    pass
        
        results.append(device_result)
    
    return results

def execute_backup_on_devices(task, devices):
    """在设备上执行备份"""
    results = []
    
    for device in devices:
        device_result = {
            'device_id': device.id,
            'device_name': device.name,
            'status': 'success',
            'result': '',
            'error_message': None,
            'execution_time': 0.0
        }
        
        start_time = time.time()
        connection = None
        
        try:
            # 连接到设备
            connection = connect_to_device(device)
            
            # 获取设备配置
            connection.enable()
            config_output = connection.send_command('show running-config')
            
            # 生成备份文件名
            backup_filename = f"backup_{device.name}_{int(time.time())}.txt"
            
            # 保存备份到本地文件（在实际环境中，这里应该保存到文件系统）
            backup_content = f"# 设备配置备份\n"
            backup_content += f"# 设备名称: {device.name}\n"
            backup_content += f"# 设备IP: {device.ip_address}\n"
            backup_content += f"# 备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            backup_content += f"# 任务ID: {task.id}\n"
            backup_content += f"# {'='*50}\n\n"
            backup_content += config_output
            
            # 计算执行时间
            execution_time = time.time() - start_time
            device_result['execution_time'] = execution_time
            device_result['result'] = f'配置备份成功:\n备份文件: {backup_filename}\n配置大小: {len(backup_content)} 字符\n\n配置预览:\n{config_output[:500]}...'
            
            # 记录设备执行结果
            exec_result = DeviceExecutionResult(
                task_id=task.id,
                device_id=device.id,
                status='success',
                result=device_result['result'],
                execution_time=execution_time
            )
            db.session.add(exec_result)
            
        except Exception as e:
            device_result['status'] = 'failed'
            device_result['error_message'] = str(e)
            device_result['execution_time'] = time.time() - start_time
            
            # 记录失败结果
            exec_result = DeviceExecutionResult(
                task_id=task.id,
                device_id=device.id,
                status='failed',
                error_message=str(e),
                execution_time=device_result['execution_time']
            )
            db.session.add(exec_result)
            
        finally:
            # 确保关闭连接
            if connection:
                try:
                    connection.disconnect()
                except:
                    pass
        
        results.append(device_result)
    
    return results

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task_details(task_id):
    """获取任务详情"""
    try:
        task = Task.query.get_or_404(task_id)
        
        # 获取任务日志
        logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.created_at.desc()).limit(10).all()
        
        # 获取设备执行结果
        device_results = DeviceExecutionResult.query.filter_by(task_id=task_id).all()
        
        # 获取执行者信息
        executed_by_user = None
        if task.executed_by:
            executed_by_user = User.query.get(task.executed_by)
        
        # 获取目标设备信息
        target_devices = []
        if task.device_id:
            device = Device.query.get(task.device_id)
            if device:
                target_devices.append({
                    'id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'device_type': device.device_type
                })
        elif task.group_id:
            devices = Device.query.filter_by(group_id=task.group_id, is_active=True).all()
            target_devices = [{
                'id': device.id,
                'name': device.name,
                'ip_address': device.ip_address,
                'device_type': device.device_type
            } for device in devices]
        
        # 获取模板信息
        template_info = None
        if task.template_id:
            template = ConfigTemplate.query.get(task.template_id)
            if template:
                template_info = {
                    'id': template.id,
                    'name': template.name,
                    'description': template.description,
                    'template_type': template.template_type
                }
        
        return jsonify({
            'success': True,
            'task': {
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'task_type': task.task_type,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'progress': task.progress,
                'retry_count': task.retry_count,
                'max_retries': task.max_retries,
                'command': task.command,
                'result': task.result,
                'error_message': task.error_message,
                'execution_log': task.execution_log,
                'executed_by': {
                    'id': executed_by_user.id,
                    'username': executed_by_user.username
                } if executed_by_user else None,
                'target_devices': target_devices,
                'template': template_info,
                'logs': [{
                    'id': log.id,
                    'action': log.action,
                    'message': log.message,
                    'details': log.details,
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                    'user_id': log.user_id
                } for log in logs],
                'device_results': [{
                    'id': result.id,
                    'device_id': result.device_id,
                    'device_name': Device.query.get(result.device_id).name if Device.query.get(result.device_id) else 'Unknown',
                    'status': result.status,
                    'result': result.result,
                    'error_message': result.error_message,
                    'execution_time': result.execution_time,
                    'created_at': result.created_at.isoformat() if result.created_at else None
                } for result in device_results]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务详情失败: {str(e)}'
        }), 500

@app.route('/api/tasks/<int:task_id>/delete', methods=['DELETE'])
@login_required
def delete_task_api(task_id):
    """删除任务API"""
    try:
        task = Task.query.get_or_404(task_id)
        task_name = task.name
        
        # 记录删除日志
        log = TaskLog(
            task_id=task.id,
            user_id=current_user.id,
            action='deleted',
            message=f'用户 {current_user.username} 删除了任务',
            details=f'任务名称: {task_name}'
        )
        db.session.add(log)
        
        # 删除任务
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'任务 "{task_name}" 已删除'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除任务失败: {str(e)}'
        }), 500

@app.route('/api/tasks/<int:task_id>/download', methods=['GET'])
@login_required
def download_task_result(task_id):
    """下载任务结果"""
    try:
        task = Task.query.get_or_404(task_id)
        
        if not task.result:
            return jsonify({
                'success': False,
                'message': '任务暂无执行结果'
            }), 404
        
        # 创建下载内容
        import json
        from flask import Response
        
        # 格式化结果数据
        result_data = {
            'task_info': {
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'task_type': task.task_type,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'progress': task.progress
            },
            'execution_result': json.loads(task.result) if task.result else None,
            'error_message': task.error_message
        }
        
        # 生成文件名
        filename = f"task_{task.id}_{task.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 返回JSON文件下载
        return Response(
            json.dumps(result_data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'下载任务结果失败: {str(e)}'
        }), 500

@app.route('/api/templates', methods=['GET'])
@login_required
def get_templates_api():
    """获取所有模板API"""
    try:
        templates = ConfigTemplate.query.filter_by(is_active=True).all()
        template_list = []
        for template in templates:
            template_list.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'template_type': template.template_type,
                'category': template.category,
                'is_active': template.is_active,
                'created_at': template.created_at.isoformat() if template.created_at else None
            })
        return jsonify(template_list)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取模板列表失败: {str(e)}'
        }), 500

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
                    # 处理完整的变量定义对象
                    var_type = value.get('type', 'string')
                    description = value.get('description', '')
                    default_value = value.get('default', '')
                    required = value.get('required', False)
                    
                    # 如果类型是 textarea 或者是需要多行输入的情况
                    if var_type == 'textarea' or (var_type == 'array' and description and '批量' in description):
                        var_type = 'textarea'
                        # 确保默认值是字符串（可能包含多行）
                        if default_value and isinstance(default_value, list):
                            default_value = '\n'.join(map(str, default_value))
                        elif not default_value:
                            default_value = ''
                    
                    variables_list.append({
                        'name': key,
                        'type': var_type,
                        'default': str(default_value) if default_value else '',
                        'description': description,
                        'required': required if isinstance(required, bool) else False
                    })
                elif isinstance(value, str):
                    # 处理简单格式：{"variable": "default_value"} 或 {"variable": "string"}
                    if value == 'string':
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
                            'default': value,
                            'description': '',
                            'required': False
                        })
                else:
                    # 其他类型（如数字等）
                    variables_list.append({
                        'name': key,
                        'type': 'string',
                        'default': str(value) if value is not None else '',
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
    
    # 创建数据库表（如果不存在）
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
    
    # 检查设备是否已存在
    existing_device = Device.query.filter_by(name='测试路由器').first()
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
    
    # 检查批量VLAN模板是否已存在
    existing_template = ConfigTemplate.query.filter_by(name='批量添加VLAN模板').first()
    bulk_vlan_content = '''{% for line in vlans.strip().split("\\n") %}
{% set line = line.strip() %}
{% if line %}
{% set parts = line.split(":") %}
{% if parts|length == 2 %}
{% set vlan_id = parts[0].strip() %}
{% set vlan_name = parts[1].strip() %}
vlan {{ vlan_id }}
 name {{ vlan_name }}
{% else %}
vlan {{ line }}
 name VLAN_{{ line }}
{% endif %}
{% endif %}
{% endfor %}
interface range G3/1
{% for line in vlans.strip().split("\\n") %}
{% set line = line.strip() %}
{% if line %}
{% set parts = line.split(":") %}
{% if parts|length == 2 %}
{% set vlan_id = parts[0].strip() %}
 switchport trunk allowed vlan add {{ vlan_id }}
{% else %}
 switchport trunk allowed vlan add {{ line }}
{% endif %}
{% endif %}
{% endfor %}'''
    
    if not existing_template:
        # 创建批量VLAN模板
        bulk_vlan_template = ConfigTemplate(
            name='批量添加VLAN模板',
            description='用于批量添加多个VLAN到网络设备，支持自定义VLAN名称',
            content=bulk_vlan_content,
            template_type='config',
            category='network',
            variables='''{"vlans": {"type": "textarea", "default": "100:Sales\\n200:Engineering\\n300:Guest", "description": "批量添加VLAN ID和名称，每行一个格式\\n\\n**格式说明:**\\n- 格式1: `VLAN_ID` (自动命名为VLAN_ID)\\n- 格式2: `VLAN_ID:VLAN_Name` (指定名称)\\n\\n**示例:**\\n```\\n100:Sales\\n200:Engineering\\n300:Guest\\n400\\n```", "required": true}}''',
            is_active=True
        )
        db.session.add(bulk_vlan_template)
        print("批量VLAN模板已创建")
    else:
        # 强制更新模板内容，修复命令顺序
        existing_template.content = bulk_vlan_content
        print("批量VLAN模板已更新（修复命令顺序）")
    
    db.session.commit()
    print("数据库初始化完成！")
    print("默认管理员账户: admin / admin123")

if __name__ == '__main__':
    # 只在数据库不存在时初始化，避免删除现有数据
    if not os.path.exists('instance/modern_netmanagerx.db'):
        print("数据库不存在，正在初始化...")
        with app.app_context():
            init_db()
    else:
        # 数据库存在，确保表结构是最新的
        with app.app_context():
            print("数据库已存在，检查并更新表结构...")
            db.create_all()  # 创建新表（如果不存在）
            # 初始化基础数据（如果不存在）
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
