# Super-Key 项目开发文档

> **版本：v2.0** | 最后更新：2026-05-15 | 状态：开发中
>
> 本版本相比 v1.0 新增了多 API Key 管理、Admin 用户登录、自定义模型路由等模块，并调整了部分架构设计。

---

## 一、项目概述

### 1.1 项目名称
**Super-Key** — 个人自用大模型聚合平台

### 1.2 项目定位
聚合多个 AI 提供商的大模型 API，统一转换为自建的 OpenAI 兼容 API 接口。实现一处配置、多端调用，让个人用户以最简单的方式管理和使用多家 AI 服务。

### 1.3 核心目标
- **聚合多个提供商**：OpenAI、Anthropic、Google Gemini、DeepSeek、阿里(通义)、百度(文心)、字节(豆包/即梦)、智谱、月之暗面、MiniMax、硅基流动(SiliconFlow)、Groq 等 17 个内置提供商，支持自定义接入
- **多 API Key 管理**：支持创建多个 API Key，每个 Key 可独立设置模型访问权限、有效期、启用/禁用
- **自定义模型路由**：支持用户创建自定义模型别名，配置自动选择/指定渠道/多渠道路由模式
- **Admin 用户体系**：完整的登录/登出/session 管理/bcrypt 密码加密的管理员认证系统
- **设置简洁明了**：3 步完成渠道配置：选提供商 → 填 API Key → 完成
- **模型类型分类**：15 种精细分类维度，涵盖全模态、深度思考、文本/视觉/视频/图片/3D/语音/向量/实时等全场景

### 1.4 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Python 3.11+ / FastAPI | 高性能异步框架，原生 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 (async) + aiosqlite | 异步数据库操作 |
| 数据库 | SQLite | 个人使用零配置零维护 |
| HTTP 客户端 | httpx (async) | 异步请求上游 API |
| 配置管理 | Pydantic Settings | 类型安全的配置管理 |
| 前端 | 内嵌 Vue.js 3 CDN 单页应用 + Tailwind CSS | 轻量级管理面板 |
| 流式响应 | SSE (Server-Sent Events) | 兼容 OpenAI 流式格式 |
| API 规范 | 完全兼容 OpenAI API | 统一输出格式，对接所有上游 |
| 认证加密 | bcrypt + AES-256-GCM + PBKDF2 | 管理员密码 + API Key 加密 + 派生密钥 |
| 日志 | Python logging + 自定义结构化 | INFO 级操作日志 + ERROR 级异常日志 |

### 1.5 参考项目
参考 `G:\--------开发--------\开发中---的项目源码\2\api聚合` (new-api) 项目：
- 渠道 (Channel) → 适配器 (Adaptor) → 分发器 (Distributor) 三层架构
- 能力表 (Ability) 实现模型→渠道的灵活映射

### 1.6 v2.0 架构偏离说明（新增于实际开发中）

以下模块在原 v1.0 计划之外，于实际开发中追加：

| 新增模块 | 文件 | 设计动机 |
|---|---|---|
| 多 API Key 管理 | `models/api_key.py`, `services/api_key_service.py` | 原计划单一 Token，实际需要多 Key + 权限隔离 |
| Admin 用户系统 | `models/admin_user.py` | 从简单 Header Token 升级为 session + bcrypt 登录 |
| 自定义模型路由 | `models/custom_model.py`, `models/custom_model_channel.py`, `services/custom_model_service.py` | 用户需要自定义模型名 + 指定渠道映射 |
| 全局异常处理 | `main.py` | 生产环境兜底，避免 raw traceback 泄露 |
| Session 后台清理 | `main.py` | 防止 admin_sessions 内存泄漏 |
| `/v1/models/categories` | `routers/relay.py` | ChatBox/CherryStudio 等客户端依赖分类端点 |

以下模块当前偏离 v1.0 设计（已识别，纳入后续迭代）：

| 偏离项 | 当前状态 | 目标状态 |
|---|---|---|
| `app/schemas/` 目录 | 不存在，端点使用 `data: dict` | 新建 + Pydantic 校验 |
| 预置数据来源 | Python 硬编码（31 模型 / 17 提供商） | JSON 文件 + 176 模型 |
| `app/middleware/request_id.py` | 未实现 | 补充 |
| `app/middleware/rate_limit.py` | 未实现 | 补充 |
| `app/utils/sse.py` / `response.py` | 未实现 | 抽取工具模块 |
| 测试 | 完全缺失 | 新建 tests/ |
| 渠道匹配方式 | `Channel.models` 逗号分隔字段 LIKE 匹配为主，Ability 表为辅 | 全面迁移到 Ability 表 JOIN |

---

## 二、项目架构

### 2.1 总体架构图（v2.0）

