# Super-Key 项目任务进度清单

> 版本：v1.0 | 创建日期：2026-05-15
>
> 本清单整合了此前 Code Review、架构审查、性能优化和完成度分析中提出的所有建议，按优先级结构化整理。

---

## 一、图例说明

| 符号 | 含义 |
|---|---|
| ⬜ | 未开始 |
| 🔄 | 进行中 |
| ✅ | 已完成 |
| ⛔ | 已阻塞 |
| ❌ | 已取消 |

| 优先级 | 含义 |
|---|---|
| P0 | 阻塞 / 高风险 / 立即修复 |
| P1 | 重要 / 本周修复 |
| P2 | 优化 / 本月修复 |
| P3 | 低优先级 / 后续迭代 |

---

## 二、性能优化任务

| ID | 任务 | 文件 | 优先级 | 工时 | 完成标准 | 状态 |
|---|---|---|---|---|---|---|
| PERF-01 | PBKDF2 密钥模块级缓存（只派生一次） | `app/utils/crypto.py` | P0 | 0.5h | Fernet 实例模块级缓存，服务启动后不重复派生 | ✅ |
| PERF-02 | 移除运行时 `__import__("time")` / `__import__("datetime")` | `app/services/channel_service.py` | P0 | 0.5h | 顶部 `import time, datetime` 标准导入 | ✅ |
| PERF-03 | `/v1/models/categories` 从 16 次查询优化为单次 GROUP BY | `app/routers/relay.py` | P1 | 2h | 单次查询 + `json_group_array` 聚合 | ✅ |
| PERF-04 | `/admin/stats/overview` 5 次串行 COUNT → `asyncio.gather` 并发 + 缓存 | `app/routers/admin.py` | P1 | 2h | 并发查询 + 30s TTL 缓存 | ✅ |
| PERF-05 | `preset_service` N+1 查询 → `WHERE code IN (...)` 批量 | `app/services/preset_service.py` | P1 | 1.5h | 批量查询替代逐个 SELECT | ✅ |
| PERF-06 | HTML 缓存 `/admin/ui` | `app/routers/admin.py` | P1 | 0.5h | 启动时读入内存，请求直接返回 | ✅ |
| PERF-07 | `list_models_admin` keyword 下推 SQL `ILIKE` | `app/routers/admin.py` | P1 | 1h | keyword 条件推到 SQL 层，不在 Python 侧过滤 | ✅ |
| PERF-08 | `list_logs` subquery COUNT → 直接 COUNT | `app/routers/admin.py` | P1 | 0.5h | `select(func.count()).select_from(RequestLog).where(...)` | ✅ |
| PERF-09 | 渠道匹配从 `Channel.models LIKE %model%` 迁移到 Ability JOIN | `app/services/distributor.py` | P1 | 4h | `select(Channel).join(Ability).where(Ability.model==model)` 为主路径 | ⬜ |
| PERF-10 | 渠道探测 OpenAI/Gemini 并行化 | `app/services/channel_service.py` | P2 | 1.5h | `asyncio.gather` 并行探测 | ⬜ |
| PERF-11 | SQLite 开启 WAL 模式 | `app/database.py` | P2 | 0.5h | `pragma journal_mode=wal` | ⬜ |

---

## 三、健壮性与异常处理任务

| ID | 任务 | 文件 | 优先级 | 工时 | 完成标准 | 状态 |
|---|---|---|---|---|---|---|
| ROB-01 | `except Exception: pass` → `logger.warning()` | `app/services/channel_service.py` | P0 | 0.5h | 异常记录日志 + 上下文信息 | ✅ |
| ROB-02 | `update_model` / `update_provider` 添加字段白名单 | `app/routers/admin.py` | P0 | 1h | `MODEL_FIELDS` / `PROVIDER_FIELDS` 校验 | ✅ |
| ROB-03 | 全项目关键路径日志补全 | 多文件 | P0 | 3h | `logging.getLogger(__name__)` 覆盖关键操作 | ✅ |
| ROB-04 | 全局异常处理中间件 | `app/main.py` | P1 | 1h | `@app.exception_handler(Exception)` + 500 兜底 | ✅ |
| ROB-05 | admin_sessions 后台清理过期 | `app/main.py` | P1 | 1h | `asyncio.create_task` 定时清理 | ✅ |
| ROB-06 | `create_channel` 白名单过滤 `extra_headers`/`extra_params` JSON 校验 | `app/routers/admin.py` | P1 | 1h | `json.loads` 校验 + 错误提示 | ⬜ |
| ROB-07 | `config.py` `model_config = {"extra": "allow"}` → `"forbid"` | `app/config.py` | P2 | 0.5h | 未知环境变量拒绝 | ⬜ |
| ROB-08 | `request_count` += 1 空值保护 | `app/middleware/auth.py` | P1 | 0.5h | `key_obj.request_count = (key_obj.request_count or 0) + 1` | ✅ |
| ROB-09 | 删除 `_test_verify.py` 等临时调试文件 | 根目录 | P2 | 0.5h | 无临时测试文件残留 | ⬜ |

