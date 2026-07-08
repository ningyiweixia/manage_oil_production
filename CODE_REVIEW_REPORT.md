# 代码审查报告

审查日期：2026-07-07  
审查范围：`agent.md`、`rules.md`，以及当前工作区未提交变更涉及的后端接口、CRUD、A5 同步、承包商派工、前端审批/A5 页面、Alembic 迁移与构建产物。

## 结论摘要

审查时发现 3 个需要优先处理的业务一致性问题，其中 2 个会影响审批与运力数据的可信度。工程设计模块删除方向在 `rules.md`、README、路由、模型和依赖中基本一致，但 `agent.md` 仍保留大量旧约束，会持续误导后续开发。

## 整改状态

2026-07-07 已按本报告完成整改：

- 普通项目编辑不再接受审批状态和核实字段，状态流转统一收敛到 `PATCH /status`。
- 审批通过必须提交本次核实字段，不再回退使用项目上已有的历史核实值。
- A5 状态回写只在工单离开占用态时释放承包商运力，避免重复终态回调加高 `available_count`。
- `agent.md`、`rules.md`、Prometheus 告警描述和 `/local_minio` 残留挂载已同步清理。
- 新增后端回归测试覆盖审批绕过、核实字段校验和 A5 运力释放幂等边界。

## 主要问题

### P1 - `PUT /workover-project-pools/{id}` 可绕过审批专用接口和新增核实校验

证据：

- `app/api/v1/endpoints/workover_project_pools.py:162` 的更新接口只要求 `workover_project_pool:update` 权限。
- `app/schemas/workover_project_pool.py:56` 的 `WorkoverProjectPoolUpdate` 仍包含 `status`。
- `app/crud/workover_project_pool.py:148` 到 `168` 直接执行状态流转，只调用 `_ensure_status_transition`，没有复用 `patch_project_status` 中的地质核实日产油、工艺井况结论、可上修确认校验。
- `app/crud/workover_project_pool.py:341` 到 `361` 的新校验只存在于 `PATCH /status` 路径。

影响：

有更新权限但没有审批权限的用户，可以通过 PUT 把项目从 `PENDING_PROCESS_VERIFY` 改到 `APPROVED`，绕过审批接口、审批动作语义和新增核实必填规则。审计日志也会记录为 `PROJECT_POOL_UPDATE` / `ApprovalAction.UPDATE`，而不是审批动作，审批链路可信度下降。

建议：

- 普通 PUT 不允许修改 `status`，将状态流转统一收敛到 `PATCH /status`。
- 若确实保留 PUT 改状态，必须复用 `patch_project_status` 的校验和审批日志语义，并要求审批权限。
- 增加测试：无审批权限但有更新权限时，PUT 不能推进到 `APPROVED`；缺少核实字段时，任何入口都不能审批通过。

### P1 - 核实字段可在创建/编辑阶段预填，审批时会被当作有效核实结论

证据：

- `app/schemas/workover_project_pool.py:43` 到 `45` 把 `geology_verified_daily_oil`、`process_well_condition`、`process_can_workover` 放在 `WorkoverProjectPoolBase`，因此创建和编辑都能写入这些审批核实字段。
- `frontend/src/views/ApprovalWorkbench.vue:152` 到 `154` 在项目创建/编辑表单中展示了“核实日产油 / 可上修 / 井况结论”。
- `frontend/src/views/ApprovalWorkbench.vue:529` 到 `531` 保存时会把整个 `projectForm` 提交给更新/创建接口。
- `app/crud/workover_project_pool.py:342` 到 `354` 在审批通过时，如果本次审批请求没有传字段，会回退使用项目上已有的核实字段。

影响：

基层录入或项目编辑人员可以提前写入“核实日产油”和“可上修”等审核结论；后续审批人即使没有重新录入，也可能因为已有值而通过校验。这削弱了“地质/生产核实”和“工艺核实”的职责边界，审批数据来源不清。

建议：

- 从 `WorkoverProjectPoolCreate` / 普通 `Update` 中移除审批核实字段，或在后端根据权限/状态禁止非审批动作写入。
- `patch_project_status` 对关键核实字段应优先要求本次审批请求显式提供，至少要记录核实字段的操作人和时间。
- 前端项目基础信息表单不要展示审批核实字段；只在审批弹窗中展示。

