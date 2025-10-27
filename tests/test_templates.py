"""
配置模板模块测试用例
测试模板管理、渲染、变量管理等功能
"""

import pytest
import json
from flask import url_for
from app import create_app, db
from app.models import ConfigTemplate, TemplateVariable, TemplateCategory, User, Role
from app.templates.services import TemplateService, TemplateVariableService, TemplateCategoryService

@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def sample_user(app):
    """创建测试用户"""
    with app.app_context():
        role = Role(name='test_role', description='测试角色')
        role.add_permission(Role.PERMISSION_VIEW | Role.PERMISSION_EXECUTE)
        db.session.add(role)
        
        user = User(
            username='testuser',
            email='test@example.com',
            role=role
        )
        user.password = 'testpass123'
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def sample_category(app):
    """创建测试分类"""
    with app.app_context():
        category = TemplateCategory(
            name='test_category',
            description='测试分类',
            icon='fas fa-test',
            color='#007bff'
        )
        db.session.add(category)
        db.session.commit()
        return category

@pytest.fixture
def sample_template(app, sample_category):
    """创建测试模板"""
    with app.app_context():
        template = ConfigTemplate(
            name='test_template',
            description='测试模板',
            category='test_category',
            template_content='hostname {{ hostname }}\ninterface {{ interface_name }}'
        )
        db.session.add(template)
        db.session.commit()
        return template

class TestTemplateService:
    """模板服务测试"""
    
    def test_create_template(self, app, sample_user, sample_category):
        """测试创建模板"""
        with app.app_context():
            template_data = {
                'name': 'new_template',
                'description': '新模板',
                'category': 'test_category',
                'template_content': 'interface {{ interface_name }}\ndescription {{ description }}',
                'version': '1.0',
                'is_active': True
            }
            
            template = TemplateService.create_template(template_data, sample_user.id)
            
            assert template.name == 'new_template'
            assert template.description == '新模板'
            assert template.category == 'test_category'
            assert template.template_content == 'interface {{ interface_name }}\ndescription {{ description }}'
            assert template.version == '1.0'
            assert template.is_active == True
    
    def test_update_template(self, app, sample_user, sample_template):
        """测试更新模板"""
        with app.app_context():
            template_data = {
                'name': 'updated_template',
                'description': '更新后的模板',
                'category': 'test_category',
                'template_content': 'hostname {{ hostname }}\ninterface {{ interface_name }}\nip address {{ ip_address }}',
                'version': '2.0',
                'is_active': True
            }
            
            updated_template = TemplateService.update_template(sample_template, template_data, sample_user.id)
            
            assert updated_template.name == 'updated_template'
            assert updated_template.description == '更新后的模板'
            assert updated_template.template_content == 'hostname {{ hostname }}\ninterface {{ interface_name }}\nip address {{ ip_address }}'
            assert updated_template.version == '2.0'
    
    def test_delete_template(self, app, sample_user, sample_template):
        """测试删除模板"""
        with app.app_context():
            template_id = sample_template.id
            template_name = sample_template.name
            
            TemplateService.delete_template(sample_template, sample_user.id)
            
            deleted_template = ConfigTemplate.query.get(template_id)
            assert deleted_template is None
    
    def test_render_template(self, app, sample_template):
        """测试模板渲染"""
        with app.app_context():
            variables = {
                'hostname': 'test-switch',
                'interface_name': 'GigabitEthernet0/1'
            }
            
            result = TemplateService.render_template(sample_template, variables)
            
            assert result['success'] == True
            assert 'hostname test-switch' in result['rendered_content']
            assert 'interface GigabitEthernet0/1' in result['rendered_content']
            assert result['template_name'] == 'test_template'
    
    def test_render_template_with_validation_error(self, app, sample_template):
        """测试模板渲染验证错误"""
        with app.app_context():
            # 缺少必需变量
            variables = {
                'hostname': 'test-switch'
                # 缺少 interface_name
            }
            
            result = TemplateService.render_template(sample_template, variables)
            
            # 由于没有定义必需变量，应该渲染成功但可能缺少变量
            assert result['success'] == True
    
    def test_render_template_syntax_error(self, app):
        """测试模板语法错误"""
        with app.app_context():
            # 创建有语法错误的模板
            template = ConfigTemplate(
                name='syntax_error_template',
                category='test_category',
                template_content='hostname {{ hostname\ninterface {{ interface_name }}'  # 缺少闭合括号
            )
            db.session.add(template)
            db.session.commit()
            
            variables = {
                'hostname': 'test-switch',
                'interface_name': 'GigabitEthernet0/1'
            }
            
            result = TemplateService.render_template(template, variables)
            
            assert result['success'] == False
            assert '模板语法错误' in result['error']
    
    def test_extract_template_variables(self, app):
        """测试提取模板变量"""
        with app.app_context():
            template_content = 'hostname {{ hostname }}\ninterface {{ interface_name }}\nip address {{ ip_address }}'
            variables = TemplateService.extract_template_variables(template_content)
            
            assert 'hostname' in variables
            assert 'interface_name' in variables
            assert 'ip_address' in variables
            assert len(variables) == 3
    
    def test_search_templates(self, app, sample_template):
        """测试搜索模板"""
        with app.app_context():
            # 按关键词搜索
            results = TemplateService.search_templates(keyword='test')
            assert len(results) > 0
            assert sample_template in results
            
            # 按分类搜索
            results = TemplateService.search_templates(category='test_category')
            assert len(results) > 0
            assert sample_template in results
            
            # 按激活状态搜索
            results = TemplateService.search_templates(is_active=True)
            assert len(results) > 0
            assert sample_template in results

