# NetManagerX - 网络配置管理系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://docker.com)

NetManagerX是一个基于Flask的网络配置管理系统，专门设计用于管理Cisco网络设备的配置。系统提供了Web界面来管理设备、创建配置模板、执行网络命令和备份配置。

## 功能特性

### 🔐 认证与安全
- 用户登录认证和权限控制
- 角色基础访问控制（RBAC）
- 密码加密存储
- 操作审计日志

### 🌐 设备管理
- 支持SSH、Telnet、RESTCONF连接
- 设备信息CRUD操作
- 设备状态监控和连接测试
- 设备分组管理

### 📝 配置模板
- Jinja2模板引擎支持
- 模板变量管理和验证
- 模板分类和搜索
- 配置模板渲染和应用

### ⚡ 任务执行
- 异步任务处理（Celery）
- 单命令和批量命令执行
- 配置备份和恢复
- 任务状态跟踪和结果记录

### 🖥️ Web界面
- 基于AdminLTE的现代化界面
- 响应式设计，支持移动设备
- 实时状态更新
- 直观的操作界面

## 技术栈

- **后端框架**: Flask 2.3+
- **数据库**: PostgreSQL / SQLite
- **任务队列**: Celery + Redis
- **前端框架**: AdminLTE + Bootstrap
- **网络通信**: Netmiko + Paramiko
- **模板引擎**: Jinja2
- **容器化**: Docker + Docker Compose

## 快速开始

### 环境要求

- Python 3.9+
- Docker & Docker Compose
- Git

### 1. 克隆项目

```bash
git clone https://github.com/shunetwork/netconfig-center.git
cd netconfig-center
```

### 2. 使用Docker部署（推荐）

#### Linux/macOS

```bash
# 运行部署脚本
./deploy.sh

# 或者手动部署
docker-compose up -d
```

#### Windows

```cmd
# 运行部署脚本
deploy.bat

# 或者手动部署
docker-compose up -d
```

### 3. 手动部署

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp env.example .env
# 编辑.env文件，配置数据库连接等信息

# 初始化数据库
flask db upgrade
flask init-db

# 启动应用
python run.py
```

### 4. 访问系统

- Web界面: http://localhost
- API接口: http://localhost/api
- 监控面板: http://localhost:9090

**默认管理员账户:**
- 用户名: `admin`
- 密码: `admin123`

## 项目结构

```
netconfig-center/
├── app/                    # 应用主目录
│   ├── models/            # 数据模型
│   ├── auth/              # 认证模块
│   ├── devices/           # 设备管理
│   ├── communication/     # 通信模块
│   ├── templates/         # 模板管理
│   ├── tasks/             # 任务执行
│   ├── api/               # API接口
│   ├── errors/            # 错误处理
│   └── main/              # 主模块
├── tests/                 # 测试用例
├── migrations/            # 数据库迁移
├── static/                # 静态文件
├── templates/             # HTML模板
├── uploads/               # 上传文件
├── logs/                  # 日志文件
├── backups/               # 配置备份
├── docker-compose.yml     # Docker编排
├── Dockerfile            # Docker镜像
├── nginx.conf            # Nginx配置
├── requirements.txt      # Python依赖
└── README.md            # 项目文档
```

## 配置说明

### 环境变量

主要环境变量配置：

```bash
# Flask配置
FLASK_ENV=production
SECRET_KEY=your-secret-key

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/netmanagerx

# Redis配置
REDIS_URL=redis://localhost:6379/0

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 数据库配置

支持多种数据库：

- **SQLite**: 开发环境，轻量级
- **PostgreSQL**: 生产环境，高性能
- **MySQL**: 生产环境，兼容性好

### 网络设备配置

支持的设备类型：

- Cisco IOS/IOS-XE
- Cisco NX-OS
- Cisco ASA
- 其他支持SSH/Telnet的设备

## 使用指南

### 1. 添加设备

1. 登录系统后，进入"设备管理"页面
2. 点击"添加设备"按钮
3. 填写设备信息（IP地址、用户名、密码等）
4. 测试连接确保配置正确
5. 保存设备信息

### 2. 创建配置模板

1. 进入"配置模板"页面
2. 点击"添加模板"按钮
3. 填写模板信息（名称、描述、分类等）
4. 编写Jinja2模板内容
5. 定义模板变量
6. 保存模板

### 3. 执行网络命令

1. 进入"任务管理"页面
2. 点击"创建任务"按钮
3. 选择任务类型（单命令/批量命令/模板应用）
4. 选择目标设备
5. 配置命令或模板参数
6. 提交任务执行

### 4. 配置备份