```
┌─────────────────────────────────────────────────┐
│                    客户端                         │
│     (ChatBox / Cherry Studio / LobeChat / 自建)   │
└─────────────────────┬───────────────────────────┘
                      │ OpenAI 兼容 API (Bearer sk-xxx)
┌─────────────────────▼───────────────────────────┐
│              Super-Key API Server  (FastAPI)     │
│                                                  │
│  ┌─ 中间件层 ────────────────────────────────┐  │
│  │  CORS → TokenAuth(API Key多密钥)          │  │
│  │  → RequestLog(请求/响应记录)               │  │
│  │  → GlobalExceptionHandler(全局异常兜底)    │  │
│  ├────────────────────────────────────────────┤  │
│  │  路由层 (Routers)                           │  │
│  │  /v1/chat/completions  /v1/images/*        │  │
│  │  /v1/audio/*           /v1/embeddings      │  │
│  │  /v1/models            /v1/models/categories│  │
│  ├────────────────────────────────────────────┤  │
│  │  业务层 (Services)                          │  │
│  │  RelayService  Distributor  ChannelService  │  │
│  │  ApiKeyService  CustomModelService         │  │
│  ├────────────────────────────────────────────┤  │
│  │  适配器层 (Adapters)                        │  │
│  │  OpenAIAdaptor  GeminiAdaptor  ClaudeAdaptor│  │
│  │  CustomAdaptor                              │  │
│  ├────────────────────────────────────────────┤  │
│  │  数据层 (SQLAlchemy Models + SQLite)       │  │
│  │  Provider/Channel/Ability/ModelClass/       │  │
│  │  ApiKey/CustomModel/AdminUser/RequestLog    │  │
│  └────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────┘
                      │ httpx (async)
    ┌─────────────────┼─────────────────┬──────────┐
    ▼                 ▼                   ▼          ▼
┌───────┐      ┌──────────┐       ┌──────────┐ ┌───────┐
│OpenAI │      │  Gemini  │       │ DeepSeek │ │ 自定义 │...
└───────┘      └──────────┘       └──────────┘ └───────┘
```

### 2.2 核心请求处理流程（v2.0）

```
POST /v1/chat/completions  (Authorization: Bearer sk-xxx)
  │
  ├─ 1. CORS 中间件
  ├─ 2. TokenAuth 中间件
  │     └─ 查询 api_keys 表 → 验证 Bearer Token → 存入 request.state
  │     └─ request.state.allowed_models → API Key 权限模型列表
  ├─ 3. 路由处理器 chat_completions()
  │     ├─ 解析请求体 JSON
  │     ├─ 提取 model 字段
  │     ├─ 校验 allowed_models（非空则过滤）
  │     ├─ Distributor.resolve_model(model)
  │     │   ├─ 查 custom_models 表 → 匹配自定义模型
  │     │   ├─ selection_mode == "specific" → 返回 (目标模型, 渠道ID)
  │     │   ├─ selection_mode == "auto" → 返回 (目标模型, None)
  │     │   └─ 未匹配 → 返回 (原始model, None)
  │     ├─ Distributor.select_channel(actual_model, channel_id)
  │     │   ├─ 指定渠道 → 直接验证 channel.status==1
  │     │   ├─ 自动选择 → Channel.models LIKE %model% + status==1
  │     │   ├─ 按 priority(低值优先) + weight(加权随机) 选择
  │     │   ├─ Fallback: Ability 表 JOIN 查询
  │     │   └─ 无匹配 → ChannelNotFoundError → 404
  │     ├─ RelayService.relay_chat()
  │     │   ├─ decrypt_api_key(channel.api_key) → Fernet 解密
  │     │   ├─ AdaptorRegistry.get(channel.api_type) → 适配器
  │     │   ├─ stream=true:
  │     │   │   ├─ adaptor.build_request_url() + build_headers()
  │     │   │   ├─ adaptor.convert_chat_request() → 转换
  │     │   │   ├─ httpx.stream() → SSE 流式消费
  │     │   │   ├─ _retry_with_next_channel() → 失败重试
  │     │   │   └─ StreamingResponse → 返回
  │     │   └─ stream=false:
  │     │       ├─ httpx.post() → 完整响应
  │     │       ├─ adaptor.convert_chat_response() → 转换
  │     │       └─ JSONResponse → 返回
  │     └─ 返回响应
  ├─ 4. RequestLog 中间件 (after response)
  │     └─ 记录: request_id, channel_id, model, latency, tokens
  └─ 5. 全局异常处理 (兜底)
        └─ HTTPException → 原样返回 / Exception → 500
```

### 2.3 错误重试流程

```
请求失败 → 判断错误类型:
  ├─ 4xx (上游拒绝): 不重试, 直接返回错误给客户端
  ├─ 5xx / 超时 / 连接错误:
  │   ├─ 排除当前渠道
  │   ├─ 从剩余匹配渠道中重新选择
  │   ├─ 最多重试 max_retries 次 (默认3次)
  │   └─ 所有渠道失败 → 返回 502 Bad Gateway
  └─ 流式中途断开:
      └─ 尝试下一个渠道重试

注意：当前版本重试机制仅在流式路径(_retry_with_next_channel)中实现，
      非流式路径尚未实现自动重试。计划后续统一。
```

### 2.4 目录结构（v2.0 实际）

