"""
配置模板模块表单
包含模板创建、编辑、变量管理等表单
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, ValidationError
from app.models import ConfigTemplate, TemplateCategory, TemplateVariable

class ConfigTemplateForm(FlaskForm):
    """配置模板表单"""
    name = StringField('模板名称', validators=[
        DataRequired(message='请输入模板名称'),
        Length(min=2, max=100, message='模板名称长度必须在2-100个字符之间')
    ])
    description = TextAreaField('描述', validators=[
        Length(max=500, message='描述长度不能超过500个字符')
    ])
    category = SelectField('分类', validators=[
        DataRequired(message='请选择模板分类')
    ])
    template_content = TextAreaField('模板内容', validators=[
        DataRequired(message='请输入模板内容'),
        Length(min=10, message='模板内容不能少于10个字符')
    ])
    version = StringField('版本', validators=[
        Length(max=20, message='版本长度不能超过20个字符')
    ], default='1.0')
    is_active = BooleanField('激活状态', default=True)
    submit = SubmitField('保存')
    
    def __init__(self, template=None, *args, **kwargs):
        super(ConfigTemplateForm, self).__init__(*args, **kwargs)
        
        # 动态加载分类选项
        categories = TemplateCategory.query.order_by(TemplateCategory.name).all()
        self.category.choices = [(cat.name, cat.name) for cat in categories]
        
        if template:
            self.name.data = template.name
            self.description.data = template.description
            self.category.data = template.category
            self.template_content.data = template.template_content
            self.version.data = template.version
            self.is_active.data = template.is_active
    
    def validate_name(self, name):
        """验证模板名称唯一性"""
        template = ConfigTemplate.query.filter_by(name=name.data).first()
        if template and (not hasattr(self, 'template') or template.id != self.template.id):
            raise ValidationError('模板名称已存在')
    
    def validate_template_content(self, template_content):
        """验证模板内容语法"""
        try:
            from jinja2 import Template
            Template(template_content.data)
        except Exception as e:
            raise ValidationError(f'模板语法错误: {str(e)}')

class TemplateVariableForm(FlaskForm):
    """模板变量表单"""
    name = StringField('变量名', validators=[
        DataRequired(message='请输入变量名'),
        Length(min=1, max=100, message='变量名长度必须在1-100个字符之间')
    ])
    var_type = SelectField('变量类型', choices=[
        ('string', '字符串'),
        ('integer', '整数'),
        ('boolean', '布尔值'),
        ('select', '选择列表')
    ], validators=[DataRequired(message='请选择变量类型')])
    description = TextAreaField('描述', validators=[
        Length(max=200, message='描述长度不能超过200个字符')
    ])
    default_value = StringField('默认值', validators=[
        Length(max=200, message='默认值长度不能超过200个字符')
    ])
    required = BooleanField('必需变量', default=True)
    options = TextAreaField('选项列表（JSON格式）', validators=[
        Length(max=500, message='选项列表长度不能超过500个字符')
    ])
    order = IntegerField('显示顺序', default=0)
    submit = SubmitField('保存')
    
    def __init__(self, variable=None, *args, **kwargs):
        super(TemplateVariableForm, self).__init__(*args, **kwargs)
        
        if variable:
            self.name.data = variable.name
            self.var_type.data = variable.var_type
            self.description.data = variable.description
            self.default_value.data = variable.default_value
            self.required.data = variable.required
            self.options.data = variable.options
            self.order.data = variable.order
    
    def validate_options(self, options):
        """验证选项列表JSON格式"""
        if self.var_type.data == 'select' and options.data:
            try:
                import json
                json.loads(options.data)
            except json.JSONDecodeError:
                raise ValidationError('选项列表必须是有效的JSON格式')

class TemplateCategoryForm(FlaskForm):
    """模板分类表单"""
    name = StringField('分类名称', validators=[
        DataRequired(message='请输入分类名称'),
        Length(min=2, max=50, message='分类名称长度必须在2-50个字符之间')
    ])
    description = TextAreaField('描述', validators=[
        Length(max=200, message='描述长度不能超过200个字符')
    ])
    icon = StringField('图标类名', validators=[
        Length(max=50, message='图标类名长度不能超过50个字符')
    ])
    color = StringField('颜色代码', validators=[
        Length(max=20, message='颜色代码长度不能超过20个字符')
    ])
    submit = SubmitField('保存')
    
    def __init__(self, category=None, *args, **kwargs):
        super(TemplateCategoryForm, self).__init__(*args, **kwargs)
        
        if category:
            self.name.data = category.name
            self.description.data = category.description
            self.icon.data = category.icon
            self.color.data = category.color
    
    def validate_name(self, name):
        """验证分类名称唯一性"""
        category = TemplateCategory.query.filter_by(name=name.data).first()
        if category and (not hasattr(self, 'category') or category.id != self.category.id):
            raise ValidationError('分类名称已存在')

class TemplateRenderForm(FlaskForm):
    """模板渲染表单"""
    template_id = HiddenField('模板ID', validators=[DataRequired()])
    variables = TextAreaField('变量值（JSON格式）', validators=[
        DataRequired(message='请输入变量值')
    ])
    submit = SubmitField('渲染模板')
    
    def validate_variables(self, variables):
        """验证变量值JSON格式"""
        try:
            import json
            json.loads(variables.data)
        except json.JSONDecodeError:
            raise ValidationError('变量值必须是有效的JSON格式')

class TemplateImportForm(FlaskForm):
    """模板导入表单"""
    import_file = StringField('导入文件内容', validators=[
        DataRequired(message='请输入要导入的模板内容')
    ])
    import_type = SelectField('导入类型', choices=[
        ('yaml', 'YAML格式'),
        ('json', 'JSON格式'),
        ('text', '文本格式')
    ], validators=[DataRequired(message='请选择导入类型')])
    category = SelectField('目标分类', validators=[
        DataRequired(message='请选择目标分类')
    ])
    submit = SubmitField('导入')
    
    def __init__(self, *args, **kwargs):
        super(TemplateImportForm, self).__init__(*args, **kwargs)
        
        # 动态加载分类选项
        categories = TemplateCategory.query.order_by(TemplateCategory.name).all()
        self.category.choices = [(cat.name, cat.name) for cat in categories]

class TemplateSearchForm(FlaskForm):
    """模板搜索表单"""
    keyword = StringField('关键词', validators=[
        Length(max=100, message='关键词长度不能超过100个字符')
    ])
    category = SelectField('分类', validators=[])
    is_active = SelectField('状态', choices=[
        ('', '全部'),
        ('true', '激活'),
        ('false', '未激活')
    ])
    submit = SubmitField('搜索')
    
    def __init__(self, *args, **kwargs):
        super(TemplateSearchForm, self).__init__(*args, **kwargs)
        
        # 动态加载分类选项
        categories = TemplateCategory.query.order_by(TemplateCategory.name).all()
        self.category.choices = [('', '全部分类')] + [(cat.name, cat.name) for cat in categories]
