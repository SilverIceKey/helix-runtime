# Helix Runtime 核心运行时基础设施

- Req ID: REQ-20260415-helix-runtime-core
- Status: in_progress (v2: AI Provider + MCP)
- Created At: 2026-04-15
- Updated At: 2026-04-16

## 背景

当前缺少一套轻量级的 AI 应用运行时基础设施，用于支持多轮上下文管理、状态驱动任务续接、后置流程补充、能力触发控制等场景。现有技术规格文档已定义核心模块与接口，需要转化为可执行的需求。

## 目标

实现一套完整的 AI 应用运行时基础设施，满足以下核心目标：
- 支持多轮对话上下文管理
- 支持状态驱动的任务续接
- 支持后置工作流补充执行
- 支持能力触发控制
- 支持多 AI Provider 接入（意图检测 + 用户 AI）
- 支持 MCP 协议接入 Claude Code

适用于 Chat 类、Agent-like、多轮任务型、文档/分析型 AI 应用。

## 范围内

### 核心模块（v1 已完成）

1. **Capability Trigger Layer** - 能力触发层
   - 判断当前请求是否需要触发特定系统能力
   - 支持 Context Trigger（上下文续接）
   - 支持 Workflow Trigger（工作流触发）
   - 提供明确的触发规则与接口

2. **Context Manager** - 上下文管理器
   - 负责历史上下文选择与 Prompt 拼接
   - 实现最近历史策略（MAX_RECENT_TURNS = 5）
   - 实现历史优先级（latest_turns > current_topic > last_decision > last_revision）
   - 实现固定的 Prompt Layout（system > state > history > current_input）
   - 强制约束：raw_user_input immutable

3. **State Engine** - 状态引擎
   - 负责维护系统运行状态（而非历史文本）
   - 实现 SessionState  schema
   - 在指定时机更新状态（user input accepted / workflow step completed / model response returned / revision detected）

4. **Post Workflow Runtime** - 后置工作流运行时
   - 在主模型无法单步完成任务时补充流程
   - 实现 Document Workflow（extract structure → generate content → refine format → finalize）
   - 实现 Revision Workflow（analyze issue → modify previous result → validate consistency → return final）
   - 实现重试策略（MAX_RETRY = 2）

### AI Provider 层（v2 新增）

#### 1. AI Provider 抽象层

统一接口，支持多种 AI Provider：

| Provider | 类型 | 用途 | API 格式 |
|----------|------|------|----------|
| Ollama | 本地/远程 | 意图检测 + 用户 AI | OpenAI 兼容 |
| DeepSeek | 云服务 | 意图检测 + 用户 AI | DeepSeek API |
| Minimax | 云服务（Code Plan） | 意图检测 + 用户 AI | Minimax API |
| 火山引擎 | 云服务（Code Plan） | 意图检测 + 用户 AI | 火山引擎 API |

#### 2. 意图检测层 (Intent Detection)

- 使用专门的 Intent Detection AI Provider
- 分析用户输入，判断意图（继续对话、触发工作流、闲聊等）
- 可配置使用哪个 Provider 进行意图检测

#### 3. 用户 AI 层 (User AI Provider)

- 用户实际使用的 AI Provider
- 支持 Code Plan 类型（Minimax、火山引擎）
- 可配置使用哪个 Provider

#### 4. 路由与编排

- 根据意图检测结果，路由到对应的处理流程
- 支持强制使用指定 Provider 进行特定任务

### MCP Server 层（v2 新增）

#### 1. MCP 协议支持

- 支持作为 MCP Server 接入 Claude Code
- 暴露 Skills/Functions 给 Claude Code 调用
- 支持强制 Claude Code 使用配置的 Provider

#### 2. Claude Code 集成

- Skill 定义：helix-runtime 提供的 AI 能力
- Function Calling：helix-runtime 提供的工具函数
- 强制路由：Claude Code 的请求必须经过 Helix Runtime 编排

### Session Storage

- 实现 Session Storage 规范
- 存储 session_id、messages、state、workflow_log
- 实现 Message schema

### 运行时约束

