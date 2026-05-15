# Super-Key 开发流程规范

> 版本：v1.0 | 创建日期：2026-05-15
>
> 本文档定义项目团队的标准开发流程，覆盖从需求到交付的完整周期。

---

## 一、流程总览

```
需求/反馈 ──► 任务创建 ──► 开发实现 ──► 自测 ──► Code Review ──► 合并 ──► 部署验证
     │            │            │          │          │            │          │
     ▼            ▼            ▼          ▼          ▼            ▼          ▼
  ISSUE.md    PROGRESS.md   coding    run tests  检查清单      git merge  集成测试
  或口头      登记+排期     +logger   +lint      3-step        +commit     回归
```

---

## 二、问题反馈机制

### 2.1 反馈渠道

| 渠道 | 适用场景 | 模板 |
|---|---|---|
| 口头/即时通讯 | 小问题、紧急 bug | 「模块 + 现象 + 复现步骤」 |
| ISSUE 记录 | 需跟踪的中大型问题 | 见 2.2 |
| Code Review 标注 | 代码质量问题 | 行级标注 + 建议方案 |

### 2.2 ISSUE 模板

```markdown
### 问题概述
[一句话描述]

### 严重程度
P0(阻塞) / P1(重要) / P2(优化) / P3(低优先)

### 影响范围
- 模块：[如 app/routers/admin.py]
- 功能：[如 提供商列表加载慢]

### 复现步骤
1. ...
2. ...
3. 观察到：[现象]

### 期望行为
[应该怎样]

### 建议方案
[可选]
```

### 2.3 反馈响应 SLA

| 优先级 | 响应时限 | 修复时限 |
|---|---|---|
| P0 | 2h | 24h |
| P1 | 8h | 72h |
| P2 | 48h | 下一 Sprint |
| P3 | 不受限 | 后续迭代 |

---

## 三、任务分配流程

### 3.1 任务生命周期

```
⬜ 未开始  →  🔄 进行中  →  ✅ 已完成
                  │
                  ├── ⛔ 已阻塞（需备注阻塞原因）
                  └── ❌ 已取消（需备注取消原因）
```

### 3.2 任务登记