```
super-key/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口, 全局异常处理, Session 清理
│   ├── config.py                # Pydantic Settings 配置
│   ├── database.py              # SQLAlchemy async engine + session
│   │
│   ├── models/                  # SQLAlchemy ORM 模型 (9 个)
│   │   ├── __init__.py
│   │   ├── base.py              # 基类 (id, created_at, updated_at)
│   │   ├── provider.py          # Provider 提供商
│   │   ├── channel.py           # Channel 渠道
│   │   ├── ability.py           # Ability 能力映射 (模型↔渠道)
│   │   ├── model_classification.py  # ModelClassification 模型分类
│   │   ├── request_log.py       # RequestLog 请求日志
│   │   ├── system_config.py     # SystemConfig 系统配置
│   │   ├── api_key.py           # ApiKey 多 API Key (v2.0 新增)
│   │   ├── custom_model.py      # CustomModel 自定义模型 (v2.0 新增)
│   │   ├── custom_model_channel.py  # CustomModelChannel 关联表 (v2.0 新增)
│   │   └── admin_user.py        # AdminUser 管理员用户 (v2.0 新增)
│   │
│   ├── routers/                 # FastAPI Router
│   │   ├── __init__.py
│   │   ├── relay.py             # 核心中继路由 /v1/* (8 端点)
│   │   └── admin.py             # 管理后台路由 /admin/* (41 端点)
│   │
│   ├── services/                # 业务逻辑层 (8 个)
│   │   ├── __init__.py
│   │   ├── relay_service.py     # 中继核心服务 (chat 编排)
│   │   ├── distributor.py       # 渠道分发器 (含 resolve_model)
│   │   ├── channel_service.py   # 渠道管理 + 测试 + 自动配置
│   │   ├── provider_service.py  # 提供商管理
│   │   ├── preset_service.py    # 预置数据加载 (内嵌数据)
│   │   ├── api_key_service.py   # API Key 管理 (v2.0 新增)
│   │   └── custom_model_service.py  # 自定义模型服务 (v2.0 新增)
│   │
│   ├── adapters/                # 提供商适配器 (6 个)
│   │   ├── __init__.py          # Adaptor 注册 + 导出
│   │   ├── base.py              # BaseAdaptor 抽象基类
│   │   ├── openai.py            # OpenAI / 通用 OpenAI 兼容
│   │   ├── gemini.py            # Google Gemini
│   │   ├── claude.py            # Anthropic Claude
│   │   ├── custom.py            # 自定义/通用适配器
│   │   └── registry.py          # AdaptorRegistry 注册表
│   │
│   ├── middleware/              # FastAPI 中间件
│   │   ├── __init__.py
│   │   ├── auth.py              # Bearer Token 认证 + admin_sessions
│   │   └── request_log.py       # 请求日志记录
│   │
│   └── utils/                   # 工具模块
│       ├── __init__.py
│       ├── crypto.py            # AES-256-GCM + PBKDF2 加密
│       └── logger.py            # 结构化日志配置
│
├── data/
│   └── super_key.db             # SQLite 数据库 (自动生成)
│
├── static/
│   └── admin.html               # 管理面板 (Vue3 + Tailwind SPA)
│
├── requirements.txt
├── .env.example
├── run.py                       # 启动脚本: uvicorn app.main:app
├── DEVELOPMENT_DOC.md
├── ROADMAP.md                   # 迭代路线图 (v2.0 新增)
├── PROGRESS.md                  # 任务进度清单 (v2.0 新增)
├── WORKFLOW.md                  # 开发流程规范 (v2.0 新增)
└── .claude/
    └── settings.local.json
```

---

## 三、数据模型设计

### 3.0 数据库关系图 (ER — v2.0)

```
┌──────────┐       ┌──────────┐       ┌──────────────┐
│ Provider │ 1───N │ Channel  │ 1───N │   Ability    │
│          │       │          │       │ model↔channel │
└──────────┘       └──────────┘       └──────────────┘
                         │
                         │ 1───N (custom_models.channel_id)
                         ▼
                   ┌──────────────┐       ┌──────────────────────┐
                   │ CustomModel  │ 1───N │ CustomModelChannel   │
                   │ (自定义别名)  │       │ (多渠道路由映射)       │
                   └──────────────┘       └──────────────────────┘

┌────────────┐     ┌──────────────┐     ┌────────────────────┐
│  ApiKey    │     │ModelClassif- │     │SystemConfig        │
│ (多密钥)    │     │  ication     │     │   (KV 配置)        │
└────────────┘     └──────────────┘     └────────────────────┘

┌──────────┐       ┌──────────┐
│AdminUser │       │RequestLog│
│(管理登录)│       │(请求记录)│
└──────────┘       └──────────┘
```

### 3.1 提供商 (Provider) — `providers`

```python
class Provider(Base):
    __tablename__ = "providers"

    id: int       = Column(Integer, primary_key=True, autoincrement=True)
    name: str     = Column(String(100), nullable=False)
    code: str     = Column(String(50), unique=True, nullable=False)
    website: str  = Column(String(255), default="")
    description: str = Column(Text, default="")
    api_base: str = Column(String(255), default="")
    api_docs_url: str = Column(String(255), default="")
    logo_url: str = Column(String(255), default="")
    is_builtin: bool = Column(Boolean, default=True)
    is_active: bool  = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=func.now())
    updated_at: datetime = Column(DateTime, default=func.now(), onupdate=func.now())

    channels = relationship("Channel", back_populates="provider")
```

### 3.2 渠道 (Channel) — `channels`