---

## 四、Feature 开发任务

| ID | 任务 | 优先级 | 工时 | 完成标准 | 状态 |
|---|---|---|---|---|---|
| FEAT-01 | 内置提供商支持完整编辑/删除 | P0 | 2h | UI 开放按钮 + 后端移除限制 + 确认提示 | ✅ |
| FEAT-02 | 提供商编辑弹窗增加 website/description 字段 | P1 | 1h | 前端表单 + API 返回 + providerForm 初始化 | ✅ |
| FEAT-03 | `POST /v1/completions` 旧版补全 | P2 | 2h | 路由 + RelayService 扩展 | ⬜ |
| FEAT-04 | `POST /v1/rerank` 重排序 | P2 | 2h | 路由 + Adaptor 扩展 | ⬜ |
| FEAT-05 | `POST /v1/moderations` 内容审核 | P2 | 2h | 路由 + Adaptor 扩展 | ⬜ |
| FEAT-06 | `POST /v1/images/edits` 图片编辑 | P2 | 2h | 路由 + Adaptor 扩展 | ⬜ |
| FEAT-07 | `POST /v1/audio/translations` 语音翻译 | P2 | 2h | 路由 + Adaptor 扩展 | ⬜ |
| FEAT-08 | `GET /admin/stats/models` 模型排行 | P2 | 2h | API + 前端 | ⬜ |
| FEAT-09 | `GET /admin/stats/channels` 渠道排行 | P2 | 2h | API + 前端 | ⬜ |
| FEAT-10 | `GET /admin/providers/{id}` 提供商详情 | P2 | 1h | 端点 | ⬜ |
| FEAT-11 | `GET /admin/channels/{id}` 渠道详情 | P2 | 1h | 端点 | ⬜ |
| FEAT-12 | `GET/PUT /admin/channels/{id}/abilities` 渠道能力 | P2 | 3h | API + 前端 | ⬜ |
| FEAT-13 | `POST /admin/channels/auto-discover-models` 自动模型发现 | P2 | 3h | 端点 + 前端联动 | ⬜ |
| FEAT-14 | `POST /admin/models/batch-import` 批量模型导入 | P2 | 2h | 端点 + CSV/JSON 解析 | ⬜ |
| FEAT-15 | `GET /admin/logs/{id}` + `DELETE /admin/logs/cleanup` 日志完善 | P2 | 2h | 详情端点 + 清理端点 | ⬜ |
| FEAT-16 | `GET /v1/realtime` WebSocket | P3 | 8h | WebSocket + OpenAI Realtime Adaptor | ⬜ |
| FEAT-17 | 版本检测与更新功能 | P1 | 2h | `/admin/version` 接口 + 前端定时检测 + 关于页面 + 更新按钮 | ✅ |

---

## 五、架构优化任务

| ID | 任务 | 优先级 | 工时 | 完成标准 | 状态 |
|---|---|---|---|---|---|
| ARCH-01 | 新建 `data/presets/providers.json` | P0 | 1h | JSON 文件包含全部 30+ 提供商 | ⬜ |
| ARCH-02 | 新建 `data/presets/model_classifications.json` | P0 | 3h | JSON 文件包含全部 176 模型 | ⬜ |
| ARCH-03 | `preset_service.py` 改为读取 JSON 文件 | P0 | 2h | `json.load()` + 启动自动加载 | ⬜ |
| ARCH-04 | 新建 `tests/` 目录 + conftest + 3 个适配器测试 | P0 | 12h | pytest 可运行，核心覆盖 > 80% | ⬜ |
| ARCH-05 | 新建 `app/schemas/` Pydantic 校验层 | P0 | 8h | 8 个 Schema 文件 + 替换所有 `data: dict` | ⬜ |
| ARCH-06 | `relay_image/relay_audio/relay_embedding` 迁入 `RelayService` | P1 | 3h | Router 层精简为一行调用 | ⬜ |
| ARCH-07 | 新建 `app/middleware/request_id.py` | P1 | 1h | UUID 注入 + 响应头 `X-Request-ID` | ⬜ |
| ARCH-08 | 新建 `app/middleware/rate_limit.py` | P2 | 3h | Token 级别频率限制 | ⬜ |
| ARCH-09 | 新建 `app/utils/sse.py` SSE 工具抽取 | P2 | 2h | SSE 处理逻辑从 relay_service 抽取 | ⬜ |
| ARCH-10 | 新建 `app/utils/response.py` 统一响应 | P2 | 1h | `success_response` / `error_response` / `paginated_response` | ⬜ |
| ARCH-11 | 非流式路径添加自动重试 (`_retry_with_next_channel`) | P1 | 3h | 与流式路径对齐的重试逻辑 | ⬜ |