### P1 - 承包商 `available_count` 回补缺少幂等边界，A5 状态回写可能把可用队伍数加高

证据：

- 派工时 `app/crud/contractor.py:347` 到 `350` 按 `available_count -= 1` 扣减。
- 手动进度完成时 `app/crud/contractor.py:393` 到 `399` 直接 `available_count += 1`。
- A5 回写完成/退回/取消时 `app/services/a5_sync_service.py:174` 到 `190` 根据旧状态直接 `available_count += 1`。
- 当前模型只保存剩余 `available_count`，没有保存日报原始总队伍数或“该工单是否已释放运力”的幂等标记。

影响：

如果同一工单先手动完成释放运力，之后 A5 又回调取消/退回，或不同同步通道按不同终态重复释放，`available_count` 可能超过当天报备能力。调度员随后会看到不存在的可用队伍，造成超派。

建议：

- 增加幂等释放标记，或以工单状态迁移表明确“占用态 -> 非占用态”只释放一次。
- 保存 `reported_count` / `total_count` 作为上限，`available_count` 回补不得超过日报总量。
- 增加测试覆盖：DISPATCHED/WORKING -> FINISHED -> CANCELED、手动完成后 A5 回调完成/取消、重复回调等场景。

### P2 - `agent.md` 与当前代码及 `rules.md` 冲突，仍要求已删除的工程设计/FPM/MinIO能力

证据：

- `rules.md:6` 已改成“三个关键业务阶段”，但 `agent.md:12` 到 `17` 仍写“四个关键业务阶段”，包含“工程设计与系统协同”。
- `agent.md:28` 到 `29` 仍要求 `python-docx` 和 MinIO；但 `requirements.txt` 已移除 `python-docx`、`minio`。
- `agent.md:56` 仍要求 `fpm_client.py`；但该文件已删除。
- `agent.md:68`、`agent.md:167`、`agent.md:206` 到 `224` 仍描述 `engineering_design_doc`、`/engineering-designs/`、规则引擎、FPM、MinIO 归档。

影响：

后续开发者或 AI Agent 会根据 `agent.md` 误判工程设计模块仍是核心红线，可能恢复已删除依赖、生成不存在接口，或在审查中把当前删除当成缺陷。当前文档源之间的冲突也会降低交付验收标准的一致性。

建议：

- 将 `agent.md` 同步到三阶段业务闭环。
- 删除或标注归档工程设计/FPM/MinIO章节。
- 如工程设计只是暂时下线，应在文档中明确“已下线/待重构/不在当前版本范围”，而不是继续作为必备能力。

### P3 - 已删除 MinIO 依赖后仍挂载 `/local_minio`

证据：

- `main.py:28` 仍挂载 `StaticFiles(directory="local_minio")`。
- `README.md`、`.env.example`、`requirements.txt` 已移除 MinIO/工程设计相关描述和依赖。

影响：

当前没有直接功能破坏，但它是残留入口。由于 `AuthMiddleware` 已取消 `/local_minio/` 白名单，这个静态挂载实际也不再承担原来的本地文档访问语义，容易造成维护困惑。

建议：

- 如果工程设计文档下线，移除 `/local_minio` 挂载。
- 如果仍需本地文件访问，补充新的业务说明和访问控制策略。

## 已验证事项

- 后端测试：`.venv/bin/python -m pytest -q` 通过，结果为 `5 passed, 1 warning`。
- 前端构建：`npm run build` 通过。
- Alembic 当前单头：`.venv/bin/alembic heads` 输出 `20260707_0012 (head)`。

## 其他观察

- A5 数据抓取仍通过 `A5Client` 和同步服务完成，未发现使用 WebScraping 的实现，符合 `rules.md` 红线。
- 派工入口仍保留 Redis `SET NX` 锁和 TTL，符合并发防重要求；主要风险在“释放运力”的幂等性，而不是派工锁缺失。
- 常规列表查询主要通过 SQLAlchemy 条件和分页下推数据库，未发现为普通列表查询滥用 Pandas 的问题。