```python
class Channel(Base):
    __tablename__ = "channels"

    id: int            = Column(Integer, primary_key=True, autoincrement=True)
    name: str          = Column(String(100), nullable=False)
    provider_id: int   = Column(Integer, ForeignKey("providers.id"), nullable=False)

    api_type: str      = Column(String(30), nullable=False)  # openai|gemini|claude|custom
    api_key: str       = Column(Text, nullable=False)        # 加密存储
    api_base: str      = Column(String(500), default="")
    api_version: str   = Column(String(50), default="")

    models: str        = Column(Text, default="")            # 逗号分隔模型列表
    model_mapping: str = Column(Text, default="")            # JSON 别名映射

    weight: int        = Column(Integer, default=1)
    priority: int      = Column(Integer, default=0)
    status: int        = Column(Integer, default=1)          # 1=启用 0=禁用
    auto_ban: int      = Column(Integer, default=1)

    enable_auto_complete: bool = Column(Boolean, default=False)

    extra_headers: str = Column(Text, default="")            # JSON
    extra_params: str  = Column(Text, default="")            # JSON
    param_override: str = Column(Text, default="")           # JSON

    timeout: int       = Column(Integer, default=60)
    max_retries: int   = Column(Integer, default=3)
    response_time: int = Column(Integer, default=0)
    total_requests: int = Column(Integer, default=0)
    failed_requests: int = Column(Integer, default=0)
    last_test_time: datetime = Column(DateTime, nullable=True)
    test_model: str    = Column(String(100), default="")
    remark: str        = Column(String(500), default="")

    created_at: datetime = Column(DateTime, default=func.now())
    updated_at: datetime = Column(DateTime, default=func.now(), onupdate=func.now())

    provider = relationship("Provider", back_populates="channels")
    abilities = relationship("Ability", back_populates="channel", cascade="all, delete-orphan")
    custom_models = relationship("CustomModel", back_populates="channel")
```

### 3.3 能力映射 (Ability) — `abilities`

```python
class Ability(Base):
    __tablename__ = "abilities"

    id: int         = Column(Integer, primary_key=True, autoincrement=True)
    channel_id: int = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    model: str      = Column(String(255), nullable=False, index=True)
    enabled: bool   = Column(Boolean, default=True)
    weight: int     = Column(Integer, default=1)
    priority: int   = Column(Integer, default=0)
    tag: str        = Column(String(100), default="")

    channel = relationship("Channel", back_populates="abilities")

    __table_args__ = (
        UniqueConstraint("channel_id", "model", name="uq_channel_model"),
    )
```

### 3.4 模型分类 (ModelClassification) — `model_classifications`

```python
class ModelClassification(Base):
    __tablename__ = "model_classifications"

    id: int        = Column(Integer, primary_key=True, autoincrement=True)
    model_id: str  = Column(String(255), unique=True, nullable=False)
    model_name: str = Column(String(255), nullable=False)
    provider_code: str = Column(String(50), nullable=False)
    category: str  = Column(String(50), nullable=False, index=True)

    description: str        = Column(Text, default="")
    context_window: int     = Column(Integer, default=0)
    max_output_tokens: int  = Column(Integer, default=0)
    pricing_input: float    = Column(Float, default=0.0)
    pricing_output: float   = Column(Float, default=0.0)
    is_free: bool           = Column(Boolean, default=False)
    supports_streaming: bool = Column(Boolean, default=True)
    supports_vision: bool   = Column(Boolean, default=False)
    supports_function_calling: bool = Column(Boolean, default=False)
    supports_tools: bool    = Column(Boolean, default=False)
    release_date: str       = Column(String(20), default="")
    is_deprecated: bool     = Column(Boolean, default=False)
    is_builtin: bool        = Column(Boolean, default=False)
    is_active: bool         = Column(Boolean, default=True)
    sort_order: int         = Column(Integer, default=0)
    created_at: datetime    = Column(DateTime, default=func.now())
    updated_at: datetime    = Column(DateTime, default=func.now(), onupdate=func.now())
```

15 种分类：`omni_modal`, `deep_thinking`, `text_generation`, `vision_understanding`, `video_generation`, `image_generation`, `3d_generation`, `speech_recognition`, `speech_synthesis`, `multimodal_embedding`, `text_embedding`, `realtime_omni`, `realtime_speech_synthesis`, `realtime_speech_recognition`, `realtime_speech_translation`

### 3.5 请求日志 (RequestLog) — `request_logs`

```python
class RequestLog(Base):
    __tablename__ = "request_logs"

    id: int            = Column(Integer, primary_key=True, autoincrement=True)
    request_id: str    = Column(String(36), index=True)
    token_hash: str    = Column(String(64), index=True)
    channel_id: int    = Column(Integer, default=0)
    model: str         = Column(String(255), default="")
    endpoint: str      = Column(String(255), default="")
    request_size: int  = Column(Integer, default=0)
    response_size: int = Column(Integer, default=0)
    status_code: int   = Column(Integer, default=0)
    latency_ms: int    = Column(Integer, default=0)
    input_tokens: int  = Column(Integer, default=0)
    output_tokens: int = Column(Integer, default=0)
    is_stream: bool    = Column(Boolean, default=False)
    is_error: bool     = Column(Boolean, default=False)
    error_type: str    = Column(String(100), default="")
    error_message: str = Column(Text, default="")
    created_at: datetime = Column(DateTime, default=func.now(), index=True)
```

### 3.6 系统配置 (SystemConfig) — `system_configs`

```python
class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: int            = Column(Integer, primary_key=True, autoincrement=True)
    key: str           = Column(String(100), unique=True, nullable=False)
    value: str         = Column(Text, default="")
    description: str   = Column(String(255), default="")
    updated_at: datetime = Column(DateTime, default=func.now(), onupdate=func.now())
```

### 3.7 API Key — `api_keys` （v2.0 新增）

