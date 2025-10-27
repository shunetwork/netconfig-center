"""
通信模块路由
包含设备连接测试、命令执行等API接口
"""

from flask import render_template, request, jsonify, flash
from flask_login import login_required, current_user
from app.communication import bp
from app.communication.ssh_client import SSHService
from app.communication.telnet_client import TelnetService
from app.communication.restconf_client import RESTCONFService
from app.models import Device, ConnectionType, Task, TaskResult, AuditLog
from app import db

@bp.route('/test-connection/<int:device_id>', methods=['POST'])
@login_required
def test_connection(device_id):
    """测试设备连接"""
    device = Device.query.get_or_404(device_id)
    
    try:
        # 根据连接类型选择相应的服务
        if device.connection_type == ConnectionType.SSH:
            result = SSHService.test_connection(device)
        elif device.connection_type == ConnectionType.TELNET:
            result = TelnetService.test_connection(device)
        elif device.connection_type == ConnectionType.RESTCONF:
            result = RESTCONFService.test_connection(device)
        else:
            result = {
                'success': False,
                'error': f'不支持的连接类型: {device.connection_type.value}'
            }
        
        # 记录测试日志
        AuditLog.log_action(
            user=current_user,
            action='test_device_connection',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            details={
                'connection_type': device.connection_type.value,
                'result': result
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'连接测试异常: {str(e)}'
        }), 500

@bp.route('/execute-command/<int:device_id>', methods=['POST'])
@login_required
def execute_command(device_id):
    """执行设备命令"""
    device = Device.query.get_or_404(device_id)
    data = request.get_json()
    
    if not data or 'command' not in data:
        return jsonify({
            'success': False,
            'error': '缺少命令参数'
        }), 400
    
    command = data['command']
    timeout = data.get('timeout', 30)
    
    try:
        # 根据连接类型选择相应的服务
        if device.connection_type == ConnectionType.SSH:
            result = SSHService.execute_command(device, command, timeout)
        elif device.connection_type == ConnectionType.TELNET:
            result = TelnetService.execute_command(device, command, timeout)
        else:
            result = {
                'success': False,
                'error': f'不支持的连接类型: {device.connection_type.value}'
            }
        
        # 记录命令执行日志
        AuditLog.log_action(
            user=current_user,
            action='execute_device_command',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            details={
                'command': command,
                'connection_type': device.connection_type.value,
                'execution_time': result.get('execution_time')
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'命令执行异常: {str(e)}'
        }), 500

@bp.route('/execute-commands/<int:device_id>', methods=['POST'])
@login_required
def execute_commands(device_id):
    """批量执行设备命令"""
    device = Device.query.get_or_404(device_id)
    data = request.get_json()
    
    if not data or 'commands' not in data:
        return jsonify({
            'success': False,
            'error': '缺少命令列表参数'
        }), 400
    
    commands = data['commands']
    timeout = data.get('timeout', 30)
    
    if not isinstance(commands, list) or len(commands) == 0:
        return jsonify({
            'success': False,
            'error': '命令列表不能为空'
        }), 400
    
    try:
        # 根据连接类型选择相应的服务
        if device.connection_type == ConnectionType.SSH:
            results = SSHService.execute_commands(device, commands, timeout)
        elif device.connection_type == ConnectionType.TELNET:
            results = TelnetService.execute_commands(device, commands, timeout)
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的连接类型: {device.connection_type.value}'
            }), 400
        
        # 记录批量命令执行日志
        success_count = sum(1 for r in results if r['success'])
        AuditLog.log_action(
            user=current_user,
            action='execute_device_commands',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=success_count > 0,
            details={
                'commands': commands,
                'total_commands': len(commands),
                'success_count': success_count,
                'connection_type': device.connection_type.value
            }
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'total_commands': len(commands),
            'success_count': success_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'批量命令执行异常: {str(e)}'
        }), 500

@bp.route('/send-config/<int:device_id>', methods=['POST'])
@login_required
def send_config(device_id):
    """发送配置到设备"""
    device = Device.query.get_or_404(device_id)
    data = request.get_json()
    
    if not data or 'config_commands' not in data:
        return jsonify({
            'success': False,
            'error': '缺少配置命令列表参数'
        }), 400
    
    config_commands = data['config_commands']
    timeout = data.get('timeout', 30)
    
    if not isinstance(config_commands, list) or len(config_commands) == 0:
        return jsonify({
            'success': False,
            'error': '配置命令列表不能为空'
        }), 400
    
    try:
        # 根据连接类型选择相应的服务
        if device.connection_type == ConnectionType.SSH:
            result = SSHService.send_config(device, config_commands, timeout)
        elif device.connection_type == ConnectionType.TELNET:
            result = TelnetService.send_config(device, config_commands, timeout)
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的连接类型: {device.connection_type.value}'
            }), 400
        
        # 记录配置发送日志
        AuditLog.log_action(
            user=current_user,
            action='send_device_config',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            details={
                'config_commands': config_commands,
                'commands_count': len(config_commands),
                'connection_type': device.connection_type.value,
                'execution_time': result.get('execution_time')
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'配置发送异常: {str(e)}'
        }), 500

