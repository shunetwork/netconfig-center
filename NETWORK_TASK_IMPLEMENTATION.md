# 网络任务执行实现方案

## 功能需求

实现配置模板与任务管理的联动，支持：
1. 批量添加多个VLAN到多个设备
2. 添加前自动判断VLAN是否已存在
3. 已存在VLAN的设备自动跳过

## 实现步骤

### 1. 创建批量添加VLAN模板

#### 模板名称
批量添加VLAN模板

#### 模板内容 (Jinja2格式)
```
{% for vlan_id in vlans.split('\n') %}
{% set vlan_id = vlan_id.strip() %}
{% if vlan_id %}
vlan {{ vlan_id }}
 name VLAN_{{ vlan_id }}
end
{% endif %}
{% endfor %}
```

#### 模板变量定义
```json
{
  "vlans": {
    "type": "textarea",
    "default": "100\n200\n300",
    "description": "批量VLAN ID，每行一个ID\n\n示例：\n100\n200\n300",
    "required": true
  }
}
```

### 2. 任务执行流程

#### 步骤1: 渲染模板
使用Jinja2引擎渲染模板，将用户输入的VLAN ID替换到模板中。

#### 步骤2: 检查VLAN是否已存在
对每个设备执行 `show vlan id <vlan_id>` 命令，检查VLAN是否已存在。

#### 步骤3: 应用配置
- 如果VLAN不存在：应用配置
- 如果VLAN已存在：跳过该设备并记录日志

#### 步骤4: 保存结果
记录执行结果到数据库。

### 3. 代码实现要点

#### 3.1 VLAN检查函数
```python
def check_vlan_exists(device, vlan_id):
    """检查VLAN是否存在"""
    command = f"show vlan id {vlan_id}"
    result = execute_command_on_device(device, command)
    
    if result['success']:
        output = result['output'].lower()
        if f"vlan{vlan_id}" in output and "invalid" not in output:
            return True
    return False
```

#### 3.2 批量任务执行函数
```python
def execute_bulk_vlan_task(task):
    """执行批量VLAN添加任务"""
    import json
    from jinja2 import Template
    
    # 获取模板变量
    variables = json.loads(task.template_variables)
    vlans = variables['vlans'].split('\n')
    
    # 渲染模板
    template_content = task.template.content
    jinja2_template = Template(template_content)
    config_lines = jinja2_template.render(vlans=variables['vlans']).split('\n')
    
    results = []
    
    # 获取设备列表（可以是单个设备或多个设备）
    if task.device_id:
        devices = [Device.query.get(task.device_id)]
    else:
        # 如果不是指定设备，可以获取所有在线设备
        devices = Device.query.filter_by(is_active=True, status='online').all()
    
    for device in devices:
        device_result = {
            'device': device.name,
            'ip': device.ip_address,
            'vlans_added': [],
            'vlans_skipped': [],
            'errors': []
        }
        
        for vlan_id in vlans:
            vlan_id = vlan_id.strip()
            if not vlan_id:
                continue
            
            # 检查VLAN是否已存在
            if check_vlan_exists(device, vlan_id):
                device_result['vlans_skipped'].append(vlan_id)
                continue
            
            # 应用配置
            vlan_config = [
                f"vlan {vlan_id}",
                f" name VLAN_{vlan_id}",
                "end"
            ]
            
            result = apply_config_to_device(device, vlan_config)
            if result['success']:
                device_result['vlans_added'].append(vlan_id)
            else:
                device_result['errors'].append({
                    'vlan': vlan_id,
                    'error': result.get('error', 'Unknown error')
                })
        
        results.append(device_result)
    
    # 保存结果
    task.result = json.dumps(results)
    task.status = 'completed'
    db.session.commit()
    
    return results
```

### 4. API端点

#### 4.1 创建任务
**端点**: `POST /tasks/create`

**请求体**:
```json
{
  "name": "批量添加VLAN 100-300",
  "description": "在核心交换机上添加VLAN 100-300",
  "task_type": "config",
  "template_id": 29,
  "device_id": 1,
  "template_variables": {
    "vlans": "100\n200\n300"
  }
}
```

#### 4.2 执行任务
**端点**: `POST /api/tasks/<task_id>/execute`

**响应**:
```json
{
  "success": true,
  "message": "任务执行完成",
  "results": [
    {
      "device": "Core-Switch-01",
      "ip": "192.168.1.1",
      "vlans_added": ["100", "200"],
      "vlans_skipped": ["300"],
      "errors": []
    }
  ]
}
```

### 5. 前端界面改进

#### 5.1 任务列表显示
显示任务状态、执行时间、结果摘要等信息。

#### 5.2 任务详情页面
显示详细的执行结果，包括：
- 每个设备的处理结果
- 成功添加的VLAN
- 跳过的VLAN
- 错误信息

### 6. 数据库迁移

需要在 `init_db` 函数中创建Task表的定义。

## 使用示例

### 步骤1: 创建批量VLAN添加模板
1. 进入"配置模板"页面
2. 点击"添加模板"
3. 填写模板信息：
   - 名称：批量添加VLAN
   - 类型：配置模板
   - 内容：如上所示的Jinja2模板
   - 变量定义：如上所示的JSON格式

### 步骤2: 创建任务
1. 进入"任务管理"页面
2. 点击"创建任务"
3. 填写任务信息：
   - 任务名称：批量添加VLAN
   - 任务类型：配置应用
   - 选择设备
   - 选择模板
   - 输入VLAN列表（每行一个）

### 步骤3: 执行任务
1. 在任务列表中点击"执行"按钮
2. 系统自动：
   - 检查每个VLAN是否存在
   - 对不存在的VLAN应用配置
   - 跳过已存在的VLAN
   - 记录执行结果

## 注意事项

1. **权限控制**: 确保只有授权用户可以执行任务
2. **错误处理**: 妥善处理网络连接失败、命令执行失败等异常情况
3. **日志记录**: 详细记录任务执行的每个步骤
4. **回滚机制**: 对于关键配置，考虑提供回滚功能
5. **并发控制**: 如果支持同时执行多个任务，需要考虑设备连接的并发限制