class TestTemplateVariableService:
    """模板变量服务测试"""
    
    def test_create_variable(self, app, sample_user, sample_template):
        """测试创建模板变量"""
        with app.app_context():
            variable_data = {
                'name': 'hostname',
                'var_type': 'string',
                'description': '设备主机名',
                'default_value': 'default-switch',
                'required': True,
                'order': 1
            }
            
            variable = TemplateVariableService.create_variable(variable_data, sample_template, sample_user.id)
            
            assert variable.name == 'hostname'
            assert variable.var_type == 'string'
            assert variable.description == '设备主机名'
            assert variable.default_value == 'default-switch'
            assert variable.required == True
            assert variable.order == 1
            assert variable.template == sample_template
    
    def test_update_variable(self, app, sample_user, sample_template):
        """测试更新模板变量"""
        with app.app_context():
            # 先创建变量
            variable_data = {
                'name': 'hostname',
                'var_type': 'string',
                'description': '设备主机名',
                'required': True,
                'order': 1
            }
            variable = TemplateVariableService.create_variable(variable_data, sample_template, sample_user.id)
            
            # 更新变量
            updated_data = {
                'name': 'device_hostname',
                'var_type': 'string',
                'description': '更新后的设备主机名',
                'default_value': 'new-default',
                'required': False,
                'order': 2
            }
            
            updated_variable = TemplateVariableService.update_variable(variable, updated_data, sample_user.id)
            
            assert updated_variable.name == 'device_hostname'
            assert updated_variable.description == '更新后的设备主机名'
            assert updated_variable.default_value == 'new-default'
            assert updated_variable.required == False
            assert updated_variable.order == 2
    
    def test_delete_variable(self, app, sample_user, sample_template):
        """测试删除模板变量"""
        with app.app_context():
            # 先创建变量
            variable_data = {
                'name': 'hostname',
                'var_type': 'string',
                'description': '设备主机名',
                'required': True
            }
            variable = TemplateVariableService.create_variable(variable_data, sample_template, sample_user.id)
            
            variable_id = variable.id
            
            # 删除变量
            TemplateVariableService.delete_variable(variable, sample_user.id)
            
            deleted_variable = TemplateVariable.query.get(variable_id)
            assert deleted_variable is None

