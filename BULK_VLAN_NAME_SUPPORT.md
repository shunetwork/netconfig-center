# 批量VLAN模板 - VLAN名称支持

## 功能说明

批量VLAN模板现已支持为每个VLAN指定自定义名称。

## 使用方式

### 输入格式

模板支持两种输入格式：

#### 格式1: 仅VLAN ID（自动命名）

```
100
200
300
```

**渲染结果**:
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

#### 格式2: VLAN ID + 自定义名称（推荐）

```
100:Sales
200:Engineering
300:Guest
```

**渲染结果**:
```
vlan 100
 name Sales
end
vlan 200
 name Engineering
end
vlan 300
 name Guest
end
```

#### 混合格式

```
100:Sales
200:Engineering
300
400:Management
```

**渲染结果**:
```
vlan 100
 name Sales
end
vlan 200
 name Engineering
end
vlan 300
 name VLAN_300
end
vlan 400
 name Management
end
```

## 模板内容

```jinja2
{% for line in vlans.strip().split("\n") %}
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
{% endfor %}
```

## 变量定义

```json
{
  "vlans": {
    "type": "textarea",
    "default": "100:Sales\n200:Engineering\n300:Guest",
    "description": "批量VLAN ID和名称，每行一个\n格式1: VLAN_ID (自动命名为VLAN_ID)\n格式2: VLAN_ID:VLAN_Name (指定名称)\n\n示例：\n100:Sales\n200:Engineering\n300:Guest\n400 (自动命名为VLAN_400)",
    "required": true
  }
}
```

## 使用示例

### 场景1: 创建部门VLAN

输入：
```
10:Management
20:HR
30:IT
40:Finance
50:Sales
```

### 场景2: 创建楼层VLAN

输入：
```
101:Floor1
102:Floor2
103:Floor3
```

### 场景3: 创建项目VLAN

输入：
```
200:ProjectA
201:ProjectB
202:ProjectC
```

## 测试

运行测试脚本验证功能：

```bash
python test_bulk_vlan_api.py
```

## 更新日志

- **2024-10-27**: 添加VLAN名称支持
  - 支持自定义VLAN名称
  - 支持自动命名（VLAN_ID格式）
  - 支持混合格式输入
  - 更新默认示例数据

