"""
设备管理模块表单
包含设备添加、编辑、分组管理等表单
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, IntegerField, BooleanField, SubmitField, FileField
from wtforms.validators import DataRequired, Length, IPAddress, NumberRange, ValidationError, Optional
from app.models import Device, DeviceGroup, DeviceType, ConnectionType

class DeviceForm(FlaskForm):
    """设备表单"""
    name = StringField('设备名称', validators=[
        DataRequired(message='请输入设备名称'),
        Length(min=2, max=100, message='设备名称长度必须在2-100个字符之间')
    ])
    ip_address = StringField('IP地址', validators=[
        DataRequired(message='请输入IP地址'),
        IPAddress(message='请输入有效的IP地址')
    ])
    hostname = StringField('主机名', validators=[
        Length(max=255, message='主机名长度不能超过255个字符')
    ])
    device_type = SelectField('设备类型', choices=[
        (DeviceType.CISCO_ROUTER.value, 'Cisco路由器'),
        (DeviceType.CISCO_SWITCH.value, 'Cisco交换机'),
        (DeviceType.CISCO_ASA.value, 'Cisco ASA防火墙'),
        (DeviceType.CISCO_WLC.value, 'Cisco无线控制器'),
        (DeviceType.OTHER.value, '其他设备')
    ], validators=[DataRequired(message='请选择设备类型')])
    connection_type = SelectField('连接类型', choices=[
        (ConnectionType.SSH.value, 'SSH'),
        (ConnectionType.TELNET.value, 'Telnet'),
        (ConnectionType.RESTCONF.value, 'RESTCONF')
    ], validators=[DataRequired(message='请选择连接类型')])
    port = IntegerField('端口', validators=[
        DataRequired(message='请输入端口号'),
        NumberRange(min=1, max=65535, message='端口号必须在1-65535之间')
    ], default=22)
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=1, max=100, message='用户名长度必须在1-100个字符之间')
    ])
    password = PasswordField('密码', validators=[
        Length(max=128, message='密码长度不能超过128个字符')
    ])
    enable_password = PasswordField('Enable密码', validators=[
        Length(max=128, message='Enable密码长度不能超过128个字符')
    ])
    ssh_key_path = StringField('SSH密钥路径', validators=[
        Length(max=255, message='SSH密钥路径长度不能超过255个字符')
    ])
    description = TextAreaField('描述', validators=[
        Length(max=500, message='描述长度不能超过500个字符')
    ])
    location = StringField('位置', validators=[
        Length(max=255, message='位置长度不能超过255个字符')
    ])
    vendor = StringField('厂商', validators=[
        Length(max=100, message='厂商名称长度不能超过100个字符')
    ], default='Cisco')
    model = StringField('型号', validators=[
        Length(max=100, message='型号长度不能超过100个字符')
    ])
    serial_number = StringField('序列号', validators=[
        Length(max=100, message='序列号长度不能超过100个字符')
    ])
    software_version = StringField('软件版本', validators=[
        Length(max=100, message='软件版本长度不能超过100个字符')
    ])
    group_id = SelectField('设备组', coerce=int, validators=[Optional()])
    is_active = BooleanField('激活状态', default=True)
    submit = SubmitField('保存')
    
    def __init__(self, device=None, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)
        # 动态加载设备组选项
        self.group_id.choices = [(0, '无分组')] + [(group.id, group.name) for group in DeviceGroup.query.order_by(DeviceGroup.name).all()]
        
        if device:
            self.name.data = device.name
            self.ip_address.data = device.ip_address
            self.hostname.data = device.hostname
            self.device_type.data = device.device_type.value if device.device_type else DeviceType.CISCO_ROUTER.value
            self.connection_type.data = device.connection_type.value if device.connection_type else ConnectionType.SSH.value
            self.port.data = device.port
            self.username.data = device.username
            self.description.data = device.description
            self.location.data = device.location
            self.vendor.data = device.vendor
            self.model.data = device.model
            self.serial_number.data = device.serial_number
            self.software_version.data = device.software_version
            self.group_id.data = device.group_id if device.group_id else 0
            self.is_active.data = device.is_active
            self.ssh_key_path.data = device.ssh_key_path
    
    def validate_name(self, name):
        """验证设备名称唯一性"""
        device = Device.query.filter_by(name=name.data).first()
        if device and (not hasattr(self, 'device') or device.id != self.device.id):
            raise ValidationError('设备名称已存在')
    
    def validate_ip_address(self, ip_address):
        """验证IP地址唯一性"""
        device = Device.query.filter_by(ip_address=ip_address.data).first()
        if device and (not hasattr(self, 'device') or device.id != self.device.id):
            raise ValidationError('IP地址已存在')
    
    def validate_group_id(self, group_id):
        """验证设备组"""
        if group_id.data == 0:
            group_id.data = None
        elif group_id.data:
            group = DeviceGroup.query.get(group_id.data)
            if not group:
                raise ValidationError('选择的设备组不存在')

class DeviceGroupForm(FlaskForm):
    """设备组表单"""
    name = StringField('组名称', validators=[
        DataRequired(message='请输入组名称'),
        Length(min=2, max=100, message='组名称长度必须在2-100个字符之间')
    ])
    description = TextAreaField('描述', validators=[
        Length(max=500, message='描述长度不能超过500个字符')
    ])
    submit = SubmitField('保存')
    
    def __init__(self, group=None, *args, **kwargs):
        super(DeviceGroupForm, self).__init__(*args, **kwargs)
        
        if group:
            self.name.data = group.name
            self.description.data = group.description
    
    def validate_name(self, name):
        """验证组名称唯一性"""
        group = DeviceGroup.query.filter_by(name=name.data).first()
        if group and (not hasattr(self, 'group') or group.id != self.group.id):
            raise ValidationError('组名称已存在')

class DeviceBulkForm(FlaskForm):
    """设备批量操作表单"""
    action = SelectField('操作', choices=[
        ('test_connection', '测试连接'),
        ('backup_config', '备份配置'),
        ('show_version', '显示版本信息'),
        ('show_inventory', '显示设备清单'),
        ('ping_test', 'Ping测试')
    ], validators=[DataRequired(message='请选择操作')])
    device_ids = StringField('设备ID', validators=[
        DataRequired(message='请选择设备')
    ])
    submit = SubmitField('执行')
    
    def validate_device_ids(self, device_ids):
        """验证设备ID"""
        try:
            ids = [int(id.strip()) for id in device_ids.data.split(',') if id.strip()]
            if not ids:
                raise ValidationError('请选择至少一个设备')
            
            # 验证设备是否存在
            devices = Device.query.filter(Device.id.in_(ids)).all()
            if len(devices) != len(ids):
                raise ValidationError('选择的设备中有不存在的设备')
                
            self.device_ids.data = ids
        except ValueError:
            raise ValidationError('设备ID格式错误')

class DeviceImportForm(FlaskForm):
    """设备导入表单"""
    import_file = FileField('导入文件', validators=[
        DataRequired(message='请选择要导入的文件')
    ])
    import_type = SelectField('导入类型', choices=[
        ('csv', 'CSV文件'),
        ('json', 'JSON文件'),
        ('excel', 'Excel文件')
    ], validators=[DataRequired(message='请选择导入类型')])
    submit = SubmitField('导入')

class DeviceConnectionTestForm(FlaskForm):
    """设备连接测试表单"""
    device_id = SelectField('选择设备', coerce=int, validators=[
        DataRequired(message='请选择设备')
    ])
    test_type = SelectField('测试类型', choices=[
        ('ping', 'Ping测试'),
        ('ssh', 'SSH连接测试'),
        ('telnet', 'Telnet连接测试'),
        ('restconf', 'RESTCONF连接测试')
    ], validators=[DataRequired(message='请选择测试类型')])
    submit = SubmitField('开始测试')
    
    def __init__(self, *args, **kwargs):
        super(DeviceConnectionTestForm, self).__init__(*args, **kwargs)
        # 动态加载设备选项
        self.device_id.choices = [(device.id, f"{device.name} ({device.ip_address})") 
                                 for device in Device.query.filter_by(is_active=True).order_by(Device.name).all()]