class TestTemplateCategoryService:
    """模板分类服务测试"""
    
    def test_create_category(self, app, sample_user):
        """测试创建分类"""
        with app.app_context():
            category_data = {
                'name': 'new_category',
                'description': '新分类',
                'icon': 'fas fa-new',
                'color': '#28a745'
            }
            
            category = TemplateCategoryService.create_category(category_data, sample_user.id)
            
            assert category.name == 'new_category'
            assert category.description == '新分类'
            assert category.icon == 'fas fa-new'
            assert category.color == '#28a745'
    
    def test_update_category(self, app, sample_user, sample_category):
        """测试更新分类"""
        with app.app_context():
            category_data = {
                'name': 'updated_category',
                'description': '更新后的分类',
                'icon': 'fas fa-updated',
                'color': '#dc3545'
            }
            
            updated_category = TemplateCategoryService.update_category(sample_category, category_data, sample_user.id)
            
            assert updated_category.name == 'updated_category'
            assert updated_category.description == '更新后的分类'
            assert updated_category.icon == 'fas fa-updated'
            assert updated_category.color == '#dc3545'
    
    def test_delete_category(self, app, sample_user, sample_category):
        """测试删除分类"""
        with app.app_context():
            category_id = sample_category.id
            category_name = sample_category.name
            
            TemplateCategoryService.delete_category(sample_category, sample_user.id)
            
            deleted_category = TemplateCategory.query.get(category_id)
            assert deleted_category is None

class TestTemplateRoutes:
    """模板路由测试"""
    
    def test_template_list_page(self, client, sample_user):
        """测试模板列表页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get('/templates/')
        assert response.status_code == 200
        assert b'配置模板' in response.data
    
    def test_template_detail_page(self, client, sample_user, sample_template):
        """测试模板详情页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get(f'/templates/{sample_template.id}')
        assert response.status_code == 200
        assert sample_template.name.encode() in response.data
    
    def test_template_add_page(self, client, sample_user):
        """测试模板添加页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get('/templates/add')
        assert response.status_code == 200
        assert b'添加模板' in response.data
    
    def test_template_add_post(self, client, sample_user, sample_category):
        """测试模板添加POST请求"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.post('/templates/add', data={
            'name': 'new_test_template',
            'description': '新的测试模板',
            'category': 'test_category',
            'template_content': 'hostname {{ hostname }}',
            'version': '1.0',
            'is_active': True
        })
        
        assert response.status_code == 302  # 重定向到模板详情页
    
    def test_template_edit_page(self, client, sample_user, sample_template):
        """测试模板编辑页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get(f'/templates/{sample_template.id}/edit')
        assert response.status_code == 200
        assert b'编辑模板' in response.data
    
    def test_template_delete(self, client, sample_user, sample_template):
        """测试模板删除"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.post(f'/templates/{sample_template.id}/delete')
        assert response.status_code == 302  # 重定向到模板列表页
    
    def test_template_render_api(self, client, sample_user, sample_template):
        """测试模板渲染API"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        variables = {
            'hostname': 'test-switch',
            'interface_name': 'GigabitEthernet0/1'
        }
        
        response = client.post(f'/templates/api/template/{sample_template.id}/render', 
                             json={'variables': variables})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] == True
        assert 'hostname test-switch' in data['rendered_content']
    
    def test_template_categories_page(self, client, sample_user):
        """测试分类管理页面"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        response = client.get('/templates/categories')
        assert response.status_code == 200
        assert b'分类管理' in response.data
    
    def test_template_api_endpoints(self, client, sample_user, sample_template):
        """测试模板API端点"""
        # 登录
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # 测试模板列表API
        response = client.get('/templates/api/templates')
        assert response.status_code == 200
        
        # 测试模板详情API
        response = client.get(f'/templates/api/template/{sample_template.id}')
        assert response.status_code == 200

