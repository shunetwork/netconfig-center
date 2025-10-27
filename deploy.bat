@echo off
REM NetManagerX部署脚本 (Windows版本)
REM 用于自动化部署NetManagerX网络配置管理系统

setlocal enabledelayedexpansion

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker未安装，请先安装Docker Desktop
    exit /b 1
)

REM 检查Docker Compose是否安装
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose未安装，请先安装Docker Compose
    exit /b 1
)

REM 检查Docker服务是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker服务未运行，请启动Docker Desktop
    exit /b 1
)

echo [INFO] 开始部署NetManagerX...

REM 创建必要的目录
echo [INFO] 创建必要的目录...
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
if not exist "static\uploads" mkdir static\uploads
if not exist "ssl" mkdir ssl
if not exist "monitoring" mkdir monitoring

REM 创建环境配置文件
echo [INFO] 创建环境配置文件...
if not exist ".env" (
    copy env.example .env
    echo [WARNING] 请编辑.env文件，配置数据库密码、Redis密码等敏感信息
)

REM 创建Prometheus配置文件
echo [INFO] 创建Prometheus配置文件...
(
echo global:
echo   scrape_interval: 15s
echo   evaluation_interval: 15s
echo.
echo rule_files:
echo   # - "first_rules.yml"
echo   # - "second_rules.yml"
echo.
echo scrape_configs:
echo   - job_name: 'prometheus'
echo     static_configs:
echo       - targets: ['localhost:9090']
echo.
echo   - job_name: 'netmanagerx'
echo     static_configs:
echo       - targets: ['app:5000']
echo     metrics_path: '/metrics'
echo     scrape_interval: 5s
) > monitoring\prometheus.yml

REM 创建数据库初始化脚本
echo [INFO] 创建数据库初始化脚本...
(
echo -- 创建数据库用户
echo CREATE USER netmanagerx WITH PASSWORD 'netmanagerx123';
echo.
echo -- 创建数据库
echo CREATE DATABASE netmanagerx OWNER netmanagerx;
echo.
echo -- 授权
echo GRANT ALL PRIVILEGES ON DATABASE netmanagerx TO netmanagerx;
echo.
echo -- 设置数据库编码
echo ALTER DATABASE netmanagerx SET client_encoding TO 'UTF8';
echo ALTER DATABASE netmanagerx SET default_transaction_isolation TO 'read committed';
echo ALTER DATABASE netmanagerx SET timezone TO 'UTC';
) > init.sql

REM 停止现有服务
echo [INFO] 停止现有服务...
docker-compose down

REM 构建镜像
echo [INFO] 构建镜像...
docker-compose build

REM 启动服务
echo [INFO] 启动服务...
docker-compose up -d

REM 等待服务启动
echo [INFO] 等待服务启动...
timeout /t 30 /nobreak >nul

REM 初始化数据库
echo [INFO] 初始化数据库...
docker-compose exec app flask db upgrade
docker-compose exec app flask init-db

echo.
echo [SUCCESS] 部署完成！
echo.
echo ==========================================
echo NetManagerX部署信息
echo ==========================================
echo Web界面: http://localhost
echo API接口: http://localhost/api
echo 监控面板: http://localhost:9090
echo 数据库: localhost:5432
echo Redis: localhost:6379
echo.
echo 默认管理员账户:
echo 用户名: admin
echo 密码: admin123
echo.
echo 管理命令:
echo 查看日志: docker-compose logs -f
echo 停止服务: docker-compose down
echo 重启服务: docker-compose restart
echo ==========================================

pause