所有任务登记在 [PROGRESS.md](file:///g:/--------开发--------/开发中---的项目源码/2/super-key/PROGRESS.md)：

```markdown
| ID | 任务 | 优先级 | 工时 | 完成标准 | 状态 |
|---|---|---|---|---|---|
| ARCH-01 | 新建 data/presets/providers.json | P0 | 1h | JSON 文件包含全部提供商 | ⬜ |
```

### 3.3 任务启动前检查清单

在开始执行任务前，确认以下事项：

- [ ] 任务在 PROGRESS.md 中已登记
- [ ] 理解了完成标准和验收条件
- [ ] 确定了影响范围和相关文件
- [ ] 预估工时已确认合理
- [ ] 无阻塞项或依赖冲突

### 3.4 WIP 限制

同一时间最多 **2 个** 进行中任务，完成一个再开下一个。

---

## 四、开发规范

### 4.1 分支策略

```
main ─────────────────────────────►
  │
  └── feat/s1-tests ──────► merge
  └── feat/s1-presets ────► merge
  └── fix/rob-06-validate─► merge
```

- 主分支：`main`
- Feature 分支：`feat/<sprint>-<feature>`
- Fix 分支：`fix/<task-id>-<desc>`
- 每个逻辑变更一个分支，完成后合并

### 4.2 Commit 规范

```
<type>(<scope>): <summary>

feat(admin): add website/description fields to provider form
fix(crypto): cache PBKDF2 derived key at module level
perf(relay): optimize /v1/models/categories with GROUP BY
refactor(distributor): extract resolve_model to separate method
test(adapters): add unit tests for OpenAI chat request conversion
```

| type | 说明 |
|---|---|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `perf` | 性能优化 |
| `refactor` | 重构（无功能变更） |
| `test` | 测试 |
| `docs` | 文档 |
| `chore` | 工程配置 |

### 4.3 编码规范（速查）

| 规则 | 说明 |
|---|---|
| PEP 8 | Python 代码风格 |
| 类型注解 | 函数签名尽量带类型 |
| 无注释 | 代码自解释，只在必要时加注释 |
| `logging.getLogger(__name__)` | 日志统一入口 |
| 关键操作 `logger.info()` | 提供商删除/更新、渠道变更等 |
| 异常 `logger.warning()` / `logger.error()` | 异常必须记录，不可 `except: pass` |
| `PROVIDER_FIELDS` / `CHANNEL_FIELDS` 白名单 | 新增 Admin 端点字段须同步白名单 |
| `setattr` 必须白名单过滤 | 防止注入 |

---

## 五、Code Review 规范

### 5.1 审查三步骤

```
第一步：性能审查
  - 检查是否有 N+1 查询、循环嵌套、重复计算
  - 检查 IO/DB 调用是否可合并或缓存
  - 检查是否引入新的阻塞操作

第二步：逻辑与架构审查
  - 检查是否破坏现有分层架构
  - 检查新代码的异常处理和边界条件
  - 检查是否引入不必要的耦合

第三步：健壮性与规范审查
  - 检查 Logger 是否覆盖
  - 检查字段白名单/参数校验是否到位
  - 检查是否符合编码规范
```

### 5.2 审查清单

| 检查项 | 通过标准 |
|---|---|
| [ ] 无 `except Exception: pass` | 异常必有日志 |
| [ ] `setattr` / `data: dict` 有白名单 | 字段白名单过滤 |
| [ ] 新端点有 `logger.info()` | 关键操作可追踪 |
| [ ] DB 查询无 N+1 | 批量/JOIN 替代逐条 |
| [ ] 无运行时 `__import__` | 顶部标准 import |
| [ ] 新模型已加入 `app/models/__init__.py` | 导入链完整 |
| [ ] 修改 API 后前端同步 | UI 与 API 一致 |
| [ ] 不引入裸 `500` 异常 | 全局 handler 兜底或自行捕获 |

### 5.3 审查通过标准

- 全部检查项 ✅
- 无 P0/P1 未解决问题
- 修改范围之外的代码未被意外改动

---

## 六、测试验证规范

### 6.1 测试策略

```
测试金字塔:
        ┌──────┐
        │ 集成  │  test_routers     (10%)
        ├──────┤
        │ 服务  │  test_services    (20%)
        ├──────┤
        │ 单元  │  test_adapters    (70%)
        └──────┘
```

### 6.2 自测检查清单

在提交 Code Review 前，逐项确认：

```markdown
- [ ] 服务正常启动（python run.py）
- [ ] 修改的端点 curl 验证通过
- [ ] 相关前端页面刷新后功能正常
- [ ] 日志输出正确（有操作时 logger.info 打印）
- [ ] 异常路径有覆盖（如传入无效 ID 返回 404）
- [ ] 无新增控制台异常或 500 错误
```

### 6.3 测试命令

```bash
# 启动服务
python run.py

# 健康检查
curl http://localhost:8000/admin/health

# 运行测试（框架搭建后）
pytest tests/ -v

# 检查导入
python -c "from app.main import app; print('OK')"
```

### 6.4 回归测试基线

每次合并前，运行以下回归验证：

| 端点 | 方法 | 预期 |
|---|---|---|
| `/admin/health` | GET | 200 |
| `/admin/stats/overview` | GET | 200 with channels/providers/models |
| `/admin/providers` | GET | 200 with 17 providers |
| `/admin/models` | GET | 200 with 32 models |
| `/v1/models` | GET | 200 with model list |
| `/admin/ui` | GET | 200 with HTML |

---

## 七、部署流程

### 7.1 部署检查清单

```markdown
- [ ] 所有测试通过
- [ ] Code Review 已批准
- [ ] PROGRESS.md 任务状态已更新
- [ ] DEVELOPMENT_DOC.md 如有 API 变更已同步
- [ ] Commit message 规范
- [ ] 无明显性能退化（响应时间/启动时间）
```

### 7.2 部署步骤

```bash
# 1. 合并到 main
git checkout main
git merge feat/xxx

# 2. 重启服务
# 停止旧进程 → python run.py

# 3. 冒烟验证
curl http://localhost:8000/admin/health
curl http://localhost:8000/v1/models

# 4. 确认日志
# 查看 Super-Key startup complete
```

---

## 八、文档维护

### 8.1 文档更新触发条件

| 触发条件 | 需更新文档 |
|---|---|
| 新增 API 端点 | `DEVELOPMENT_DOC.md` Section 4 |
| 新增数据模型 | `DEVELOPMENT_DOC.md` Section 3 |
| 架构变更 | `DEVELOPMENT_DOC.md` Section 2 |
| 依赖变更 | `DEVELOPMENT_DOC.md` Section 8.2 + `requirements.txt` |
| 迭代排期变更 | `ROADMAP.md` |
| 任务完成/新增 | `PROGRESS.md` |
| 流程变更 | `WORKFLOW.md`（本文档） |

### 8.2 文档版本号规则

```
DEVELOPMENT_DOC.md v<Major>.<Minor>
  Major: 架构重大变更
  Minor: API/数据模型增删

PROGRESS.md 不标记版本，实时更新任务状态
ROADMAP.md 随 Sprint 规划更新
WORKFLOW.md 随流程优化更新
```

---

## 九、附录：快速参考

### 关键文件速查

| 文件 | 用途 |
|---|---|
| `app/main.py` | 服务入口，中间件注册，全局异常 |
| `app/routers/relay.py` | `/v1/*` 对外 API |
| `app/routers/admin.py` | `/admin/*` 管理 API |
| `app/services/distributor.py` | 模型→渠道分发 |
| `app/services/relay_service.py` | 上游中继 |
| `app/services/preset_service.py` | 预置数据 |
| `app/middleware/auth.py` | API Key 认证 + Admin session |
| `static/admin.html` | 管理面板 SPA |

### 常用命令

```bash
python run.py                              # 启动
pytest tests/ -v                           # 测试
python -c "from app.main import app"       # 导入验证
```