"""
配置模板服务模块
包含模板管理、渲染、验证等功能
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from jinja2 import Template, Environment, BaseLoader, TemplateSyntaxError, UndefinedError

from app.models import ConfigTemplate, TemplateVariable, TemplateCategory, AuditLog
from app import db

class TemplateService:
    """模板服务类"""
    
    @staticmethod
    def create_template(template_data: Dict[str, Any], user_id: int) -> ConfigTemplate:
        """
        创建配置模板
        
        Args:
            template_data: 模板数据
            user_id: 用户ID
            
        Returns:
            创建的模板对象
        """
        template = ConfigTemplate(
            name=template_data['name'],
            description=template_data.get('description'),
            category=template_data['category'],
            template_content=template_data['template_content'],
            version=template_data.get('version', '1.0'),
            is_active=template_data.get('is_active', True)
        )
        
        db.session.add(template)
        db.session.commit()
        
        # 记录创建日志
        AuditLog.log_action(
            user_id=user_id,
            action='create_config_template',
            resource_type='config_template',
            resource_id=template.id,
            resource_name=template.name,
            success=True,
            details={'category': template.category, 'version': template.version}
        )
        
        return template
    
    @staticmethod
    def update_template(template: ConfigTemplate, template_data: Dict[str, Any], user_id: int) -> ConfigTemplate:
        """
        更新配置模板
        
        Args:
            template: 模板对象
            template_data: 模板数据
            user_id: 用户ID
            
        Returns:
            更新的模板对象
        """
        # 保存原始数据用于日志
        original_data = {
            'name': template.name,
            'category': template.category,
            'version': template.version
        }
        
        template.name = template_data['name']
        template.description = template_data.get('description')
        template.category = template_data['category']
        template.template_content = template_data['template_content']
        template.version = template_data.get('version', '1.0')
        template.is_active = template_data.get('is_active', True)
        
        db.session.add(template)
        db.session.commit()
        
        # 记录更新日志
        AuditLog.log_action(
            user_id=user_id,
            action='update_config_template',
            resource_type='config_template',
            resource_id=template.id,
            resource_name=template.name,
            success=True,
            details={
                'original': original_data,
                'updated': {
                    'name': template.name,
                    'category': template.category,
                    'version': template.version
                }
            }
        )
        
        return template
    
    @staticmethod
    def delete_template(template: ConfigTemplate, user_id: int) -> None:
        """
        删除配置模板
        
        Args:
            template: 模板对象
            user_id: 用户ID
        """
        template_name = template.name
        template_id = template.id
        variables_count = template.variables.count()
        
        # 记录删除日志
        AuditLog.log_action(
            user_id=user_id,
            action='delete_config_template',
            resource_type='config_template',
            resource_id=template_id,
            resource_name=template_name,
            success=True,
            details={'variables_count': variables_count}
        )
        
        db.session.delete(template)
        db.session.commit()
    
    @staticmethod
    def render_template(template: ConfigTemplate, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        渲染模板
        
        Args:
            template: 模板对象
            variables: 变量字典
            
        Returns:
            渲染结果字典
        """
        try:
            # 验证变量
            validation_errors = TemplateService.validate_template_variables(template, variables)
            if validation_errors:
                return {
                    'success': False,
                    'error': '变量验证失败',
                    'validation_errors': validation_errors,
                    'rendered_content': None
                }
            
            # 渲染模板
            jinja_template = Template(template.template_content)
            rendered_content = jinja_template.render(**variables)
            
            return {
                'success': True,
                'rendered_content': rendered_content,
                'variables_used': list(variables.keys()),
                'template_name': template.name
            }
            
        except TemplateSyntaxError as e:
            return {
                'success': False,
                'error': f'模板语法错误: {str(e)}',
                'rendered_content': None
            }
        except UndefinedError as e:
            return {
                'success': False,
                'error': f'模板变量错误: {str(e)}',
                'rendered_content': None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'模板渲染失败: {str(e)}',
                'rendered_content': None
            }
    
    @staticmethod
    def validate_template_variables(template: ConfigTemplate, variables: Dict[str, Any]) -> List[str]:
        """
        验证模板变量
        
        Args:
            template: 模板对象
            variables: 变量字典
            
        Returns:
            验证错误列表
        """
        errors = []
        
        # 获取模板中定义的变量
        template_vars = TemplateService.extract_template_variables(template.template_content)
        required_vars = {var.name for var in template.variables.filter_by(required=True)}
        provided_vars = set(variables.keys())
        
        # 检查必需变量
        missing_vars = required_vars - provided_vars
        if missing_vars:
            errors.append(f"缺少必需变量: {', '.join(missing_vars)}")
        
        # 检查变量类型
        for var in template.variables:
            if var.name in variables:
                value = variables[var.name]
                type_error = TemplateService.validate_variable_type(var, value)
                if type_error:
                    errors.append(type_error)
        
        return errors
    
    @staticmethod
    def validate_variable_type(variable: TemplateVariable, value: Any) -> Optional[str]:
        """
        验证变量类型
        
        Args:
            variable: 变量对象
            value: 变量值
            
        Returns:
            错误信息或None
        """
        if variable.var_type == 'integer':
            try:
                int(value)
            except (ValueError, TypeError):
                return f"变量 {variable.name} 必须是整数"
        
        elif variable.var_type == 'boolean':
            if isinstance(value, bool):
                return None
            if isinstance(value, str):
                if value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    return f"变量 {variable.name} 必须是布尔值"
            else:
                return f"变量 {variable.name} 必须是布尔值"
        
        elif variable.var_type == 'select':
            options = variable.get_options_list()
            if options and value not in options:
                return f"变量 {variable.name} 的值不在允许的选项中"
        
        return None
    
    @staticmethod
    def extract_template_variables(template_content: str) -> List[str]:
        """
        从模板内容中提取变量名
        
        Args:
            template_content: 模板内容
            
        Returns:
            变量名列表
        """
        # 使用正则表达式提取变量
        variable_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
        matches = re.findall(variable_pattern, template_content)
        
        # 去重并排序
        return sorted(list(set(matches)))
    
    @staticmethod
    def generate_variable_form(template: ConfigTemplate) -> Dict[str, Any]:
        """
        生成变量表单配置
        
        Args:
            template: 模板对象
            
        Returns:
            表单配置字典
        """
        form_config = {
            'template_id': template.id,
            'template_name': template.name,
            'variables': []
        }
        
        # 按顺序排序变量
        variables = template.variables.order_by(TemplateVariable.order, TemplateVariable.name).all()
        
        for var in variables:
            var_config = {
                'name': var.name,
                'type': var.var_type,
                'label': var.name.replace('_', ' ').title(),
                'description': var.description,
                'required': var.required,
                'default_value': var.default_value,
                'order': var.order
            }
            
            if var.var_type == 'select':
                var_config['options'] = var.get_options_list()
            
            form_config['variables'].append(var_config)
        
        return form_config
    
    @staticmethod
    def search_templates(keyword: str = None, category: str = None, 
                        is_active: bool = None, limit: int = 20) -> List[ConfigTemplate]:
        """
        搜索模板
        
        Args:
            keyword: 关键词
            category: 分类
            is_active: 激活状态
            limit: 结果数量限制
            
        Returns:
            模板列表
        """
        query = ConfigTemplate.query
        
        if keyword:
            query = query.filter(
                ConfigTemplate.name.contains(keyword) |
                ConfigTemplate.description.contains(keyword) |
                ConfigTemplate.template_content.contains(keyword)
            )
        
        if category:
            query = query.filter_by(category=category)
        
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        
        return query.order_by(ConfigTemplate.name).limit(limit).all()
    
    @staticmethod
    def import_template_from_text(content: str, category: str, user_id: int) -> ConfigTemplate:
        """
        从文本导入模板
        
        Args:
            content: 模板内容
            category: 分类
            user_id: 用户ID
            
        Returns:
            导入的模板对象
        """
        # 尝试解析YAML格式
        try:
            import yaml
            data = yaml.safe_load(content)
            
            if isinstance(data, dict) and 'name' in data:
                template_data = {
                    'name': data['name'],
                    'description': data.get('description', ''),
                    'category': category,
                    'template_content': data.get('content', ''),
                    'version': data.get('version', '1.0')
                }
                
                return TemplateService.create_template(template_data, user_id)
        except:
            pass
        
        # 如果不是YAML格式，作为普通文本处理
        template_data = {
            'name': f'导入模板_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'description': '从文本导入的模板',
            'category': category,
            'template_content': content,
            'version': '1.0'
        }
        
        return TemplateService.create_template(template_data, user_id)

