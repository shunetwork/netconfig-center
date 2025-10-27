# 批量VLAN模板测试文档

## 模板信息

- **模板ID**: 29
- **模板名称**: 批量添加VLAN模板
- **模板类型**: 配置模板
- **分类**: 交换机配置

## 模板变量

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

## 测试步骤

### 1. 验证模板存在

访问 `http://localhost:5001/templates`，确认可以看到"批量添加VLAN模板"。

### 2. 测试API获取模板变量

运行测试脚本：
```bash
python test_bulk_vlan_api.py
```

预期输出：
```
=== 测试批量VLAN模板 ===

1. 登录系统...
登录成功！

2. 获取所有模板...
状态码: 200

3. 查找批量VLAN模板...

4. 获取模板ID 29 的变量定义...
状态码: 200
响应头 Content-Type: application/json
JSON响应:
{
  "success": true,
  "variables": [
    {
      "default": "100\n200\n300",
      "description": "批量VLAN ID，每行一个ID\n\n示例：\n100\n200\n300",
      "name": "vlans",
      "required": true,
      "type": "textarea"
    }
  ]
}

变量数量: 1
  变量名: vlans
  类型: textarea
  默认值: 100
200
300
  描述: 批量VLAN ID，每行一个ID

示例：
100
200
300
```

### 3. 测试创建任务

1. 访问 `http://localhost:5001/tasks/create`
2. 选择"批量添加VLAN模板"
3. 在"模板变量"区域会出现一个 `textarea` 输入框
4. 输入多个VLAN ID，每行一个，例如：
   ```
   100
   200
   300
   400
   ```

### 4. 验证模板渲染

模板内容：
```
{% for vlan_id in vlans.split("\n") %}
{% set vlan_id = vlan_id.strip() %}
{% if vlan_id %}
vlan {{ vlan_id }}
 name VLAN_{{ vlan_id }}
end
{% endif %}
{% endfor %}
```

输入 `vlans = "100\n200\n300"` 后，预期渲染结果：
```
vlan 100
 name VLAN_100
end
vlan 200
 name VLAN_200
end
vlan 300
 name VLAN_300
end
```

## API测试命令

### 直接使用curl测试

```bash
# 1. 登录获取session
curl -c cookies.txt -X POST http://localhost:5001/login \
  -d "username=admin&password=admin123"

# 2. 获取模板变量
curl -b cookies.txt http://localhost:5001/api/templates/29/variables

# 预期响应:
# {
#   "success": true,
#   "variables": [
#     {
#       "name": "vlans",
#       "type": "textarea",
#       "default": "100\n200\n300",
#       "description": "批量VLAN ID，每行一个ID\n\n示例：\n100\n200\n300",
#       "required": true
#     }
#   ]
# }
```

### 使用Python requests测试

```python
import requests
import json

BASE_URL = "http://localhost:5001"
session = requests.Session()

# 登录
session.post(f"{BASE_URL}/login", data={
    'username': 'admin',
    'password': 'admin123'
})

# 获取模板变量
response = session.get(f"{BASE_URL}/api/templates/29/variables")
data = response.json()
print(json.dumps(data, indent=2, ensure_ascii=False))
```

## 前端测试

### 在浏览器中测试

1. 访问 `http://localhost:5001/tasks/create`
2. 在"配置模板"下拉框中选择"批量添加VLAN模板"
3. 观察"模板变量"区域是否动态显示一个 `textarea` 输入框
4. `textarea` 应该显示：
   - 标签：`vlans`（带红色必填标记 `*`）
   - 描述：批量VLAN ID，每行一个ID\n\n示例：\n100\n200\n300
   - 默认值：100\n200\n300
   - 行数：5行

### 预期界面

```
模板变量
┌────────────────────────────────────────┐
│ vlans *                                │
│ 批量VLAN ID，每行一个ID                 │
│ 示例：100 200 300                       │
├────────────────────────────────────────┤
│ 100                                    │
│ 200                                    │
│ 300                                    │
│                                        │
│                                        │
└────────────────────────────────────────┘
```

## 功能验证清单

- [x] 模板已创建并存储在数据库中（ID: 29）
- [x] API `/api/templates/29/variables` 正常返回JSON数据
- [x] 变量类型正确识别为 `textarea`
- [x] 变量描述正确显示中文
- [x] 默认值正确传递多行数据
- [x] 前端JavaScript正确渲染textarea输入框
- [x] 模板内容使用Jinja2语法正确
- [ ] 任务执行时检查VLAN是否已存在（待实现）
- [ ] 应用配置到设备（待实现）

## 下一步实现

1. **实现VLAN存在检查功能**
   - 添加 `check_vlan_exists()` 函数
   - 在执行任务前检查每个VLAN

2. **实现任务执行**
   - 添加 `execute_bulk_vlan_task()` 函数
   - 支持跳过已存在的VLAN
   - 记录执行结果

3. **前端完善**
   - 任务列表显示
   - 任务详情页面
   - 执行结果展示

## 已知问题

1. 数据库中的中文在某些终端显示为乱码，但API返回正常
2. VLAN检查功能尚未实现
3. 任务执行逻辑尚未实现
