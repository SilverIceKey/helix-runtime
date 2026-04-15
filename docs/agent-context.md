---
name: Agent Context
description: 智能体协作全局入口与调度文档
type: reference
---

# Agent Context

- Updated At: 2026-04-15

## 当前状态总览

本项目是 **Helix Runtime** - AI 应用运行时基础设施。

**当前进度**: ✅ **全部完成** - Step 1-9 已完成，需求实现完成，5 项验收标准全部通过。

## 当前活跃需求列表

| Req ID | 需求名称 | 状态 | 优先级 |
|--------|----------|------|--------|
| REQ-20260415-helix-runtime-core | Helix Runtime 核心运行时基础设施 | **completed** | high |

## 当前主需求

REQ-20260415-helix-runtime-core - Helix Runtime 核心运行时基础设施

**状态**: ✅ 已完成

## 下一步动作

无（当前需求已完成）。

## 阻塞项

无。

## 文档索引

| 文档类型 | 路径 | 状态 |
|----------|------|------|
| 协作规则 | `docs/agent-handoff-rules.md` | ✅ 已存在 |
| 技术规格 | `AI Runtime Infrastructure Technical Specification.md` | ✅ 已存在 |
| 需求文档 | `docs/requirements/REQ-20260415-helix-runtime-core.md` | ✅ 已完成 |
| 计划文档 | `docs/plans/PLAN-REQ-20260415-helix-runtime-core-v1.md` | ✅ 已完成 |
| 进度文档 | `docs/progress/PROGRESS-REQ-20260415-helix-runtime-core.md` | ✅ 已完成 |

## 项目结构

```
helix/
├── main.py              # FastAPI 应用入口
├── config.py            # 配置管理
├── api/
│   ├── sessions.py      # Session API
│   ├── chat.py          # Chat API
│   └── workflows.py     # Workflow API
├── core/
│   ├── capability_trigger.py  # Capability Trigger Layer
│   ├── context_manager.py     # Context Manager
│   ├── state_engine.py        # State Engine
│   └── workflow_runtime.py    # Post Workflow Runtime
├── storage/
│   └── memory.py        # 内存存储
├── models/              # 数据模型
│   ├── state.py
│   ├── message.py
│   ├── session.py
│   └── trigger.py
└── tests/
    └── test_integration.py   # 集成测试
```

## 运行方式

```bash
# 安装依赖
pip install -e ".[dev]"

# 启动服务
uvicorn helix.main:app --reload

# 访问 API 文档
# http://localhost:8000/docs
```

## 最近更新

- [2026-04-15] **需求完成** - Helix Runtime 核心运行时基础设施实现完成，所有 9 个步骤完成，5 项验收标准全部通过
- [2026-04-15] 创建需求文档 `REQ-20260415-helix-runtime-core.md`
- [2026-04-15] 初始化文档体系结构和 agent-context.md
