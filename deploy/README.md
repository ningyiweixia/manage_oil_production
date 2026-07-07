# 服务器容器化部署与监控体系

本目录用于采油二厂井下作业管理系统在企业内网环境的一键容器化部署，覆盖 DMZ 前端接入域、APP 应用逻辑域、DB 核心数据域和监控域。

## 目录

```text
deploy/
  docker/                 标准化 Python、Node、Nginx 镜像与业务镜像
  nginx/                  DMZ 反向代理、HTTPS、安全响应头、前端 SPA 配置
  prometheus/             Prometheus 采集配置与告警规则
  grafana/                Grafana 数据源与预设看板
  frontend-dist/          Vue3 dist 发布目录，当前含可运行占位页
  scripts/                一键部署脚本
```

## 三区域网络架构

| 区域 | Docker 网络 | 服务 | 暴露策略 |
| --- | --- | --- | --- |
| DMZ 前端接入域 | `manage_factory_dmz_net` | `nginx` | 仅暴露宿主机 `80/443`，负责 HTTPS、反向代理、限流、安全拦截 |
| APP 应用逻辑域 | `manage_factory_app_net` | `backend`、`frontend`、`prometheus`、`grafana` | `internal: true`，不向宿主机直接暴露 |
| DB 核心数据域 | `manage_factory_db_net` | `postgres`、`redis` | `internal: true`，禁止外部直接访问 |
| 监控采集域 | `manage_factory_monitor_net` | `cadvisor`、`node-exporter` | 仅 Prometheus 访问，用于容器和主机指标采集 |

## 端口说明

| 宿主端口 | 服务 | 说明 |
| --- | --- | --- |
| `80` | Nginx DMZ | HTTP 自动跳转 HTTPS |
| `443` | Nginx DMZ | 统一生产访问入口 |

内部端口不直接暴露：FastAPI `8000`、Vue 静态服务 `8080`、PostgreSQL `5432`、Redis `6379`、Prometheus `9090`、Grafana `3000`、Cadvisor `8080`、Node Exporter `9100`。

## 首次部署

1. 准备 Docker Engine 与 Docker Compose v2。
2. 将 `.env.example` 复制为 `.env`，修改所有口令和内网域名。
3. 将正式 TLS 证书放入 `deploy/nginx/ssl/server.crt` 与 `deploy/nginx/ssl/server.key`。未提供证书时脚本会生成自签证书，仅建议内网联调使用。
4. Windows 首次部署前，如果 Docker Desktop 提示 WSL2 或虚拟机平台不可用，请使用管理员 PowerShell 执行：

```powershell
.\deploy\scripts\enable-wsl2.ps1
Restart-Computer
```

5. 在 Windows PowerShell 执行：

```powershell
.\deploy\scripts\deploy.ps1
```

Linux 执行：

```sh
chmod +x deploy/scripts/deploy.sh
./deploy/scripts/deploy.sh
```

脚本会执行：创建目录、生成 TLS 证书、构建镜像、启动服务、执行 `alembic upgrade head`、执行 `python -m app.db.seed`。

## 企业内网离线镜像

无外网服务器应提前在联网环境拉取并保存镜像：

```sh
docker pull python:3.12-slim
docker pull nginx:1.27-alpine
docker pull postgres:15
docker pull redis:7.4-alpine
docker pull prom/prometheus:v3.3.0
docker pull grafana/grafana:12.0.0
docker pull gcr.io/cadvisor/cadvisor:v0.52.1
docker pull prom/node-exporter:v1.9.1
docker save -o manage_factory_images.tar python:3.12-slim nginx:1.27-alpine postgres:15 redis:7.4-alpine prom/prometheus:v3.3.0 grafana/grafana:12.0.0 gcr.io/cadvisor/cadvisor:v0.52.1 prom/node-exporter:v1.9.1
```

在内网服务器导入：

```sh
docker load -i manage_factory_images.tar
```

如果使用企业私有镜像仓库，在 `.env` 中把 `PYTHON_BASE_IMAGE`、`NGINX_BASE_IMAGE`、`POSTGRES_IMAGE` 等变量改为内网镜像地址。

## 前端 Vue3 发布

当前仓库没有 Vue3 源码目录，`frontend` 容器默认发布 `deploy/frontend-dist`。前端团队交付后执行：

```sh
npm ci
npm run build
cp -r dist/* deploy/frontend-dist/
docker compose up -d --build frontend nginx
```

Nginx 已配置 `try_files $uri $uri/ /index.html`，支持 Vue Router history 模式刷新。

## 监控与看板

Prometheus 采集目标：

- FastAPI `/metrics`
- Cadvisor 容器指标
- Node Exporter 主机 CPU、内存、磁盘、网络指标
- Grafana 自身指标
- Nginx DMZ 健康检查

Grafana 入口：`https://localhost/grafana/`

默认账号来自 `.env`：

```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=ChangeMe_Grafana_123456
```

预设看板：`Manage Factory Overview`，包含后端存活、主机 CPU、内存、API p95 延迟、容器 CPU。

告警规则文件：`deploy/prometheus/rules/manage_factory_alerts.yml`。企业微信或内网告警通道可接入 Alertmanager 后由 Prometheus 配置 `alerting` 节点扩展。

## 数据与日志持久化

| 类型 | 位置 |
| --- | --- |
| PostgreSQL | Docker volume `postgres_data` |
| Redis AOF/RDB | Docker volume `redis_data` |
| Prometheus TSDB | Docker volume `prometheus_data` |
| Grafana 配置数据 | Docker volume `grafana_data` |
| Nginx 日志 | `logs/nginx` |
| 后端日志目录 | `logs/backend` |
| PostgreSQL 日志目录 | `logs/postgres` |

容器删除不会删除业务数据卷。生产清理前必须先执行数据备份，禁止直接删除 named volumes。

## 安全规范

- 仅 DMZ Nginx 暴露宿主端口，APP/DB/监控网络均为内部网络。
- 后端、前端、Redis、PostgreSQL、Prometheus、Grafana 均指定非 root 用户或镜像内置低权限用户。
- 通用容器启用 `no-new-privileges`、`cap_drop: ALL`；DMZ Nginx 仅增加 `NET_BIND_SERVICE` 用于绑定 `80/443`。
- Nginx 启用 HTTPS、HSTS、安全响应头、方法白名单、API 限流、连接数限制。
- `.env` 不提交仓库，生产必须替换 JWT、数据库、Grafana 默认口令。
- DB 区服务不得通过 `ports` 暴露到宿主机。

## 常用运维命令

```sh
docker compose -f docker-compose.yml config
docker compose ps
docker compose logs -f nginx backend
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.db.seed
docker compose restart backend
docker compose down
```

仅当确认需要销毁全部数据时才可执行：

```sh
docker compose down -v
```