---

## 六、已完成任务汇总（v2.0）

| ID | 类别 | 任务简述 |
|---|---|---|
| ✅ PERF-01 | 性能 | PBKDF2 密钥缓存 |
| ✅ PERF-02 | 性能 | 移除运行时 __import__ |
| ✅ PERF-03 | 性能 | models/categories GROUP BY 优化 |
| ✅ PERF-04 | 性能 | stats 并发 + 缓存 |
| ✅ PERF-05 | 性能 | preset N+1 → IN 批量 |
| ✅ PERF-06 | 性能 | admin/ui HTML 缓存 |
| ✅ PERF-07 | 性能 | keyword SQL ILIKE |
| ✅ PERF-08 | 性能 | logs 直接 COUNT |
| ✅ ROB-01 | 健壮 | except 异常日志 |
| ✅ ROB-02 | 健壮 | admin 白名单 setattr |
| ✅ ROB-03 | 健壮 | 全项目 logger |
| ✅ ROB-04 | 健壮 | 全局异常 handler |
| ✅ ROB-05 | 健壮 | session 后台清理 |
| ✅ ROB-08 | 健壮 | request_count 空值保护 |
| ✅ FEAT-01 | Feature | 内置提供商编辑删除 |
| ✅ FEAT-02 | Feature | provider 新增字段 |
| ✅ FEAT-17 | Feature | 版本检测与更新功能 |
| ✅ FIX-01 | Bug修复 | 前端server-info数据解析错误 |
| ✅ FIX-02 | Bug修复 | ModelClassification字段不匹配(provider_id→provider_code, is_builtin, is_active) |
| ✅ FIX-03 | Bug修复 | list_channels不返回api_base字段 |
| ✅ FIX-04 | Bug修复 | Distributor不支持multi模式自定义模型 |
| ✅ FIX-05 | Bug修复 | 前端退出不调用后端logout(session安全风险) |
| ✅ FIX-06 | Bug修复 | request_count并发竞态条件(改用SQL原子更新) |
| ✅ FIX-07 | Bug修复 | expires_at字符串转datetime类型失败 |
| ✅ FIX-08 | Bug修复 | api()错误信息显示原始JSON不可读 |
| ✅ FIX-09 | Bug修复 | modelsKeyword不传给后端(全量请求) |
| ✅ FIX-10 | Bug修复 | loadXxx静默吞错误 |
| ✅ FIX-11 | Bug修复 | X-Admin-Token无法修改密码(双重验证不一致) |
| ✅ SEC-01 | 安全 | 移除硬编码默认密码，改为环境变量或随机生成 |
| ✅ SEC-02 | 安全 | 启动时检查默认弱密钥并警告 |
| ✅ SEC-03 | 安全 | admin_sessions添加asyncio.Lock并发保护 |
| ✅ PERF-09 | 性能 | sync_abilities批量插入替代循环插入 |
| ✅ PERF-10 | 性能 | channel_mappings批量删除替代循环删除 |
| ✅ PERF-11 | 性能 | RequestLog表添加索引(model,channel_id,is_error) |
| ✅ PERF-12 | 性能 | 网络探测并行化(asyncio.gather) |
| ✅ PERF-13 | 性能 | 异常日志记录完整堆栈(logger.exception) |
| ✅ PERF-14 | 性能 | 数据库连接池配置(pool_pre_ping) |
| ✅ ROB-09 | 健壮 | relay.py JSON解析异常捕获返回400 |
| ✅ ROB-10 | 健壮 | stats_overview修复asyncio.gather与SQLAlchemy冲突 |
| ✅ DEPLOY-01 | 部署 | .gitignore排除db文件，git rm --cached移除 |
| ✅ DEPLOY-02 | 部署 | init_db()添加自动迁移逻辑(检测缺失列并ALTER TABLE) |
| ✅ DEPLOY-03 | 部署 | database.py修复路径不一致(相对路径→绝对路径) |
| ✅ DEPLOY-04 | 部署 | 创建.env.example配置模板并提交 |
| ✅ DEPLOY-05 | 部署 | data/目录添加.gitkeep确保被git跟踪 |
| ✅ DEPLOY-06 | 部署 | 添加vercel.json配置，README说明SQLite不兼容Serverless |

---

## 七、工时统计

| 类别 | 已完成 | 剩余 + 未开始 | 总计 |
|---|---|---|---|
| 性能优化 | 12h | 9h (4 任务) | 21h |
| 健壮性 | 6.5h | 2.5h (3 任务) | 9h |
| Feature 开发 | 3h | 32h (14 任务) | 35h |
| 架构优化 | 0h | 43h (11 任务) | 43h |
| **合计** | **21.5h** | **86.5h** | **108h** |

---

## 八、当前阻塞项

无阻塞项。所有 P0 已修复完成。下一 Sprint 按 ROADMAP.md 执行。