```python
class ApiKey(Base):
    __tablename__ = "api_keys"

    id: int           = Column(Integer, primary_key=True, autoincrement=True)
    name: str         = Column(String(100), nullable=False)      # "ChatBox个人"
    key: str          = Column(String(64), unique=True, nullable=False)  # "sk-xxx"
    models: str       = Column(Text, default="")                 # 逗号分隔，空=全部
    is_active: bool   = Column(Boolean, default=True)
    expires_at: datetime = Column(DateTime, nullable=True)
    last_used_at: datetime = Column(DateTime, nullable=True)
    request_count: int = Column(Integer, default=0)
    remark: str       = Column(String(500), default="")
    created_at: datetime = Column(DateTime, default=func.now())
    updated_at: datetime = Column(DateTime, default=func.now(), onupdate=func.now())
```

**设计意图**：
- 替代原计划的单一 `SUPER_KEY_API_TOKEN`，支持多 Key
- 每个 Key 可限制允许的模型 (`models` 字段)
- `expires_at` 实现 Key 级别的过期管理
- `request_count` + `last_used_at` 实现使用统计

### 3.8 自定义模型 (CustomModel + CustomModelChannel) — `custom_models` / `custom_model_channels`（v2.0 新增）

```python
class CustomModel(Base):
    __tablename__ = "custom_models"

    id: int             = Column(Integer, primary_key=True, autoincrement=True)
    name: str           = Column(String(100), nullable=False)
    model_id: str       = Column(String(100), unique=True, nullable=False)
    description: str    = Column(Text, default="")

    selection_mode: str = Column(String(20), default="auto")    # "auto" | "specific" | "multi"
    target_model: str   = Column(String(100), default="")       # 实际路由模型
    channel_id: int     = Column(Integer, ForeignKey("channels.id"), nullable=True)
    channel_model: str  = Column(String(100), default="")

    is_active: bool     = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=func.now())
    updated_at: datetime = Column(DateTime, default=func.now(), onupdate=func.now())

    channel = relationship("Channel", back_populates="custom_models")
    channel_mappings = relationship("CustomModelChannel", back_populates="custom_model", cascade="all, delete-orphan")


class CustomModelChannel(Base):
    __tablename__ = "custom_model_channels"

    id: int              = Column(Integer, primary_key=True, autoincrement=True)
    custom_model_id: int = Column(Integer, ForeignKey("custom_models.id"), nullable=False)
    channel_id: int      = Column(Integer, ForeignKey("channels.id"), nullable=False)
    target_model: str    = Column(String(100), default="")
    channel_model: str   = Column(String(100), default="")
    weight: int          = Column(Integer, default=1)
    is_active: bool      = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=func.now())

    custom_model = relationship("CustomModel", back_populates="channel_mappings")
    channel = relationship("Channel")
```

**三种选择模式**：

| 模式 | `selection_mode` | 行为 |
|---|---|---|
| 自动选择 | `"auto"` | 使用 `target_model` 进行正常渠道分发 |
| 指定渠道 | `"specific"` | 直接指定 `channel_id` + `channel_model` |
| 多渠道路由 | `"multi"` | 通过 `channel_mappings` 配置加权路由 |

### 3.9 Admin 用户 (AdminUser) — `admin_users` （v2.0 新增）

```python
class AdminUser(Base):
    __tablename__ = "admin_users"

    id: int            = Column(Integer, primary_key=True, autoincrement=True)
    username: str      = Column(String(50), unique=True, nullable=False, index=True)
    password_hash: str = Column(String(255), nullable=False)  # bcrypt hash
    email: str         = Column(String(100))
    is_active: bool    = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=func.now())
    updated_at: datetime = Column(DateTime, default=func.now(), onupdate=func.now())

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
```

**认证流程**：
```
POST /admin/login { username, password }
  → 查 admin_users → verify_password()
  → 生成 UUID session_id + 2小时过期
  → 存入 admin_sessions 字典
  → 返回 { token: session_id }

后续 /admin/* 请求:
  → verify_admin_token → 从 admin_sessions 查 session_id
  → 验证未过期 → 允许请求
```

默认账号：`super` / `key_888`（首次启动自动创建）

---

## 四、API 接口设计

### 4.1 OpenAI 兼容接口（对外暴露）

| 方法 | 路径 | 功能 | 实战状态 |
|---|---|---|---|
| POST | `/v1/chat/completions` | 对话补全 (stream + non-stream) | ✅ |
| POST | `/v1/images/generations` | 图片生成 | ✅ |
| POST | `/v1/audio/transcriptions` | 语音转文字 | ✅ |
| POST | `/v1/audio/speech` | 文字转语音 | ✅ |
| POST | `/v1/embeddings` | 文本向量化 | ✅ |
| GET  | `/v1/models` | 模型列表 (内置 + 自定义) | ✅ |
| GET  | `/v1/models/{model_id}` | 模型详情 | ✅ |
| GET  | `/v1/models/categories` | 分类模型列表（分组） | ✅ v2.0 |
| POST | `/v1/completions` | 文本补全 (旧) | ❌ 待补充 |
| POST | `/v1/images/edits` | 图片编辑 | ❌ 待补充 |
| POST | `/v1/audio/translations` | 语音翻译 | ❌ 待补充 |
| POST | `/v1/rerank` | 重排序 | ❌ 待补充 |
| POST | `/v1/moderations` | 内容审核 | ❌ 待补充 |
| GET  | `/v1/realtime` | 实时全模态 (WebSocket) | ❌ 待补充 |