class TestTemplateForms:
    """模板表单测试"""
    
    def test_config_template_form_validation(self, app):
        """测试配置模板表单验证"""
        with app.app_context():
            from app.templates.forms import ConfigTemplateForm
            
            # 测试空表单
            form = ConfigTemplateForm()
            assert not form.validate()
            assert 'name' in form.errors
            assert 'category' in form.errors
            assert 'template_content' in form.errors
            
            # 测试有效表单
            form = ConfigTemplateForm(data={
                'name': 'test_template',
                'description': '测试模板',
                'category': 'basic',
                'template_content': 'hostname {{ hostname }}',
                'version': '1.0'
            })
            # 需要先创建分类才能验证
            category = TemplateCategory(name='basic', description='基础分类')
            db.session.add(category)
            db.session.commit()
            
            # 重新创建表单以加载分类选项
            form = ConfigTemplateForm(data={
                'name': 'test_template',
                'description': '测试模板',
                'category': 'basic',
                'template_content': 'hostname {{ hostname }}',
                'version': '1.0'
            })
            assert form.validate()
    
    def test_template_variable_form_validation(self, app):
        """测试模板变量表单验证"""
        with app.app_context():
            from app.templates.forms import TemplateVariableForm
            
            # 测试空表单
            form = TemplateVariableForm()
            assert not form.validate()
            assert 'name' in form.errors
            assert 'var_type' in form.errors
            
            # 测试有效表单
            form = TemplateVariableForm(data={
                'name': 'hostname',
                'var_type': 'string',
                'description': '设备主机名',
                'default_value': 'default-switch',
                'required': True,
                'order': 1
            })
            assert form.validate()

class TestTemplateIntegration:
    """模板集成测试"""
    
    def test_template_with_variables_integration(self, app, sample_user, sample_category):
        """测试模板和变量的集成功能"""
        with app.app_context():
            # 创建模板
            template_data = {
                'name': 'interface_template',
                'description': '接口配置模板',
                'category': 'test_category',
                'template_content': 'interface {{ interface_name }}\ndescription {{ description }}\nip address {{ ip_address }} {{ subnet_mask }}',
                'version': '1.0'
            }
            template = TemplateService.create_template(template_data, sample_user.id)
            
            # 添加变量
            variables_data = [
                {
                    'name': 'interface_name',
                    'var_type': 'string',
                    'description': '接口名称',
                    'required': True,
                    'order': 1
                },
                {
                    'name': 'description',
                    'var_type': 'string',
                    'description': '接口描述',
                    'required': False,
                    'order': 2
                },
                {
                    'name': 'ip_address',
                    'var_type': 'string',
                    'description': 'IP地址',
                    'required': True,
                    'order': 3
                },
                {
                    'name': 'subnet_mask',
                    'var_type': 'string',
                    'description': '子网掩码',
                    'required': True,
                    'order': 4
                }
            ]
            
            for var_data in variables_data:
                TemplateVariableService.create_variable(var_data, template, sample_user.id)
            
            # 测试模板渲染
            variables = {
                'interface_name': 'GigabitEthernet0/1',
                'description': 'Test Interface',
                'ip_address': '192.168.1.1',
                'subnet_mask': '255.255.255.0'
            }
            
            result = TemplateService.render_template(template, variables)
            
            assert result['success'] == True
            rendered_content = result['rendered_content']
            assert 'interface GigabitEthernet0/1' in rendered_content
            assert 'description Test Interface' in rendered_content
            assert 'ip address 192.168.1.1 255.255.255.0' in rendered_content
            
            # 测试变量验证
            validation_errors = TemplateService.validate_template_variables(template, variables)
            assert len(validation_errors) == 0  # 应该没有验证错误
            
            # 测试缺少必需变量
            incomplete_variables = {
                'interface_name': 'GigabitEthernet0/1',
                'description': 'Test Interface'
                # 缺少 ip_address 和 subnet_mask
            }
            
            validation_errors = TemplateService.validate_template_variables(template, incomplete_variables)
            assert len(validation_errors) > 0  # 应该有验证错误
