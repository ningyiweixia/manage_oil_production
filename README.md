# 采油二厂井下作业管理系统

后端基础工程采用 `FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL 15(JSONB) + Alembic`，已完成系统底层搭建和【上修项目池管理模块】。

## 项目结构

```text
manage_factory/
  app/
    api/
      deps.py
      v1/
        router.py
        endpoints/
          auth.py
          workover_project_pools.py
    core/
      config.py
      exceptions.py
      middleware.py
      security.py
      status_codes.py
    crud/
      workover_project_pool.py
    db/
      base.py
      seed.py
      session.py
    models/
      approval.py
      dictionary.py
      engineering.py
      rbac.py
      workover.py
    schemas/
      auth.py
      pagination.py
      response.py
      workover_project_pool.py
    services/
      audit_service.py
      auth_service.py
      dictionary_service.py
      notification_service.py
      workover_project_pool_excel.py
    utils/
      jsonb.py
  alembic/
    env.py
    versions/
      20260531_0001_init_core_tables.py
      20260602_0002_workover_project_pool_module.py
  main.py
  requirements.txt
```

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
net start postgresql-x64-15
alembic upgrade head
python -m app.db.seed
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

访问入口：

- 健康检查：`GET http://127.0.0.1:8000/health`
- Swagger：`http://127.0.0.1:8000/docs`
- 登录：`POST /api/v1/auth/login`

开发初始化账号：

```json
{"username": "admin", "password": "ChangeMe_123!"}
```

## 环境配置

`.env.example` 提供本地配置模板，实际运行使用 `.env`，不要提交 `.env`。

关键配置：

```env
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=manage_factory
JWT_SECRET_KEY=please-change-this-secret-in-production
```

## 统一接口规范

所有业务接口统一返回：

```json
{"code": 20000, "msg": "success", "data": {}}
```

业务码：

- `20000`：成功
- `40001`：参数错误
- `40100`：登录失效
- `40300`：越权访问
- `40900`：业务冲突

## 已实现模块

### 模块 1：系统总体底层搭建

- FastAPI 应用入口、配置加载、数据库 session。
- SQLAlchemy 2.0 ORM 基类、PostgreSQL 连接、Alembic 迁移框架。
- JWT 登录认证、全局鉴权中间件、RBAC 权限依赖。
- 统一响应体、全局异常处理。
- 核心表：用户、角色、权限、上修项目池、修井运行表、承包商运力、工程设计文档、审批日志。

### 模块 2：上修项目池管理

业务源头模块，路由前缀：

```text
/api/v1/workover-project-pools/
```

已实现能力：

- 基层单位录入井号、井名、层位、故障描述、属地单位、区块、措施 JSON、备注。
- 项目池管理员维护台账，支持单条新增、详情、修改、逻辑删除。
- 多条件筛选分页：区块、井号、审批状态、措施类型。
- JSONB 原生检索：`measures_jsonb @>`，不把全量数据加载进 Pandas。
- 选井提报：`PATCH /submit`，状态自动变为 `PENDING_GEOLOGY_VERIFY`。
- 提报、编辑、删除自动写入 `approval_log`，保存操作人、IP、前后数据快照。
- 提报后预留 WebSocket 待办推送地质所用户。
- Excel 导入导出：基于 Pandas 批量解析/导出，预留 Celery 异步入口。

主要接口：

```text
GET    /api/v1/workover-project-pools/              列表分页
GET    /api/v1/workover-project-pools/{id}          详情
POST   /api/v1/workover-project-pools/              新增
PUT    /api/v1/workover-project-pools/{id}          全量修改
PATCH  /api/v1/workover-project-pools/submit        一键提报
PATCH  /api/v1/workover-project-pools/{id}/status   审批状态变更
DELETE /api/v1/workover-project-pools/{id}          逻辑删除
POST   /api/v1/workover-project-pools/import        Excel导入
GET    /api/v1/workover-project-pools/export/all    Excel导出
```

## 数据库说明

`workover_project_pool` 关键字段：

- `well_no`：井号
- `well_name`：井名
- `layer`：层位
- `fault_description`：故障描述
- `territory_unit`：属地单位
- `block_name`：区块
- `report_unit`：基层单位
- `status`：业务状态
- `measures_jsonb`：JSONB 修井措施
- `remark`：备注
- `is_deleted`：逻辑删除标记

JSONB 示例：

```json
{
  "measures": [
    {
      "measure_type": "由数据字典维护",
      "process": "工艺名称",
      "construction_params": {"pump_depth": 1200},
      "duration_days": 3,
      "estimated_cost": 12000
    }
  ]
}
```

GIN 索引：

```sql
CREATE INDEX ix_workover_project_pool_measures_gin
ON workover_project_pool
USING gin (measures_jsonb);
```

注意：措施类型、井区等业务选项不得硬编码，应由 `data_dictionary` 维表维护。

## Alembic

```powershell
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "message"
```

当前迁移版本：

- `20260531_0001`：核心底层表
- `20260602_0002`：上修项目池管理模块

## 验证记录

已完成本地验证：

- `python -m compileall app main.py alembic`
- `alembic upgrade head`
- `python -m app.db.seed`
- `/health` 返回 `20000`
- 登录接口返回 JWT
- 新增项目池返回 `20000`
- 多条件分页查询返回 `20000`
- 一键提报后状态为 `PENDING_GEOLOGY_VERIFY`
- 数据库确认 `measures_jsonb` GIN 索引存在

## 安全说明

- `.env`、`.local/`、日志、虚拟环境、缓存文件已加入 `.gitignore`。
- 代码不使用裸 SQL 拼接业务查询。
- 禁止爬虫对接外部系统。
- 高危编辑/删除/提报写入审计日志。
