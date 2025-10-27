"""
配置模板相关数据模型
包含配置模板、模板变量、模板版本等
"""

from datetime import datetime
from app import db

class ConfigTemplate(db.Model):
    """配置模板模型"""
    __tablename__ = 'config_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False, index=True)  # 模板分类
    template_content = db.Column(db.Text, nullable=False)  # Jinja2模板内容
    version = db.Column(db.String(20), default='1.0')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    variables = db.relationship('TemplateVariable', backref='template', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='template', lazy='dynamic')
    
    def add_variable(self, name, var_type, description='', default_value='', required=True):
        """添加模板变量"""
        variable = TemplateVariable(
            name=name,
            var_type=var_type,
            description=description,
            default_value=default_value,
            required=required,
            template=self
        )
        db.session.add(variable)
        return variable
    
    def get_variables_dict(self):
        """获取模板变量字典"""
        variables = {}
        for var in self.variables:
            variables[var.name] = {
                'type': var.var_type,
                'description': var.description,
                'default': var.default_value,
                'required': var.required,
                'options': var.options
            }
        return variables
    
    def render_template(self, variables):
        """渲染模板"""
        try:
            from jinja2 import Template
            template = Template(self.template_content)
            return template.render(**variables)
        except Exception as e:
            raise ValueError(f"模板渲染失败: {str(e)}")
    
    def validate_variables(self, variables):
        """验证模板变量"""
        errors = []
        required_vars = {var.name for var in self.variables.filter_by(required=True)}
        provided_vars = set(variables.keys())
        
        # 检查必需变量
        missing_vars = required_vars - provided_vars
        if missing_vars:
            errors.append(f"缺少必需变量: {', '.join(missing_vars)}")
        
        # 检查变量类型
        for var in self.variables:
            if var.name in variables:
                value = variables[var.name]
                if var.var_type == 'integer' and not isinstance(value, int):
                    try:
                        int(value)
                    except ValueError:
                        errors.append(f"变量 {var.name} 必须是整数")
                elif var.var_type == 'boolean' and not isinstance(value, bool):
                    if str(value).lower() not in ['true', 'false', '1', '0']:
                        errors.append(f"变量 {var.name} 必须是布尔值")
        
        return errors
    
    def to_dict(self, include_content=False):
        """转换为字典格式"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'version': self.version,
            'is_active': self.is_active,
            'variables_count': self.variables.count(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_content:
            data['template_content'] = self.template_content
            data['variables'] = [var.to_dict() for var in self.variables]
        
        return data
    
    def __repr__(self):
        return f'<ConfigTemplate {self.name} v{self.version}>'

class TemplateVariable(db.Model):
    """模板变量模型"""
    __tablename__ = 'template_variables'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    var_type = db.Column(db.String(20), nullable=False)  # string, integer, boolean, select
    description = db.Column(db.Text)
    default_value = db.Column(db.Text)
    required = db.Column(db.Boolean, default=True)
    options = db.Column(db.Text)  # JSON格式存储选项（用于select类型）
    order = db.Column(db.Integer, default=0)  # 显示顺序
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 外键
    template_id = db.Column(db.Integer, db.ForeignKey('config_templates.id'), nullable=False)
    
    def get_options_list(self):
        """获取选项列表"""
        if not self.options:
            return []
        try:
            import json
            return json.loads(self.options)
        except:
            return []
    
    def set_options_list(self, options):
        """设置选项列表"""
        import json
        self.options = json.dumps(options) if options else None
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.var_type,
            'description': self.description,
            'default_value': self.default_value,
            'required': self.required,
            'options': self.get_options_list(),
            'order': self.order
        }
    
    def __repr__(self):
        return f'<TemplateVariable {self.name} ({self.var_type})>'

class TemplateCategory(db.Model):
    """模板分类模型"""
    __tablename__ = 'template_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # 图标类名
    color = db.Column(db.String(20))  # 颜色代码
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'templates_count': ConfigTemplate.query.filter_by(category=self.name).count(),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<TemplateCategory {self.name}>'

    @staticmethod
    def create_default_categories():
        """创建默认模板分类"""
        categories_data = [
            {
                'name': 'basic',
                'description': '基础配置',
                'icon': 'fas fa-cog',
                'color': '#007bff'
            },
            {
                'name': 'interface',
                'description': '接口配置',
                'icon': 'fas fa-network-wired',
                'color': '#28a745'
            },
            {
                'name': 'routing',
                'description': '路由配置',
                'icon': 'fas fa-route',
                'color': '#ffc107'
            },
            {
                'name': 'security',
                'description': '安全配置',
                'icon': 'fas fa-shield-alt',
                'color': '#dc3545'
            },
            {
                'name': 'vlan',
                'description': 'VLAN配置',
                'icon': 'fas fa-sitemap',
                'color': '#6f42c1'
            },
            {
                'name': 'acl',
                'description': 'ACL配置',
                'icon': 'fas fa-filter',
                'color': '#fd7e14'
            }
        ]
        
        for cat_data in categories_data:
            category = TemplateCategory.query.filter_by(name=cat_data['name']).first()
            if not category:
                category = TemplateCategory(**cat_data)
                db.session.add(category)
        
        db.session.commit()
