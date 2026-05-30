# Super-Key

> 个人自用大模型聚合平台

聚合多个 AI 提供商的大模型 API，统一转换为 OpenAI 兼容接口。实现一处配置、多端调用。

---

## 🌟 项目概述

Super-Key 是一个轻量级的大模型 API 聚合网关，旨在帮助个人用户以最简单的方式管理和使用多家 AI 服务。通过统一的 OpenAI 兼容接口，您可以无缝切换不同的 AI 提供商，无需修改客户端代码。

### ✨ 核心功能

| 功能 | 描述 |
|---|---|
| **多提供商聚合** | 支持 17+ 内置 AI 提供商，支持自定义接入 |
| **OpenAI 兼容** | 完全兼容 OpenAI API 格式，无缝对接各类客户端 |
| **多 API Key 管理** | 创建多个 API Key，独立设置权限和有效期 |
| **自定义模型路由** | 创建自定义模型别名，灵活配置渠道映射 |
| **智能渠道分发** | 基于优先级和权重自动选择最优渠道 |
| **自动重试** | 上游服务失败时自动切换备用渠道 |
| **管理面板** | 可视化管理所有配置 |
| **请求日志** | 完整的请求记录和统计 |
| **版本检测** | 自动检测新版本，一键更新 |

---

## 🛠️ 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | >= 0.115.0 |
| 数据库 | SQLite + SQLAlchemy | >= 2.0.30 |
| HTTP 客户端 | httpx | >= 0.27.0 |
| 配置管理 | Pydantic Settings | >= 2.3.0 |
| 加密 | cryptography + bcrypt | >= 42.0.0 |
| 前端 | Vue.js 3 + Tailwind CSS | CDN |
| 运行时 | Python | >= 3.11 |

---

## 📋 环境要求

- Python 3.11+
- 操作系统：Windows / macOS / Linux
- 依赖：见 `requirements.txt`

---

## 🚀 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/sgobiorodolfo170-ai/super-key.git
cd super-key
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 并重命名为 `.env`，修改配置：

```env
# 服务配置
SUPER_KEY_HOST=0.0.0.0
SUPER_KEY_PORT=8000

# 数据库路径
SUPER_KEY_DATABASE_URL=sqlite+aiosqlite:///./data/super_key.db

# 加密密钥（32 位字符串，请务必修改！）
SUPER_KEY_ENCRYPTION_KEY=your-32-character-encryption-key

# 日志级别
SUPER_KEY_LOG_LEVEL=INFO
```

### 3. 启动服务

```bash
python run.py
```

服务启动后访问：
- API 端点：`http://localhost:8000/v1/`
- 管理面板：`http://localhost:8000/admin/ui`

### 4. 初始登录

管理面板默认账号：
- 用户名：`admin`
- 密码：`admin123`

> ⚠️ **首次登录后请立即修改密码！**

---

## 📖 使用指南

### 基本使用

#### 作为 OpenAI 替代

将您的客户端 API 地址指向 `http://localhost:8000/v1/`，使用管理面板生成的 API Key：

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-api-key" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

### 管理面板功能

| 模块 | 功能 |
|---|---|
| **概览** | 服务状态和统计信息 |
| **渠道** | 添加、编辑、测试渠道配置 |
| **提供商** | 管理 AI 提供商信息 |
| **模型** | 查看和管理模型分类 |
| **API Key** | 创建和管理访问密钥 |
| **自定义模型** | 创建自定义模型别名和路由 |
| **日志** | 查看请求日志 |
| **预设** | 加载预置配置 |
| **设置** | 修改密码、修改用户名 |
| **关于** | 查看版本号、检测更新 |

---

## 🔌 API 文档

### OpenAI 兼容接口

| 端点 | 方法 | 描述 |
|---|---|---|
| `/v1/chat/completions` | POST | 对话补全 |
| `/v1/images/generations` | POST | 图片生成 |
| `/v1/audio/transcriptions` | POST | 语音转文字 |
| `/v1/audio/speech` | POST | 文字转语音 |
| `/v1/embeddings` | POST | 文本向量化 |
| `/v1/models` | GET | 模型列表 |
| `/v1/models/{id}` | GET | 模型详情 |
| `/v1/models/categories` | GET | 分类模型列表 |

### 管理接口

| 端点 | 方法 | 描述 |
|---|---|---|
| `/admin/login` | POST | 管理员登录 |
| `/admin/logout` | POST | 管理员登出 |
| `/admin/health` | GET | 健康检查 |
| `/admin/version` | GET | 获取当前版本信息 |
| `/admin/auth/check` | GET | 验证登录状态 |
| `/admin/stats/overview` | GET | 统计概览 |
| `/admin/channels` | GET/POST | 渠道管理 |
| `/admin/providers` | GET/POST | 提供商管理 |
| `/admin/api-keys` | GET/POST | API Key 管理 |
| `/admin/custom-models` | GET/POST | 自定义模型管理 |
| `/admin/models` | GET/POST | 模型分类管理 |

### 完整 API 文档

启动服务后访问：
- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

---

## 📁 项目结构

```
super-key/
├── app/                    # 应用核心代码
│   ├── adapters/           # 提供商适配器
│   ├── middleware/         # 中间件
│   ├── models/             # 数据库模型
│   ├── routers/            # API 路由
│   ├── services/           # 业务逻辑服务
│   ├── utils/              # 工具函数
│   ├── config.py           # 配置管理
│   ├── database.py         # 数据库连接
│   └── main.py             # 应用入口
├── data/                   # 数据目录（SQLite 数据库）
├── static/                 # 静态文件（管理面板）
├── .env                    # 环境变量
├── .env.example            # 环境变量示例
├── requirements.txt        # 依赖清单
├── run.py                  # 启动脚本
├── DEVELOPMENT_DOC.md      # 开发文档
├── ROADMAP.md              # 迭代路线图
├── PROGRESS.md             # 任务进度
└── WORKFLOW.md             # 开发流程规范
```

---

## 🤝 贡献指南

### 开发流程

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feat/your-feature`
3. 提交代码：`git commit -m "feat(模块): 描述"`
4. 推送到分支：`git push origin feat/your-feature`
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 编码规范
- 使用类型注解
- 保持代码自解释，必要时添加注释
- 关键操作添加日志记录
- 异常处理必须记录日志

### Commit 规范

```
<type>(<scope>): <summary>

类型说明：
- feat: 新功能
- fix: Bug 修复
- perf: 性能优化
- refactor: 重构
- test: 测试
- docs: 文档
- chore: 工程配置
```

---

## 📜 许可证

MIT License - 详见 `LICENSE` 文件

---

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 Issue：[GitHub Issues](https://github.com/sgobiorodolfo170-ai/super-key/issues)
- 邮件：sgobiorodolfo170@gmail.com

---

## 📊 项目状态

| 状态 | 说明 |
|---|---|
| 开发进度 | 核心功能已完成，持续优化中 |
| 测试覆盖 | 正在完善测试框架 |
| 文档 | 开发文档和 API 文档已完善 |

> **注意**：本项目仅供个人使用，生产环境部署请做好安全加固。