class TemplateVariableService:
    """模板变量服务类"""
    
    @staticmethod
    def create_variable(variable_data: Dict[str, Any], template: ConfigTemplate, user_id: int) -> TemplateVariable:
        """
        创建模板变量
        
        Args:
            variable_data: 变量数据
            template: 模板对象
            user_id: 用户ID
            
        Returns:
            创建的变量对象
        """
        variable = TemplateVariable(
            name=variable_data['name'],
            var_type=variable_data['var_type'],
            description=variable_data.get('description'),
            default_value=variable_data.get('default_value'),
            required=variable_data.get('required', True),
            options=variable_data.get('options'),
            order=variable_data.get('order', 0),
            template=template
        )
        
        db.session.add(variable)
        db.session.commit()
        
        # 记录创建日志
        AuditLog.log_action(
            user_id=user_id,
            action='create_template_variable',
            resource_type='template_variable',
            resource_id=variable.id,
            resource_name=variable.name,
            success=True,
            details={'template_name': template.name, 'var_type': variable.var_type}
        )
        
        return variable
    
    @staticmethod
    def update_variable(variable: TemplateVariable, variable_data: Dict[str, Any], user_id: int) -> TemplateVariable:
        """
        更新模板变量
        
        Args:
            variable: 变量对象
            variable_data: 变量数据
            user_id: 用户ID
            
        Returns:
            更新的变量对象
        """
        variable.name = variable_data['name']
        variable.var_type = variable_data['var_type']
        variable.description = variable_data.get('description')
        variable.default_value = variable_data.get('default_value')
        variable.required = variable_data.get('required', True)
        variable.options = variable_data.get('options')
        variable.order = variable_data.get('order', 0)
        
        db.session.add(variable)
        db.session.commit()
        
        return variable
    
    @staticmethod
    def delete_variable(variable: TemplateVariable, user_id: int) -> None:
        """
        删除模板变量
        
        Args:
            variable: 变量对象
            user_id: 用户ID
        """
        variable_name = variable.name
        variable_id = variable.id
        template_name = variable.template.name
        
        # 记录删除日志
        AuditLog.log_action(
            user_id=user_id,
            action='delete_template_variable',
            resource_type='template_variable',
            resource_id=variable_id,
            resource_name=variable_name,
            success=True,
            details={'template_name': template_name}
        )
        
        db.session.delete(variable)
        db.session.commit()

