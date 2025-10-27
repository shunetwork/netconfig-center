#!/usr/bin/env python3
"""创建批量添加VLAN模板"""

from modern_start import app, db, ConfigTemplate
from datetime import datetime

app.app_context().push()

# 检查是否已存在
existing = ConfigTemplate.query.filter_by(name='批量添加VLAN模板').first()
if existing:
    print(f'模板已存在，ID: {existing.id}')
    # 更新现有模板
    existing.description = '用于批量添加多个VLAN到网络设备，支持VLAN存在检查'
    existing.content = '''{% for vlan_id in vlans.split("\\n") %}
{% set vlan_id = vlan_id.strip() %}
{% if vlan_id %}
vlan {{ vlan_id }}
 name VLAN_{{ vlan_id }}
end
{% endif %}
{% endfor %}'''
    existing.variables = '{"vlans": {"type": "textarea", "default": "100\\n200\\n300", "description": "批量VLAN ID，每行一个ID\\n\\n示例：\\n100\\n200\\n300", "required": true}}'
    existing.category = 'switching'
    existing.is_active = True
    db.session.commit()
    print('模板已更新')
else:
    # 创建新模板
    vlan_template = ConfigTemplate(
        name='批量添加VLAN模板',
        description='用于批量添加多个VLAN到网络设备，支持VLAN存在检查',
        content='''{% for vlan_id in vlans.split("\\n") %}
{% set vlan_id = vlan_id.strip() %}
{% if vlan_id %}
vlan {{ vlan_id }}
 name VLAN_{{ vlan_id }}
end
{% endif %}
{% endfor %}''',
        template_type='config',
        category='switching',
        variables='{"vlans": {"type": "textarea", "default": "100\\n200\\n300", "description": "批量VLAN ID，每行一个ID\\n\\n示例：\\n100\\n200\\n300", "required": true}}',
        is_active=True,
        created_at=datetime.now()
    )
    
    db.session.add(vlan_template)
    db.session.commit()
    print(f'批量添加VLAN模板创建成功，ID: {vlan_template.id}')

print(f'模板名称: {vlan_template.name}')
print(f'模板内容预览:')
print(vlan_template.content[:100] + '...')