### 4.2 管理后台接口

所有 `/admin/*` 路由需 session 认证 (`X-Session-Token` 头)。

**认证**（v2.0）：

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/admin/login` | Admin 登录 (username + password → session_id) |
| POST | `/admin/logout` | Admin 登出 |
| GET  | `/admin/auth/check` | 验证 session 有效性 |
| POST | `/admin/change-password` | 修改 Admin 密码 |
| POST | `/admin/change-username` | 修改 Admin 用户名 |

**统计**：

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/admin/health` | 健康检查 |
| GET | `/admin/version` | 版本信息（返回 git commit hash + buildTime） |
| GET | `/admin/server-info` | 服务信息（v2.0 新增） |
| GET | `/admin/stats/overview` | 总览统计 |

**提供商管理**：

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/admin/providers` | 提供商列表 |
| POST | `/admin/providers` | 新增 |
| PUT | `/admin/providers/{id}` | 编辑 |
| DELETE | `/admin/providers/{id}` | 删除 |

**渠道管理**：

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/admin/channels` | 渠道列表 |
| POST | `/admin/channels` | 新增 |
| PUT | `/admin/channels/{id}` | 编辑 |
| DELETE | `/admin/channels/{id}` | 删除 |
| POST | `/admin/channels/{id}/test` | 测试渠道 |
| POST | `/admin/channels/{id}/auto-config` | 自动补全 |
| POST | `/admin/channels/{id}/toggle` | 切换启用/禁用 |
| POST | `/admin/channels/auto-detect` | 智能检测 |

**API Key 管理**（v2.0）：

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/admin/api-keys` | 列表 |
| POST | `/admin/api-keys` | 新增 |
| GET | `/admin/api-keys/{id}` | 详情 |
| PUT | `/admin/api-keys/{id}` | 编辑 |
| DELETE | `/admin/api-keys/{id}` | 删除 |
| POST | `/admin/api-keys/{id}/regenerate` | 重新生成 Key |

**自定义模型管理**（v2.0）：

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/admin/custom-models` | 列表 |
| POST | `/admin/custom-models` | 新增 |
| GET | `/admin/custom-models/{id}` | 详情 |
| PUT | `/admin/custom-models/{id}` | 编辑 |
| DELETE | `/admin/custom-models/{id}` | 删除 |

**模型分类管理**：

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/admin/models` | 列表 |
| GET | `/admin/models/categories` | 分类列表 |
| POST | `/admin/models` | 新增 |
| PUT | `/admin/models/{id}` | 编辑 |
| DELETE | `/admin/models/{id}` | 删除 |

**预置数据**：

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/admin/presets/load-providers` | 加载预置提供商 |
| POST | `/admin/presets/load-models` | 加载预置模型分类 |
| GET | `/admin/presets/status` | 预置数据状态 |

**日志**：

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/admin/logs` | 请求日志分页 |

**其他**：

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/admin/ui` | 管理面板 HTML |

---

## 五、核心功能详细设计

### 5.1 适配器模式 (Adaptor Pattern)

#### 5.1.1 抽象基类

```python
from abc import ABC, abstractmethod

class BaseAdaptor(ABC):
    api_type: str = ""

    @abstractmethod
    def build_request_url(self, channel, request_model: str, endpoint: str) -> str:
        ...

    @abstractmethod
    def build_headers(self, channel, original_headers: dict) -> dict:
        ...

    @abstractmethod
    def convert_chat_request(self, channel, openai_request: dict) -> dict:
        ...

    @abstractmethod
    def convert_chat_response(self, upstream_response: dict, request_model: str) -> dict:
        ...

    @abstractmethod
    def convert_stream_chunk(self, chunk_line: str) -> dict | None:
        ...

    def convert_image_request(self, channel, openai_request: dict) -> dict:
        raise NotImplementedError

    def convert_embedding_request(self, channel, openai_request: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_model_list(self, channel) -> list[str]:
        ...
```

#### 5.1.2 适配器注册表

```python
class AdaptorRegistry:
    _adaptors: dict[str, type[BaseAdaptor]] = {}

    @classmethod
    def register(cls, adaptor_class: type[BaseAdaptor]):
        cls._adaptors[adaptor_class.api_type] = adaptor_class

    @classmethod
    def get(cls, api_type: str) -> BaseAdaptor:
        adaptor_class = cls._adaptors.get(api_type)
        if adaptor_class is None:
            raise ValueError(f"Unknown api_type: {api_type}")
        return adaptor_class()

# 注册
AdaptorRegistry.register(OpenAIAdaptor)    # api_type="openai"
AdaptorRegistry.register(GeminiAdaptor)    # api_type="gemini"
AdaptorRegistry.register(ClaudeAdaptor)    # api_type="claude"
AdaptorRegistry.register(CustomAdaptor)    # api_type="custom"
```

**OpenAIAdaptor**：标准 OpenAI 格式，几乎无需转换，仅处理 `model_mapping`
**GeminiAdaptor**：`contents/parts` 格式转换 + SSE chunk 解析 + API Key 拼 URL
**ClaudeAdaptor**：`x-api-key` 头认证 + `messages/system` 分离 + SSE event 解析
**CustomAdaptor**：继承 OpenAIAdaptor，追加 `extra_headers`/`extra_params` + `auto_detect`