class TemplateCategoryService:
    """模板分类服务类"""
    
    @staticmethod
    def create_category(category_data: Dict[str, Any], user_id: int) -> TemplateCategory:
        """
        创建模板分类
        
        Args:
            category_data: 分类数据
            user_id: 用户ID
            
        Returns:
            创建的分类对象
        """
        category = TemplateCategory(
            name=category_data['name'],
            description=category_data.get('description'),
            icon=category_data.get('icon'),
            color=category_data.get('color')
        )
        
        db.session.add(category)
        db.session.commit()
        
        return category
    
    @staticmethod
    def update_category(category: TemplateCategory, category_data: Dict[str, Any], user_id: int) -> TemplateCategory:
        """
        更新模板分类
        
        Args:
            category: 分类对象
            category_data: 分类数据
            user_id: 用户ID
            
        Returns:
            更新的分类对象
        """
        category.name = category_data['name']
        category.description = category_data.get('description')
        category.icon = category_data.get('icon')
        category.color = category_data.get('color')
        
        db.session.add(category)
        db.session.commit()
        
        return category
    
    @staticmethod
    def delete_category(category: TemplateCategory, user_id: int) -> None:
        """
        删除模板分类
        
        Args:
            category: 分类对象
            user_id: 用户ID
        """
        category_name = category.name
        category_id = category.id
        templates_count = ConfigTemplate.query.filter_by(category=category.name).count()
        
        # 记录删除日志
        AuditLog.log_action(
            user_id=user_id,
            action='delete_template_category',
            resource_type='template_category',
            resource_id=category_id,
            resource_name=category_name,
            success=True,
            details={'templates_count': templates_count}
        )
        
        db.session.delete(category)
        db.session.commit()
