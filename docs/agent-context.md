---
name: Agent Context
description: 智能体协作全局入口与调度文档
type: reference
---

# Agent Context

- Updated At: 2026-04-16

## 当前状态总览

本项目是 **Helix Runtime** - AI 应用运行时基础设施。

**当前进度**: v2 开发中 - AI Provider 抽象层 + MCP Server 实现

## 当前活跃需求列表

| Req ID | 需求名称 | 状态 | 优先级 |
|--------|----------|------|--------|
| REQ-20260415-helix-runtime-core | Helix Runtime 核心运行时基础设施 | in_progress (v2) | high |

## 当前主需求

REQ-20260415-helix-runtime-core - Helix Runtime v2 扩展（AI Provider + MCP Server）

**v1 状态**: ✅ 已完成（9 个步骤，5 项验收标准通过）

**v2 状态**: 🔄 进行中

## 下一步动作

v2 实施步骤：

1. ⏳ Step 1: Provider 抽象层（基类和注册表）
2. ⏳ Step 2: Ollama Provider
3. ⏳ Step 3: DeepSeek Provider
4. ⏳ Step 4: Minimax Provider
5. ⏳ Step 5: 火山引擎 Provider
6. ⏳ Step 6: Intent Detection 集成
7. ⏳ Step 7: MCP Server 实现
8. ⏳ Step 8: 配置更新
9. ⏳ Step 9: 集成测试

## 阻塞项

无。

## 文档索引

| 文档类型 | 路径 | 状态 |
|----------|------|------|
| 协作规则 | `docs/agent-handoff-rules.md` | ✅ 已存在 |
| 技术规格 | `AI Runtime Infrastructure Technical Specification.md` | ✅ 已存在 |
| 需求文档 | `docs/requirements/REQ-20260415-helix-runtime-core.md` | ✅ v2 更新中 |
| 计划文档 v1 | `docs/plans/PLAN-REQ-20260415-helix-runtime-core-v1.md` | ✅ 已完成 |
| 计划文档 v2 | `docs/plans/PLAN-REQ-20260415-helix-runtime-core-v2.md` | ✅ 已创建 |
| 进度文档 | `docs/progress/PROGRESS-REQ-20260415-helix-runtime-core.md` | ✅ 更新中 |

## v2 架构设计

```
用户 / Claude Code
    ↓
┌─────────────────────────────────────┐
│  Helix Runtime (MCP Server)         │
│  - Intent Detection Layer           │
│  - Capability Trigger Layer         │
│  - User AI Provider Layer           │
└─────────────────────────────────────┘
```

### AI Provider 支持

| Provider | 类型 | 用途 |
|----------|------|------|
| Ollama | 本地/远程 | 意图检测 + 用户 AI |
| DeepSeek | 云服务 | 意图检测 + 用户 AI |
| Minimax | 云服务（Code Plan） | 用户 AI |
| 火山引擎 | 云服务（Code Plan） | 用户 AI |

## 运行方式

```bash
# 安装依赖
pip install -e ".[dev]"

# 启动服务
uvicorn helix.main:app --reload

# 访问 API 文档
# http://localhost:8000/docs

# MCP Server（待实现）
uvicorn helix.mcp.server:app --reload --port 8765
```

## 最近更新

- [2026-04-16] **v2 开始** - 扩展架构：添加 AI Provider 抽象层和 MCP Server 层
- [2026-04-15] **v1 完成** - Helix Runtime 核心基础设施实现完成
