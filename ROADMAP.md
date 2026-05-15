# Super-Key 迭代路线图

> 版本：v1.0 | 创建日期：2026-05-15 | 与 DEVELOPMENT_DOC.md v2.0 对齐

---

## 一、路线总览

```
当前状态                         短期 (1-2周)                    中期 (1-2月)                    长期 (3-6月)
─────────────────────────────────────────────────────────────────────────────────────────────────────────
核心可用                    补齐基础设施                     生产加固                      生态扩展
┌──────────┐              ┌──────────┐                   ┌──────────┐                  ┌──────────┐
│ chat ✅   │              │ tests    │                   │ schema   │                  │ WS/实时   │
│ models ✅ │    ──────►   │ presets  │    ──────────►    │ ability  │    ─────────►   │ 多worker  │
│ admin ✅  │              │ rate lim │                   │ non-st   │                  │ 按需模型  │
│ api-keys✅│              │ requestId│                   │ retry    │                  │ 插件系统  │
└──────────┘              └──────────┘                   └──────────┘                  └──────────┘
```

---

## 二、短期目标（Sprint 1 — 1-2 周）

> 优先级：— 补齐基础设施保障

### S1.1 测试框架 ⭐ 最高优先

| 任务 | 文件 | 工时 |
|---|---|---|
| `tests/conftest.py` — pytest fixtures (async session, test DB) | 新建 | 2h |
| `tests/test_adapters/test_openai.py` — OpenAIAdaptor 单元测试 | 新建 | 3h |
| `tests/test_adapters/test_gemini.py` — GeminiAdaptor 格式转换测试 | 新建 | 3h |
| `tests/test_routers/test_relay.py` — /v1/* 集成测试 (mock 上游) | 新建 | 4h |
| `tests/test_routers/test_admin.py` — /admin/* 集成测试 | 新建 | 4h |

**目标**：核心路径测试覆盖 > 80%

### S1.2 预置数据 JSON 迁移

| 任务 | 文件 | 工时 |
|---|---|---|
| 创建 `data/presets/providers.json` | 新建 | 1h |
| 创建 `data/presets/model_classifications.json` | 新建 | 3h |
| 补充模型数据至 176 个（从 v1.0 文档的 5.4.1 节提取） | 修改 | 6h |
| 修改 `preset_service.py` 改为读取 JSON 文件 | 修改 | 2h |
| 保持启动自动加载逻辑不变 | 验证 | 1h |

**目标**：数据与代码分离，模型覆盖 176

### S1.3 性能快速修补

| 任务 | 说明 | 工时 |
|---|---|---|
| 渠道匹配从 `LIKE %model%` 迁移到 Ability 表 JOIN | 解决假匹配问题 | 4h |
| 非流式路径添加异常重试 | `relay_service.py` `_relay_non_stream` | 3h |
| SQLite WAL 模式开启 | `database.py` `engine.execution_options` | 0.5h |

---

## 三、中期目标（Sprint 2-3 — 1-2 月）

> 优先级：— 生产加固

### S3.1 Pydantic Schema 层

| 任务 | 说明 |
|---|---|
| 新建 `app/schemas/` 目录 | 8 个 Pydantic Schema 文件 |
| `openai_compat.py` | GeneralOpenAIRequest / GeneralOpenAIResponse |
| `provider.py` / `channel.py` / `model_classification.py` | CRUD Schema |
| `api_key.py` / `custom_model.py` | v2.0 新增 Schema |
| `admin.py` | 管理后台通用 Schema |
| 替换所有 `data: dict` 为 Pydantic 模型 | admin.py 全部端点 |

### S3.2 中间件补全

| 任务 | 说明 |
|---|---|
| `app/middleware/request_id.py` | UUID 注入 `request.state.request_id` |
| `app/middleware/rate_limit.py` | Token 级别频率限制 (读写 Redis/内存) |
| 全局中间件注册链调整 | CORS → RequestID → RateLimit → TokenAuth → RequestLog |

### S3.3 API 端点补全（13 个）

| 端点 | 说明 |
|---|---|
| `POST /v1/completions` | 旧版补全 |
| `POST /v1/images/edits` | 图片编辑 |
| `POST /v1/audio/translations` | 语音翻译 |
| `POST /v1/rerank` | 重排序 |
| `POST /v1/moderations` | 内容审核 |
| `GET /admin/stats/models` | 模型排行 |
| `GET /admin/stats/channels` | 渠道排行 |
| `GET /admin/providers/{id}` | 提供商详情 |
| `GET /admin/channels/{id}` | 渠道详情 |
| `GET/PUT /admin/channels/{id}/abilities` | 渠道能力管理 |
| `POST /admin/channels/auto-discover-models` | 模型发现 |
| `POST /admin/models/batch-import` | 批量导入 |
| `GET /admin/logs/{id}` + `DELETE /admin/logs/cleanup` | 日志完善 |

### S3.4 中继逻辑统一

| 任务 | 说明 |
|---|---|
| 抽取 `relay_image` / `relay_audio` / `relay_embedding` 到 `RelayService` | 从 router 层迁入 service 层 |
| 统一重试逻辑 (流式 + 非流式) | `RelayService._select_and_relay()` |
| 非流式路径添加 `_retry_with_next_channel` | 与流式对齐 |

### S3.5 工具抽取

| 任务 | 文件 |
|---|---|
| SSE 处理工具 | `app/utils/sse.py` — 从 relay_service 抽取 |
| 统一响应格式 | `app/utils/response.py` — `success_response` / `error_response` / `paginated_response` |
| 渠道匹配工具 | `app/utils/channel_matcher.py` — `match_models_from_string` / `build_ability_index` |

---

## 四、长期目标（Sprint 4+ — 3-6 月）

> 优先级：— 生态扩展

### L4.1 WebSocket 实时端点

| 任务 | 说明 |
|---|---|
| `GET /v1/realtime` | WebSocket 端点 |
| OpenAI Realtime API 适配 | 双向 WebRTC/WebSocket 代理 |
| Gemini Live API 适配 | 双向 WebSocket 代理 |

### L4.2 多 Worker 支持

| 问题 | 方案 |
|---|---|
| admin_sessions 不跨 worker 共享 | Redis / SQLite 持久化 session |
| SQLite 写锁瓶颈 | WAL 模式 + 连接池优化 / 切换到 PostgreSQL（可选） |
| Fernet 密钥缓存 | 每个 worker 独立缓存，无影响 |

### L4.3 自动熔断与健康检查

| 任务 | 说明 |
|---|---|
| 渠道 `auto_ban` 落地 | 连续失败 N 次后 `status=0` |
| 后台健康检查定时器 | 每分钟探测失败渠道，恢复后自动启用 |
| 渠道响应时间加权分发 | `weight = base_weight * (1 / response_time)` |

### L4.4 插件化适配器

| 任务 | 说明 |
|---|---|
| 适配器热加载 | 扫描 `adapters/` 目录自动注册 |
| 适配器配置界面 | admin 面板配置额外适配器参数 |
| 第三方适配器支持 | 用户自定义适配器 Python 文件上传 |

### L4.5 自定义模型"多渠道路由"模式落地

| 任务 | 说明 |
|---|---|
| `selection_mode == "multi"` | 通过 `CustomModelChannel` 表加权分发 |
| 前端 UI 补全 | 自定义模型编辑面板中多渠道路由配置 |
| 与 Distributor 集成 | `resolve_model → select_channel_multi()` |

---

## 五、技术优化策略

### 5.1 性能优化路线

```
当前  ──────►    S1.3   ──────►    S3.5   ──────►   L4.3
LIKE匹配        Ability        SSE工具          熔断+健康检查
N+1查询         JOIN            批量预加载        加权响应时间
                               非流式重试         SQLite WAL
```

### 5.2 安全加固路线

```
当前  ──────►    S1.2   ──────►    S3.2   ──────►   L4.2
API Key加密     salt配置化      RequestID        多Worker session
bcrypt密码      env变量        RateLimit         持久化session
全局异常兜底     JSON配置      日志脱敏/轮转      API Key审计
```

### 5.3 可维护性路线

```
当前  ──────►    S1.1   ──────►    S3.1   ──────►   L4.4
34个Py文件      tests/         schemas/          插件化适配器
无测试          核心覆盖80%    Pydantic校验       热加载
dict满天飞      回归保障       OpenAPI文档        第三方适配器
```

---

## 六、里程碑

| 里程碑 | 版本 | 核心指标 | 预计日期 |
|---|---|---|---|
| M1 — 基础设施 | v2.1 | 测试覆盖 > 80%、预置数据 JSON + 176 模型 | +2周 |
| M2 — 生产加固 | v2.2 | Schema 层完成、13 端点补齐、RateLimit | +6周 |
| M3 — 全量发布 | v3.0 | WebSocket、熔断、健康检查、插件系统 | +3月 |

---

## 七、技术与业务指标

| 指标 | 当前 | M1 | M2 | M3 |
|---|---|---|---|---|
| OpenAI 兼容端点 | 8/12 (67%) | 8/12 | 12/12 | 13/13(+WS) |
| Admin 端点 | 41 | 41 | 54 | 54 |
| 测试覆盖率 | 0% | >80% | >85% | >90% |
| 预置模型数 | 31 | 176 | 176 | 200+ |
| 预置提供商数 | 17 | 30 | 30 | 30 |
| 渠道匹配精度 | LIKE 模糊 | Ability JOIN | Ability JOIN | 同上 |
| 非流式重试 | ❌ | ✅ | ✅ | ✅ |
| Rate Limit | ❌ | ❌ | ✅ | ✅ |
| WebSocket | ❌ | ❌ | ❌ | ✅ |