详见文档 v1.0 中 Section 5.1.2~5.1.5 的详细代码示例。

### 5.2 渠道分发器 (Distributor — v2.0)

```python
class Distributor:

    @staticmethod
    async def resolve_model(model: str) -> tuple[str, int | None]:
        """
        解析模型名称 → (实际模型名, 渠道ID或None)
        优先查 CustomModel，匹配自定义模型路由配置
        """
        async with async_session() as session:
            result = await session.execute(
                select(CustomModel).where(
                    CustomModel.model_id == model,
                    CustomModel.is_active == True
                )
            )
            custom_model = result.scalar_one_or_none()

            if custom_model:
                if custom_model.selection_mode == "specific" and custom_model.channel_id:
                    actual_model = custom_model.channel_model or custom_model.target_model or model
                    return (actual_model, custom_model.channel_id)
                else:
                    return (custom_model.target_model or model, None)
            return (model, None)

    @staticmethod
    async def select_channel(model: str, specific_channel_id: int | None = None) -> Channel:
        """
        选择渠道：
        - 指定渠道 → 直接返回
        - 自动选择 → channels.model  LIKE + status=1 → priority + weight
        - Fallback: Ability 表 JOIN
        """
```

### 5.3 API Key 认证体系（v2.0 新增）

```
客户端请求 /v1/chat/completions
  Authorization: Bearer sk-super-key-abc123...

中间件 verify_api_token:
  1. 提取 Bearer Token
  2. SELECT * FROM api_keys WHERE key={token_hash}? AND is_active=1
  3. 如果 expires_at < now → 403
  4. 存入 request.state:
     - allowed_models → Key 的 models 字段解析（空=全部允许）
     - request_count += 1, last_used_at = now
  5. 失败 → 401

路由层:
  6. 如果 allowed_models 非空且 model 不在列表中 → 403 "Model not allowed"
```

**与 v1.0 的差异**：
- v1.0：单一 `SUPER_KEY_API_TOKEN`，任意模型可调用
- v2.0：多 ApiKey，每个 Key 独立模型权限、有效期、使用统计

### 5.4 预置数据管理

当前实现：预置数据硬编码在 `preset_service.py` 中：
- `_get_builtin_providers()` → 17 个提供商
- `_get_builtin_models()` → 31 个模型分类

启动时自动加载：`PresetService.load_all_if_empty()`

**后续优化方向**：迁移到 `data/presets/*.json` 文件，补充至目标 176 模型

---

## 六、开发计划（带完成度）

### 阶段一：基础框架 ✅ 100%
1. ✅ 项目目录结构
2. ✅ `app/config.py`
3. ✅ `app/database.py`
4. ✅ `app/models/base.py`
5. ✅ `app/main.py`（追加：全局异常 + Session 清理）

### 阶段二：数据模型 + 预置数据 🟡 75%
1. ✅ Provider / Channel / Ability / ModelClassification / RequestLog / SystemConfig
2. ✅ ApiKey / CustomModel / CustomModelChannel / AdminUser（追加）
3. 🟡 预置数据：Python 硬编码，仅 31 模型 / 17 提供商 → 目标：JSON + 176 模型
4. ❌ `data/presets/*.json`：未创建

### 阶段三：适配器层 ✅ 100%
1. ✅ BaseAdaptor + OpenAIAdaptor + GeminiAdaptor + ClaudeAdaptor + CustomAdaptor
2. ✅ AdaptorRegistry 工厂模式

### 阶段四：核心服务 ✅ 100%
1. ✅ Distributor（追加 resolve_model + 自定义模型路由）
2. ✅ RelayService（relay_chat）
3. ✅ ChannelService（测试 + 自动配置）
4. ✅ ProviderService
5. ✅ PresetService
6. ✅ ApiKeyService（v2.0）
7. ✅ CustomModelService（v2.0）

### 阶段五：路由 + 中间件 🟡 75%
1. ✅ `auth.py`（多 Key 认证 + admin session）
2. ❌ `request_id.py` — 未实现
3. ✅ `request_log.py`
4. ❌ `rate_limit.py` — 未实现
5. ✅ `relay.py`（8/12 OpenAI 端点）
6. ✅ `admin.py`（41 端点）

### 阶段六：管理面板 ✅ 100%
1. ✅ `static/admin.html`（功能超出文档）

### 阶段七：运行脚本 + 配置 ✅ 100%

### 阶段八：辅助工具 🟡 50%
1. ✅ `crypto.py`
2. ❌ `sse.py` — SSE 处理内联
3. ✅ `logger.py`
4. ❌ `response.py` — 未实现

### 阶段九：测试 ❌ 0%

---

## 七、开发规范

### 7.1 代码风格
- 遵循 PEP 8
- 类型注解尽量覆盖
- 无注释（代码自解释）

### 7.2 命名规范

| 类型 | 规则 | 示例 |
|---|---|---|
| 文件名 | snake_case | `relay_service.py` |
| 类名 | PascalCase | `OpenAIAdaptor` |
| 函数/方法 | snake_case | `convert_chat_request()` |
| 变量 | snake_case | `channel_id` |
| 常量 | UPPER_SNAKE | `MAX_RETRIES` |
| 数据库表 | snake_case 复数 | `channels` |

