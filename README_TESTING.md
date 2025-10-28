# NetManagerX 功能测试说明

## 概述

本文档说明如何使用自动化测试套件来验证 NetManagerX 系统的各项功能。

## 测试套件

### 1. 完整功能测试 (`test_all_functionality.py`)

这是一个综合测试套件，测试系统的主要功能模块：

- ✅ 服务健康检查
- ✅ 设备管理（添加、列表、状态检查）
- ✅ 模板管理（添加、列表、批量VLAN模板）
- ✅ 任务管理（列表、创建页面）

#### 运行方法

```bash
# 确保服务正在运行
python modern_start.py

# 在新终端运行测试
python test_all_functionality.py
```

#### 测试内容

1. **健康检查**
   - 验证服务是否正常运行

2. **设备管理测试**
   - 获取设备列表
   - 添加新设备
   - 检查设备状态
   - 获取设备API数据

3. **模板管理测试**
   - 获取模板列表
   - 添加新模板
   - 验证批量VLAN模板变量

4. **任务管理测试**
   - 获取任务列表
   - 创建任务页面

## 测试策略

### 新功能开发流程

1. **开发新功能前**
   ```bash
   python test_all_functionality.py
   ```
   确保所有现有测试通过

2. **开发新功能**
   - 实现功能代码
   - 更新 `modern_start.py` 或相关文件

3. **添加新测试**
   - 在 `test_all_functionality.py` 中添加对应的测试用例
   - 确保测试覆盖新功能的主要场景

4. **运行完整测试**
   ```bash
   python test_all_functionality.py
   ```
   验证新功能不影响现有功能

### 回归测试

每次更新代码后，都应该运行完整测试套件，确保：
- 新功能正常工作
- 现有功能未被破坏
- 数据持久化正常
- API接口正常

## 数据库初始化策略

系统已经优化为**不会删除现有数据**：

- ✅ 数据库文件会自动保留
- ✅ 只有新表会被创建
- ✅ 基础数据（如批量VLAN模板）会在需要时自动创建
- ✅ 已添加的设备和模板数据会保留

## 批量VLAN模板

系统会自动创建"批量添加VLAN模板"：

**模板变量格式：**
```
100:Sales
200:Engineering
300:Guest
400
```

**说明：**
- 格式1: `VLAN_ID:VLAN_Name` - 指定VLAN名称
- 格式2: `VLAN_ID` - 自动命名为 VLAN_ID

## 注意事项

1. **测试环境**
   - 测试会使用真实数据库，请在生产环境前备份数据
   - 建议在开发/测试环境运行测试

2. **服务状态**
   - 测试前确保 Flask 服务正在运行
   - 默认地址: http://localhost:5001

3. **登录凭证**
   - 默认管理员: admin / admin123
   - 测试脚本会自动登录

4. **数据保护**
   - 系统不会自动删除数据库文件
   - 如需重置数据库，手动删除 `modern_netmanagerx.db` 文件

## 故障排查

### 测试失败

1. 检查服务是否运行
   ```bash
   # Windows
   netstat -ano | findstr :5001
   
   # Linux/Mac
   netstat -ano | grep 5001
   ```

2. 检查服务健康状态
   ```bash
   curl http://localhost:5001/health
   ```

3. 查看服务日志
   - 检查 `modern_start.py` 的输出日志

### 常见问题

**问题**: 测试提示"无法登录"
- 检查默认用户是否存在
- 检查密码是否正确

**问题**: 批量VLAN模板未找到
- 首次运行时会自动创建
- 检查数据库文件是否存在

**问题**: 设备添加失败
- 检查设备名称或IP是否已存在
- 检查必填字段是否完整

## 测试报告示例

```
==================================================
NetManagerX Complete Functionality Test
==================================================
[OK] Login successful

========== Health Check ==========
[OK] Service health check passed

========== Device Management Test ==========
[OK] Device list retrieved successfully
[OK] Device added successfully
[OK] Device status check successful
[OK] Retrieved X devices

========== Template Management Test ==========
[OK] Template list retrieved successfully
[OK] Template added successfully
[OK] Bulk VLAN template variables verified

========== Task Management Test ==========
[OK] Task list retrieved successfully
[OK] Create task page loaded successfully

==================================================
[SUCCESS] All tests passed!
==================================================
```

## 持续集成建议

建议在以下场景自动运行测试：

1. 代码提交前（pre-commit hook）
2. Pull Request 创建时
3. 代码合并到主分支前
4. 定期自动化测试（如每天）

## 联系与支持

如有问题或建议，请：
- 查看服务日志
- 检查数据库状态
- 参考本文档的故障排查部分

