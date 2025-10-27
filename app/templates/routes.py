"""
配置模板模块路由
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.templates import bp
from app.templates.forms import ConfigTemplateForm, TemplateVariableForm, TemplateCategoryForm, TemplateRenderForm, TemplateSearchForm
from app.templates.services import TemplateService, TemplateVariableService, TemplateCategoryService
from app.models import ConfigTemplate, TemplateCategory, TemplateVariable
from app import db

@bp.route('/')
@login_required
def index():
    """模板列表页面"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 搜索表单
    search_form = TemplateSearchForm()
    if request.method == 'GET':
        keyword = request.args.get('keyword', '').strip()
        category = request.args.get('category', '').strip()
        is_active = request.args.get('is_active', '').strip()
        
        # 构建查询
        query = ConfigTemplate.query
        
        if keyword:
            query = query.filter(
                ConfigTemplate.name.contains(keyword) |
                ConfigTemplate.description.contains(keyword)
            )
        
        if category:
            query = query.filter_by(category=category)
        
        if is_active:
            is_active_bool = is_active == 'true'
            query = query.filter_by(is_active=is_active_bool)
        
        templates = query.order_by(ConfigTemplate.name).paginate(
            page=page, per_page=per_page, error_out=False
        )
    else:
        templates = ConfigTemplate.query.order_by(ConfigTemplate.name).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    categories = TemplateCategory.query.order_by(TemplateCategory.name).all()
    return render_template('templates/index.html', 
                         templates=templates, 
                         categories=categories,
                         search_form=search_form)

@bp.route('/<int:template_id>')
@login_required
def detail(template_id):
    """模板详情页面"""
    template = ConfigTemplate.query.get_or_404(template_id)
    return render_template('templates/detail.html', template=template)

@bp.route('/api/templates')
@login_required
def api_templates():
    """API: 获取模板列表"""
    templates = ConfigTemplate.query.order_by(ConfigTemplate.name).all()
    return jsonify([template.to_dict() for template in templates])

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加模板"""
    form = ConfigTemplateForm()
    
    if form.validate_on_submit():
        try:
            template_data = {
                'name': form.name.data,
                'description': form.description.data,
                'category': form.category.data,
                'template_content': form.template_content.data,
                'version': form.version.data,
                'is_active': form.is_active.data
            }
            
            template = TemplateService.create_template(template_data, current_user.id)
            flash('模板添加成功', 'success')
            return redirect(url_for('templates.detail', template_id=template.id))
            
        except Exception as e:
            flash(f'模板添加失败: {str(e)}', 'error')
    
    return render_template('templates/form.html', form=form, title='添加模板')

@bp.route('/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(template_id):
    """编辑模板"""
    template = ConfigTemplate.query.get_or_404(template_id)
    form = ConfigTemplateForm(obj=template)
    form.template = template
    
    if form.validate_on_submit():
        try:
            template_data = {
                'name': form.name.data,
                'description': form.description.data,
                'category': form.category.data,
                'template_content': form.template_content.data,
                'version': form.version.data,
                'is_active': form.is_active.data
            }
            
            TemplateService.update_template(template, template_data, current_user.id)
            flash('模板更新成功', 'success')
            return redirect(url_for('templates.detail', template_id=template.id))
            
        except Exception as e:
            flash(f'模板更新失败: {str(e)}', 'error')
    
    return render_template('templates/form.html', form=form, title='编辑模板', template=template)

@bp.route('/<int:template_id>/delete', methods=['POST'])
@login_required
def delete(template_id):
    """删除模板"""
    template = ConfigTemplate.query.get_or_404(template_id)
    
    try:
        TemplateService.delete_template(template, current_user.id)
        flash('模板删除成功', 'success')
        return redirect(url_for('templates.index'))
    except Exception as e:
        flash(f'模板删除失败: {str(e)}', 'error')
        return redirect(url_for('templates.detail', template_id=template.id))

@bp.route('/<int:template_id>/render', methods=['GET', 'POST'])
@login_required
def render_template(template_id):
    """渲染模板"""
    template = ConfigTemplate.query.get_or_404(template_id)
    form = TemplateRenderForm()
    
    if request.method == 'POST':
        try:
            import json
            variables = json.loads(form.variables.data)
            
            result = TemplateService.render_template(template, variables)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except json.JSONDecodeError:
            return jsonify({
                'success': False,
                'error': '变量值JSON格式错误'
            }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # GET请求：显示渲染表单
    form_config = TemplateService.generate_variable_form(template)
    return render_template('templates/render.html', template=template, form_config=form_config)

@bp.route('/<int:template_id>/variables')
@login_required
def variables(template_id):
    """模板变量管理"""
    template = ConfigTemplate.query.get_or_404(template_id)
    variables = template.variables.order_by(TemplateVariable.order, TemplateVariable.name).all()
    
    return render_template('templates/variables.html', template=template, variables=variables)

@bp.route('/<int:template_id>/variables/add', methods=['GET', 'POST'])
@login_required
def add_variable(template_id):
    """添加模板变量"""
    template = ConfigTemplate.query.get_or_404(template_id)
    form = TemplateVariableForm()
    
    if form.validate_on_submit():
        try:
            variable_data = {
                'name': form.name.data,
                'var_type': form.var_type.data,
                'description': form.description.data,
                'default_value': form.default_value.data,
                'required': form.required.data,
                'options': form.options.data,
                'order': form.order.data
            }
            
            TemplateVariableService.create_variable(variable_data, template, current_user.id)
            flash('变量添加成功', 'success')
            return redirect(url_for('templates.variables', template_id=template.id))
            
        except Exception as e:
            flash(f'变量添加失败: {str(e)}', 'error')
    
    return render_template('templates/variable_form.html', form=form, title='添加变量', template=template)

@bp.route('/categories')
@login_required
def categories():
    """分类管理页面"""
    categories = TemplateCategory.query.order_by(TemplateCategory.name).all()
    return render_template('templates/categories.html', categories=categories)

@bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    """添加分类"""
    form = TemplateCategoryForm()
    
    if form.validate_on_submit():
        try:
            category_data = {
                'name': form.name.data,
                'description': form.description.data,
                'icon': form.icon.data,
                'color': form.color.data
            }
            
            TemplateCategoryService.create_category(category_data, current_user.id)
            flash('分类添加成功', 'success')
            return redirect(url_for('templates.categories'))
            
        except Exception as e:
            flash(f'分类添加失败: {str(e)}', 'error')
    
    return render_template('templates/category_form.html', form=form, title='添加分类')

@bp.route('/api/template/<int:template_id>')
@login_required
def api_template_detail(template_id):
    """API: 获取模板详情"""
    template = ConfigTemplate.query.get_or_404(template_id)
    return jsonify(template.to_dict(include_content=True))

@bp.route('/api/template/<int:template_id>/render', methods=['POST'])
@login_required
def api_render_template(template_id):
    """API: 渲染模板"""
    template = ConfigTemplate.query.get_or_404(template_id)
    data = request.get_json()
    
    if not data or 'variables' not in data:
        return jsonify({
            'success': False,
            'error': '缺少变量参数'
        }), 400
    
    try:
        result = TemplateService.render_template(template, data['variables'])
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