1. 在设备管理页面选择设备
2. 点击"备份配置"按钮
3. 系统自动执行`show running-config`命令
4. 配置保存到备份目录
5. 可设置自动备份计划

## API文档

系统提供RESTful API接口：

### 认证接口

```http
POST /api/auth/login
POST /api/auth/logout
GET /api/auth/user
```

### 设备管理接口

```http
GET /api/devices
POST /api/devices
GET /api/devices/{id}
PUT /api/devices/{id}
DELETE /api/devices/{id}
POST /api/devices/{id}/test-connection
```

### 任务管理接口

```http
GET /api/tasks
POST /api/tasks
GET /api/tasks/{id}
POST /api/tasks/{id}/cancel
POST /api/tasks/{id}/retry
```

### 模板管理接口

```http
GET /api/templates
POST /api/templates
GET /api/templates/{id}
PUT /api/templates/{id}
DELETE /api/templates/{id}
POST /api/templates/{id}/render
```

## 开发指南

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/shunetwork/netconfig-center.git
cd netconfig-center

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp env.example .env
# 编辑.env文件

# 初始化数据库
flask db upgrade
flask init-db

# 启动开发服务器
python run.py
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/test_auth.py

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 代码规范

项目使用以下工具保持代码质量：

- **Black**: 代码格式化
- **Flake8**: 代码检查
- **isort**: 导入排序

```bash
# 格式化代码
black app/

# 检查代码
flake8 app/

# 排序导入
isort app/
```

## 部署指南

### Docker部署

1. **准备环境**
   ```bash
   # 确保Docker和Docker Compose已安装
   docker --version
   docker-compose --version
   ```

2. **配置环境**
   ```bash
   # 复制环境配置文件
   cp env.example .env
   
   # 编辑配置文件，设置生产环境参数
   nano .env
   ```

3. **启动服务**
   ```bash
   # 使用部署脚本
   ./deploy.sh
   
   # 或手动启动
   docker-compose up -d
   ```

4. **验证部署**
   ```bash
   # 检查服务状态
   docker-compose ps
   
   # 查看日志
   docker-compose logs -f
   ```

### 生产环境配置

1. **安全配置**
   - 修改默认密码
   - 配置HTTPS证书
   - 设置防火墙规则
   - 启用访问日志

2. **性能优化**
   - 配置数据库连接池
   - 启用Redis缓存
   - 设置负载均衡
   - 监控系统资源

3. **备份策略**
   - 数据库定期备份
   - 配置文件备份
   - 日志文件轮转
   - 灾难恢复计划

## 监控和日志

### 系统监控

- **Prometheus**: 指标收集和监控
- **Grafana**: 可视化监控面板
- **健康检查**: 自动服务状态检测

### 日志管理

- **应用日志**: 操作记录和错误日志
- **访问日志**: Nginx访问日志
- **审计日志**: 用户操作审计

### 告警配置

- 服务异常告警
- 资源使用告警
- 安全事件告警

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务状态
   - 验证连接参数
   - 检查网络连接

2. **Redis连接失败**
   - 检查Redis服务状态
   - 验证连接配置
   - 检查内存使用

3. **设备连接失败**
   - 验证设备网络连通性
   - 检查SSH/Telnet配置
   - 确认设备认证信息

### 日志查看

```bash
# 查看应用日志
docker-compose logs app

# 查看数据库日志
docker-compose logs db

# 查看Redis日志
docker-compose logs redis
```

### 性能调优

1. **数据库优化**
   - 调整连接池大小
   - 优化查询语句
   - 添加索引

2. **缓存优化**
   - 启用Redis缓存
   - 设置缓存策略
   - 监控缓存命中率

3. **网络优化**
   - 调整连接超时
   - 优化并发连接数
   - 启用连接复用

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

### 开发规范

- 遵循PEP 8代码规范
- 编写单元测试
- 更新文档
- 提交信息清晰明确

## 许可证

本项目采用MIT许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 联系方式

- 项目主页: https://github.com/shunetwork/netconfig-center
- 问题反馈: https://github.com/shunetwork/netconfig-center/issues
- 邮箱: shunetwork@example.com

## 更新日志

### v1.0.0 (2024-01-01)

- 初始版本发布
- 基础功能实现
- Docker部署支持
- 完整的测试覆盖

## 致谢

感谢以下开源项目的支持：

- [Flask](https://flask.palletsprojects.com/) - Web框架
- [AdminLTE](https://adminlte.io/) - 管理界面模板
- [Netmiko](https://github.com/ktbyers/netmiko) - 网络设备连接
- [Celery](https://celeryproject.org/) - 异步任务队列
- [Docker](https://www.docker.com/) - 容器化平台