- MAX_HISTORY_TURNS = 5
- MAX_WORKFLOW_STEPS = 3
- MAX_PROMPT_TOKENS = configurable（推荐 4k）

### 非功能需求

- 稳定性优先：禁止将不稳定小模型放入核心控制链路
- 优先确定性规则：不依赖模型判断核心流程（意图检测除外）
- 输入安全：禁止覆盖用户原始输入
- 可扩展性：新增模块必须满足统一接口

## 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                      用户 / Claude Code                        │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                    Helix Runtime (MCP Server)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │ MCP Handler│  │ Skill Router│  │ Function Handler     │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                    Intent Detection Layer                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Intent AI Provider (可配置: Ollama / DeepSeek / ...)   │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                    Capability Trigger Layer                   │
│  - Context Trigger (continue, resume, based on above)         │
│  - Workflow Trigger (document generation, revision, etc.)     │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                    User AI Provider Layer                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ User AI Provider (可配置: Minimax / 火山引擎 / Ollama) │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                    Context Manager + State Engine             │
└──────────────────────────────────────────────────────────────┘
```

## 范围外

以下不属于本次核心实现范围（可选扩展模块）：

- long-term memory（长期记忆）
- preference engine（偏好引擎）
- replay system（回放系统）
- ranking system（排序系统）

## 约束与默认假设

### 技术栈约束（已确定）

**已选定：Python + FastAPI**

- Python 3.11+
- FastAPI（Web 框架）
- Redis（session state 存储）
- PostgreSQL（历史消息存储，可选，初期可用内存存储替代）

选型理由：
- 方便作为独立服务接入 Claude Code/opencode
- 侵入式小，通过 HTTP/MCP 对接
- AI 生态丰富，方便未来扩展
- 部署灵活，方便独立运行

### AI Provider 配置

```yaml
# Intent Detection Provider（用于分析用户意图）
intent_provider:
  type: "ollama"  # ollama / deepseek / minimax / volc
  model: "qwen2.5-coder"
  base_url: "http://localhost:11434/v1"
  api_key: ""  # 可选

# User AI Provider（用户实际使用的 AI）
user_provider:
  type: "minimax"  # minimax / volc / ollama / deepseek
  model: "abab6.5s-chat"
  api_key: "${MINIMAX_API_KEY}"
  base_url: "https://api.minimax.chat/v1"
```

### 其他约束

- 核心控制链路必须使用确定性规则，不得依赖 LLM 判断（意图检测除外）
- 用户原始输入必须保持不可变
- 状态更新必须在指定时机执行
- MCP Server 必须强制使用配置的 Provider

## 验收标准

### v1 已完成

1. ✅ 多轮连续稳定 - 能够连续处理 5 轮以上对话，上下文正确传递
2. ✅ 状态正确续接 - 中断后恢复，session state 能够正确续接
3. ✅ workflow 可控 - Document Workflow 和 Revision Workflow 能够按预期触发和执行
4. ✅ 输入不可变 - 用户原始输入在整个处理流程中保持不变
5. ✅ 历史上下文可配置 - MAX_HISTORY_TURNS、MAX_PROMPT_TOKENS 等参数可配置

### v2 新增验收标准

6. [ ] Intent Detection - 意图检测 Provider 可配置并正常工作
7. [ ] User AI Provider - 用户 AI Provider 可配置并正常工作
8. [ ] Multi-Provider Support - 支持 Ollama、DeepSeek、Minimax、火山引擎
9. [ ] MCP Server - 可作为 MCP Server 接入 Claude Code
10. [ ] Claude Code Integration - Claude Code 可通过 Helix Runtime 使用指定 Provider

## 待确认问题

- [ ] Code Plan 类型的 Provider（Minimax、火山引擎）的具体 API 格式
- [ ] MCP 协议的具体实现细节

## 关键决策记录

- [2026-04-16] 扩展架构：添加 AI Provider 抽象层和 MCP Server 层
- [2026-04-15] 确定技术栈：Python + FastAPI，理由：方便接入 Claude Code/opencode、侵入小、方便独立运行、AI 生态丰富
- [2026-04-15] 初始化需求文档，基于技术规格转化