### 7.3 安全规范
- API Key：AES-256-GCM 加密 → PBKDF2 派生 → Fernet，密钥来自 `SUPER_KEY_ENCRYPTION_KEY`
- Admin 密码：bcrypt hash（`AdminUser.hash_password`）
- API Key 脱敏：`[前4后4]`
- SQLite 文件权限：仅当前用户可读写

### 7.4 日志规范（v2.0）
全项目使用 `logging.getLogger(__name__)`：

| 级别 | 场景 | 通用逻辑 |
|---|---|---|
| `logger.info` | 提供商删除/更新、渠道创建/删除、模型编辑/删除、服务启动/关闭 | 关键操作 |
| `logger.warning` | 渠道测试失败、上游 API 错误、认证失败 | 需关注但非阻断 |
| `logger.error` | 未知异常、系统级错误 | 严重问题 |

---

## 八、环境配置

### 8.1 环境变量

```env
# 服务
SUPER_KEY_HOST=0.0.0.0
SUPER_KEY_PORT=8000

# 数据库
SUPER_KEY_DATABASE_URL=sqlite+aiosqlite:///./data/super_key.db

# 加密 (32 字节)
SUPER_KEY_ENCRYPTION_KEY=super-key-change-me-to-32-bytes!

# 管理员 Token (向后兼容，v2.0 推荐使用 Admin 登录)
ADMIN_TOKEN=admin-change-me

# 日志级别
SUPER_KEY_LOG_LEVEL=INFO
```

### 8.2 Python 依赖

```txt
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy[asyncio]>=2.0.30
aiosqlite>=0.20.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
httpx>=0.27.0
python-dotenv>=1.0.1
cryptography>=42.0.0
bcrypt>=4.0.0
```

---

## 九、管理面板设计

### 9.1 页面结构

```
┌─────────────────────────────────────────────┐
│  Super-Key Admin         [用户] [退出]       │
├──────────┬──────────────────────────────────┤
│ 📊 概览   │                                  │
│ 🔌 渠道   │        主内容区域                  │
│ 🏢 提供商 │        (列表/表单/详情)           │
│ 🧠 模型   │                                  │
│ 🔑 API Key│                                  │
│ 🎯 自定义 │                                  │
│ 📋 日志   │                                  │
│ ⚡ 预设   │                                  │
└──────────┴──────────────────────────────────┘
```

### 9.2 核心页面（v2.0 完善）

**渠道管理页**：列表（名称/提供商/API类型/模型数/状态/响应时间）+ 新增/编辑表单 + 测试/自动补全/启用禁用/删除

**API Key 管理页**（v2.0）：列表（名称/Key预览/模型限制/状态/请求数）+ 新增表单 + Key 生成/删除

**自定义模型页**（v2.0）：列表（别名/实际模型/选择模式/渠道）+ 新增表单（三种模式选择）

**提供商管理页**：列表（名称/代码/API Base/状态）+ 新增/编辑/删除 + 内置提示

**模型分类页**：分类侧边栏 + 模型列表 + 新增/编辑/删除

**关于页**（v2.1）：显示当前版本号（git commit hash），检测新版本，一键更新按钮

### 9.3 前端技术
- Vue.js 3 CDN (完整版)
- Tailwind CSS CDN
- 单文件 `static/admin.html`，零构建
- Fetch API 调用 `/admin/*` + Session Token 认证
- 版本检测：每 5 分钟请求 `/admin/version`，对比 localStorage 中的版本号，不同则提示更新
- api() 错误处理：解析 JSON 错误响应（detail/error.message），显示可读消息

### 9.4 安全机制
- 管理员密码：首次启动从环境变量 `SUPER_KEY_DEFAULT_ADMIN_PASSWORD` 读取，未设置则随机生成
- 弱密钥检测：启动时检查 api_token/admin_token/encryption_key 是否为默认值，使用则警告
- Session 并发安全：`admin_sessions` 字典操作使用 `asyncio.Lock` 保护
- 退出登录：前端调用 `/admin/logout` 通知后端删除 session
- API Key 统计更新：使用 SQL 原子操作 `UPDATE ... SET request_count = COALESCE(request_count, 0) + 1` 避免竞态

### 9.5 性能优化
- RequestLog 表索引：model、channel_id、is_error 字段添加索引
- 批量插入：sync_abilities 使用 `session.add_all()` 替代循环 `session.add()`
- 批量删除：channel_mappings 使用 SQL `DELETE WHERE` 替代循环 `session.delete()`
- 并行网络探测：OpenAI/Gemini 探测使用 `asyncio.gather()` 并行执行
- 数据库连接池：配置 `pool_pre_ping=True` 和 `check_same_thread=False`

### 9.6 部署与数据库
- 数据库路径：`database.py` 将相对路径解析为绝对路径后传给 `create_async_engine`，避免 cwd 不一致导致路径错误
- 自动迁移：`init_db()` 在 `create_all` 之后执行自动迁移逻辑，检测已有表缺失的列并执行 `ALTER TABLE ADD COLUMN`，替代 Alembic
- 数据库文件：`data/super_key.db` 不纳入 git 跟踪（`.gitignore` 排除 `*.db`），首次启动自动创建
- 配置模板：`.env.example` 提供完整环境变量模板，部署者复制为 `.env` 后修改
- Vercel 限制：SQLite 不兼容 Serverless 环境（只读文件系统），需使用 Turso/Vercel Postgres 等外部数据库
- 目录结构：`data/.gitkeep` 确保空目录被 git 跟踪