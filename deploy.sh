#!/bin/bash

# NetManagerX部署脚本
# 用于自动化部署NetManagerX网络配置管理系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 命令未找到，请先安装 $1"
        exit 1
    fi
}

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖..."
    check_command docker
    check_command docker-compose
    
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p uploads
    mkdir -p logs
    mkdir -p backups
    mkdir -p static/uploads
    mkdir -p ssl
    mkdir -p monitoring
    
    log_success "目录创建完成"
}

# 生成SSL证书（自签名）
generate_ssl_cert() {
    log_info "生成SSL证书..."
    
    if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
        openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/C=CN/ST=Beijing/L=Beijing/O=NetManagerX/CN=localhost"
        log_success "SSL证书生成完成"
    else
        log_info "SSL证书已存在，跳过生成"
    fi
}

# 创建环境配置文件
create_env_file() {
    log_info "创建环境配置文件..."
    
    if [ ! -f .env ]; then
        cp env.example .env
        log_warning "请编辑.env文件，配置数据库密码、Redis密码等敏感信息"
    else
        log_info ".env文件已存在"
    fi
}

# 创建Prometheus配置文件
create_prometheus_config() {
    log_info "创建Prometheus配置文件..."
    
    cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'netmanagerx'
    static_configs:
      - targets: ['app:5000']
    metrics_path: '/metrics'
    scrape_interval: 5s
EOF
    
    log_success "Prometheus配置文件创建完成"
}

# 创建数据库初始化脚本
create_db_init_script() {
    log_info "创建数据库初始化脚本..."
    
    cat > init.sql << EOF
-- 创建数据库用户
CREATE USER netmanagerx WITH PASSWORD 'netmanagerx123';

-- 创建数据库
CREATE DATABASE netmanagerx OWNER netmanagerx;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE netmanagerx TO netmanagerx;

-- 设置数据库编码
ALTER DATABASE netmanagerx SET client_encoding TO 'UTF8';
ALTER DATABASE netmanagerx SET default_transaction_isolation TO 'read committed';
ALTER DATABASE netmanagerx SET timezone TO 'UTC';
EOF
    
    log_success "数据库初始化脚本创建完成"
}

# 构建和启动服务
build_and_start() {
    log_info "构建和启动服务..."
    
    # 停止现有服务
    docker-compose down
    
    # 构建镜像
    docker-compose build
    
    # 启动服务
    docker-compose up -d
    
    log_success "服务启动完成"
}

# 等待服务启动
wait_for_services() {
    log_info "等待服务启动..."
    
    # 等待数据库启动
    log_info "等待数据库启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T db pg_isready -U netmanagerx -d netmanagerx &> /dev/null; then
            log_success "数据库启动完成"
            break
        fi
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -eq 0 ]; then
        log_error "数据库启动超时"
        exit 1
    fi
    
    # 等待Redis启动
    log_info "等待Redis启动..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T redis redis-cli ping &> /dev/null; then
            log_success "Redis启动完成"
            break
        fi
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -eq 0 ]; then
        log_error "Redis启动超时"
        exit 1
    fi
    
    # 等待应用启动
    log_info "等待应用启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:5000/health &> /dev/null; then
            log_success "应用启动完成"
            break
        fi
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -eq 0 ]; then
        log_error "应用启动超时"
        exit 1
    fi
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."
    
    # 运行数据库迁移
    docker-compose exec app flask db upgrade
    
    # 初始化数据库
    docker-compose exec app flask init-db
    
    log_success "数据库初始化完成"
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo
    echo "=========================================="
    echo "NetManagerX部署信息"
    echo "=========================================="
    echo "Web界面: http://localhost"
    echo "API接口: http://localhost/api"
    echo "监控面板: http://localhost:9090"
    echo "数据库: localhost:5432"
    echo "Redis: localhost:6379"
    echo
    echo "默认管理员账户:"
    echo "用户名: admin"
    echo "密码: admin123"
    echo
    echo "管理命令:"
    echo "查看日志: docker-compose logs -f"
    echo "停止服务: docker-compose down"
    echo "重启服务: docker-compose restart"
    echo "=========================================="
}

# 主函数
main() {
    log_info "开始部署NetManagerX..."
    
    check_dependencies
    create_directories
    generate_ssl_cert
    create_env_file
    create_prometheus_config
    create_db_init_script
    build_and_start
    wait_for_services
    init_database
    show_deployment_info
    
    log_success "NetManagerX部署完成！"
}

# 脚本参数处理
case "${1:-}" in
    "stop")
        log_info "停止NetManagerX服务..."
        docker-compose down
        log_success "服务已停止"
        ;;
    "restart")
        log_info "重启NetManagerX服务..."
        docker-compose restart
        log_success "服务已重启"
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        docker-compose ps
        ;;
    "clean")
        log_info "清理NetManagerX..."
        docker-compose down -v
        docker system prune -f
        log_success "清理完成"
        ;;
    "help"|"-h"|"--help")
        echo "NetManagerX部署脚本"
        echo
        echo "用法: $0 [命令]"
        echo
        echo "命令:"
        echo "  (无参数)  部署NetManagerX"
        echo "  stop      停止服务"
        echo "  restart   重启服务"
        echo "  logs      查看日志"
        echo "  status    查看状态"
        echo "  clean     清理所有数据"
        echo "  help      显示帮助"
        ;;
    *)
        main
        ;;
esac
