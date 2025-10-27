"""
设备管理模块路由
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.devices import bp
from app.devices.forms import DeviceForm, DeviceGroupForm, DeviceBulkForm, DeviceConnectionTestForm
from app.devices.services import DeviceManagementService, DeviceStatusService, DeviceGroupService
from app.models import Device, DeviceGroup, DeviceType, ConnectionType, DeviceStatus, AuditLog
from app import db

@bp.route('/')
@login_required
def index():
    """设备列表页面"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    group_id = request.args.get('group_id', type=int)
    status = request.args.get('status')
    
    query = Device.query
    
    if group_id:
        query = query.filter_by(group_id=group_id)
    if status:
        query = query.filter_by(status=status)
    
    devices = query.order_by(Device.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
    
    return render_template('devices/index.html', 
                         devices=devices, 
                         groups=groups,
                         current_group_id=group_id,
                         current_status=status)

@bp.route('/<int:device_id>')
@login_required
def detail(device_id):
    """设备详情页面"""
    device = Device.query.get_or_404(device_id)
    return render_template('devices/detail.html', device=device)

@bp.route('/api/devices')
@login_required
def api_devices():
    """API: 获取设备列表"""
    devices = Device.query.order_by(Device.name).all()
    return jsonify([device.to_dict() for device in devices])

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加设备"""
    form = DeviceForm()
    
    if form.validate_on_submit():
        try:
            device_data = {
                'name': form.name.data,
                'ip_address': form.ip_address.data,
                'hostname': form.hostname.data,
                'device_type': DeviceType(form.device_type.data),
                'connection_type': ConnectionType(form.connection_type.data),
                'port': form.port.data,
                'username': form.username.data,
                'password': form.password.data,
                'enable_password': form.enable_password.data,
                'ssh_key_path': form.ssh_key_path.data,
                'description': form.description.data,
                'location': form.location.data,
                'vendor': form.vendor.data,
                'model': form.model.data,
                'serial_number': form.serial_number.data,
                'software_version': form.software_version.data,
                'group_id': form.group_id.data if form.group_id.data != 0 else None
            }
            
            device = DeviceManagementService.create_device(device_data, current_user.id)
            flash('设备添加成功', 'success')
            return redirect(url_for('devices.detail', device_id=device.id))
            
        except Exception as e:
            flash(f'设备添加失败: {str(e)}', 'error')
    
    return render_template('devices/form.html', form=form, title='添加设备')

@bp.route('/<int:device_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(device_id):
    """编辑设备"""
    device = Device.query.get_or_404(device_id)
    form = DeviceForm(obj=device)
    form.device = device
    
    if form.validate_on_submit():
        try:
            device_data = {
                'name': form.name.data,
                'ip_address': form.ip_address.data,
                'hostname': form.hostname.data,
                'device_type': DeviceType(form.device_type.data),
                'connection_type': ConnectionType(form.connection_type.data),
                'port': form.port.data,
                'username': form.username.data,
                'password': form.password.data,
                'enable_password': form.enable_password.data,
                'ssh_key_path': form.ssh_key_path.data,
                'description': form.description.data,
                'location': form.location.data,
                'vendor': form.vendor.data,
                'model': form.model.data,
                'serial_number': form.serial_number.data,
                'software_version': form.software_version.data,
                'group_id': form.group_id.data if form.group_id.data != 0 else None
            }
            
            DeviceManagementService.update_device(device, device_data, current_user.id)
            flash('设备更新成功', 'success')
            return redirect(url_for('devices.detail', device_id=device.id))
            
        except Exception as e:
            flash(f'设备更新失败: {str(e)}', 'error')
    
    return render_template('devices/form.html', form=form, title='编辑设备', device=device)

@bp.route('/<int:device_id>/delete', methods=['POST'])
@login_required
def delete(device_id):
    """删除设备"""
    device = Device.query.get_or_404(device_id)
    
    try:
        DeviceManagementService.delete_device(device, current_user.id)
        flash('设备删除成功', 'success')
        return redirect(url_for('devices.index'))
    except Exception as e:
        flash(f'设备删除失败: {str(e)}', 'error')
        return redirect(url_for('devices.detail', device_id=device.id))

@bp.route('/<int:device_id>/test-connection', methods=['POST'])
@login_required
def test_connection(device_id):
    """测试设备连接"""
    device = Device.query.get_or_404(device_id)
    
    try:
        result = DeviceStatusService.check_device_status(device)
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/bulk-action', methods=['POST'])
@login_required
def bulk_action():
    """批量操作设备"""
    form = DeviceBulkForm()
    
    if form.validate_on_submit():
        try:
            device_ids = form.device_ids.data
            action = form.action.data
            
            if action == 'test_connection':
                result = DeviceStatusService.batch_check_status(device_ids)
                return jsonify({
                    'success': True,
                    'result': result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'不支持的操作: {action}'
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return jsonify({
        'success': False,
        'errors': form.errors
    }), 400

@bp.route('/groups')
@login_required
def groups():
    """设备组管理页面"""
    groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
    return render_template('devices/groups.html', groups=groups)

@bp.route('/groups/add', methods=['GET', 'POST'])
@login_required
def add_group():
    """添加设备组"""
    form = DeviceGroupForm()
    
    if form.validate_on_submit():
        try:
            group_data = {
                'name': form.name.data,
                'description': form.description.data
            }
            
            group = DeviceGroupService.create_group(group_data, current_user.id)
            flash('设备组添加成功', 'success')
            return redirect(url_for('devices.groups'))
            
        except Exception as e:
            flash(f'设备组添加失败: {str(e)}', 'error')
    
    return render_template('devices/group_form.html', form=form, title='添加设备组')

@bp.route('/api/device/<int:device_id>')
@login_required
def api_device_detail(device_id):
    """API: 获取设备详情"""
    device = Device.query.get_or_404(device_id)
    return jsonify(device.to_dict(include_credentials=False))

@bp.route('/api/groups')
@login_required
def api_groups():
    """API: 获取设备组列表"""
    groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
    return jsonify([group.to_dict() for group in groups])