@bp.route('/get-system-info/<int:device_id>', methods=['GET'])
@login_required
def get_system_info(device_id):
    """获取设备系统信息"""
    device = Device.query.get_or_404(device_id)
    
    try:
        if device.connection_type == ConnectionType.RESTCONF:
            result = RESTCONFService.get_system_info(device)
        else:
            # 对于SSH和Telnet，执行show version命令
            if device.connection_type == ConnectionType.SSH:
                result = SSHService.execute_command(device, 'show version')
            elif device.connection_type == ConnectionType.TELNET:
                result = TelnetService.execute_command(device, 'show version')
            else:
                result = {
                    'success': False,
                    'error': f'不支持的连接类型: {device.connection_type.value}'
                }
        
        # 记录获取系统信息日志
        AuditLog.log_action(
            user=current_user,
            action='get_device_system_info',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            details={
                'connection_type': device.connection_type.value
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取系统信息异常: {str(e)}'
        }), 500

@bp.route('/get-interfaces/<int:device_id>', methods=['GET'])
@login_required
def get_interfaces(device_id):
    """获取设备接口信息"""
    device = Device.query.get_or_404(device_id)
    
    try:
        if device.connection_type == ConnectionType.RESTCONF:
            result = RESTCONFService.get_interfaces(device)
        else:
            # 对于SSH和Telnet，执行show interfaces命令
            if device.connection_type == ConnectionType.SSH:
                result = SSHService.execute_command(device, 'show interfaces')
            elif device.connection_type == ConnectionType.TELNET:
                result = TelnetService.execute_command(device, 'show interfaces')
            else:
                result = {
                    'success': False,
                    'error': f'不支持的连接类型: {device.connection_type.value}'
                }
        
        # 记录获取接口信息日志
        AuditLog.log_action(
            user=current_user,
            action='get_device_interfaces',
            resource_type='device',
            resource_id=device.id,
            resource_name=device.name,
            success=result['success'],
            error_message=result.get('error'),
            details={
                'connection_type': device.connection_type.value
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取接口信息异常: {str(e)}'
        }), 500

@bp.route('/batch-test-connections', methods=['POST'])
@login_required
def batch_test_connections():
    """批量测试设备连接"""
    data = request.get_json()
    
    if not data or 'device_ids' not in data:
        return jsonify({
            'success': False,
            'error': '缺少设备ID列表参数'
        }), 400
    
    device_ids = data['device_ids']
    timeout = data.get('timeout', 30)
    
    if not isinstance(device_ids, list) or len(device_ids) == 0:
        return jsonify({
            'success': False,
            'error': '设备ID列表不能为空'
        }), 400
    
    try:
        devices = Device.query.filter(Device.id.in_(device_ids)).all()
        results = {}
        
        for device in devices:
            try:
                if device.connection_type == ConnectionType.SSH:
                    result = SSHService.test_connection(device, timeout)
                elif device.connection_type == ConnectionType.TELNET:
                    result = TelnetService.test_connection(device, timeout)
                elif device.connection_type == ConnectionType.RESTCONF:
                    result = RESTCONFService.test_connection(device, timeout)
                else:
                    result = {
                        'success': False,
                        'error': f'不支持的连接类型: {device.connection_type.value}'
                    }
                
                results[device.id] = {
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'connection_type': device.connection_type.value,
                    'result': result
                }
                
            except Exception as e:
                results[device.id] = {
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'connection_type': device.connection_type.value,
                    'result': {
                        'success': False,
                        'error': str(e)
                    }
                }
        
        # 记录批量测试日志
        success_count = sum(1 for r in results.values() if r['result']['success'])
        AuditLog.log_action(
            user=current_user,
            action='batch_test_device_connections',
            resource_type='device',
            success=success_count > 0,
            details={
                'device_count': len(device_ids),
                'success_count': success_count,
                'results': results
            }
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'total_devices': len(device_ids),
            'success_count': success_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'批量连接测试异常: {str(e)}'
        }), 500
