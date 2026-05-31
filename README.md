# 采油二厂井下作业管理系统 - 模块1底层搭建

## 目录结构

```text
manage_factory/
  app/
    api/
      deps.py
      v1/
        router.py
        endpoints/auth.py
    core/
      config.py
      exceptions.py
      middleware.py
      security.py
      status_codes.py
    db/
      base.py
      seed.py
      session.py
    models/
      approval.py
      engineering.py
      rbac.py
      workover.py
    schemas/
      auth.py
      response.py
    services/auth_service.py
  alembic/
    env.py
    script.py.mako
    versions/20260531_0001_init_core_tables.py
  .env
  .env.example
  alembic.ini
  docker-compose.yml
  main.py
  requirements.txt
```

## 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
net start postgresql-x64-15
alembic upgrade head
python -m app.db.seed
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问：

- 健康检查：`GET http://127.0.0.1:8000/health`
- OpenAPI：`http://127.0.0.1:8000/docs`
- 登录：`POST /api/v1/auth/login`

开发初始化账号：

```json
{"username": "admin", "password": "ChangeMe_123!"}
```

## Alembic命令

```bash
alembic revision --autogenerate -m "change message"
alembic upgrade head
alembic downgrade -1
```

## 已落实约束

- FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL 15 + Alembic。
- 所有 API 统一返回 `code/msg/data`，业务码限定为 `20000/40001/40100/40300/40900`。
- RBAC 模型包含用户、角色、权限和两张多对多中间表。
- 全局 JWT 鉴权中间件拦截非白名单接口，路由依赖提供权限校验。
- 核心业务表包含上修项目池、修井运行表、承包商运力、工程设计文档、审批日志。
- `workover_project_pool.workover_measures` 使用 PostgreSQL `JSONB`，并通过 `ix_workover_project_pool_measures_gin` 建立 GIN 索引。
- 审批日志记录操作人、IP、审批节点、前后数据快照，满足审计溯源基础要求。
- 代码未使用裸 SQL、爬虫或不安全明文密码存储。
