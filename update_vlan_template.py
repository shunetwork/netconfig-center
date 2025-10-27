#!/usr/bin/env python3
"""更新批量VLAN模板以支持VLAN名称"""

from modern_start import app, db, ConfigTemplate
from datetime import datetime

app.app_context().push()

# 查找现有的批量VLAN模板
template = ConfigTemplate.query.filter_by(name='批量添加VLAN模板').first()

if template:
    # 更新模板内容以支持VLAN名称
    template.content = '''{% for line in vlans.strip().split("\\n") %}
{% set line = line.strip() %}
{% if line %}
{% set parts = line.split(":") %}
{% if parts|length == 2 %}
{% set vlan_id = parts[0].strip() %}
{% set vlan_name = parts[1].strip() %}
vlan {{ vlan_id }}
 name {{ vlan_name }}
end
{% else %}
vlan {{ line }}
 name VLAN_{{ line }}
end
{% endif %}
{% endif %}
{% endfor %}'''
    
    # 更新变量定义
    template.variables = '''{"vlans": {"type": "textarea", "default": "100:Sales\\n200:Engineering\\n300:Guest", "description": "批量VLAN ID和名称，每行一个\\n格式1: VLAN_ID (自动命名为VLAN_ID)\\n格式2: VLAN_ID:VLAN_Name (指定名称)\\n\\n示例：\\n100:Sales\\n200:Engineering\\n300:Guest\\n400 (自动命名为VLAN_400)", "required": true}}'''
    
    template.description = '用于批量添加多个VLAN到网络设备，支持自定义VLAN名称'
    
    db.session.commit()
    print('模板已更新！')
    print(f'模板ID: {template.id}')
    print(f'模板内容预览:\n{template.content[:200]}...')
    print(f'\n变量定义:\n{template.variables}')
else:
    print('未找到批量VLAN模板')
