# AI Runtime Infrastructure Technical Specification

Version: 1.0
Status: Draft for Implementation

------

# 1. Scope

本规范定义一套轻量级 AI 应用运行时基础设施，用于支持：

- 多轮上下文管理
- 状态驱动任务续接
- 后置流程补充
- 能力触发控制

适用于：

- Chat 类 AI 应用
- Agent-like AI 应用
- 多轮任务型 AI 应用
- 文档 / 分析型 AI 应用

------

# 2. High-Level Runtime Flow

```text
User Request
-> Capability Trigger
-> Context Manager
-> State Engine
-> Post Workflow Runtime
-> Main LLM
-> Output
-> State Update
```

------

# 3. Core Modules

------

## 3.1 Capability Trigger Layer

### Purpose

决定当前请求是否需要触发特定系统能力。

------

### Input

```json
{
  "session_id": "string",
  "user_input": "string"
}
```

------

### Output

```json
{
  "trigger_context": true,
  "trigger_workflow": false,
  "mode": "direct"
}
```

------

### Trigger Rules

#### Context Trigger

以下情况必须触发：

```text
continue
continue previous
based on above
modify previous
not correct
```

------

#### Workflow Trigger

以下情况触发：

```text
document generation
multi-step analysis
revision task
formatting task
```

------

### Interface

```typescript
interface CapabilityTrigger {
  evaluate(input: UserRequest): TriggerResult
}
```

------

# 3.2 Context Manager

------

## Purpose

负责历史上下文选择与 Prompt 拼接。

------

## Input

```json
{
  "session_id": "string",
  "current_input": "string",
  "trigger_context": true
}
```

------

## Output

```json
{
  "context_blocks": [],
  "final_prompt_segments": []
}
```

------

## Rules

------

### Recent History Policy

```text
MAX_RECENT_TURNS = 5
```

------

### History Priority

```text
latest_turns
current_topic
last_decision
last_revision
```

------

### Prompt Layout

```text
system
state
history
current_input
```

------

### Hard Rule

```text
raw_user_input immutable
```

------

### Interface

```typescript
interface ContextManager {
  buildPromptContext(
    sessionId: string,
    userInput: string
  ): PromptContext
}
```

------

# 3.3 State Engine

------

## Purpose

负责维护系统运行状态，而非历史文本。

------

## State Schema

```json
{
  "session_id": "string",
  "current_topic": "string",
  "current_task": "string",
  "task_status": "idle|in_progress|completed",
  "workflow_step": 0,
  "last_feedback_type": "none|confirm|revision"
}
```

------

## State Update Timing

必须在以下阶段更新：

- user input accepted
- workflow step completed
- model response returned
- revision detected

------

## Interface

```typescript
interface StateEngine {
  getState(sessionId: string): SessionState
  updateState(
    sessionId: string,
    patch: Partial<SessionState>
  ): void
}
```

------

# 3.4 Post Workflow Runtime

------

## Purpose

在主模型无法单步完成任务时补充流程。

------

## Trigger Condition

```json
{
  "trigger_workflow": true
}
```

------

## Workflow Template

------

### Document Workflow

```text
extract structure
generate content
refine format
finalize
```

------

### Revision Workflow

```text
analyze issue
modify previous result
validate consistency
return final
```

------

## Retry Policy

```text
MAX_RETRY = 2
```

------

## Interface

```typescript
interface WorkflowRuntime {
  execute(
    taskType: string,
    context: PromptContext
  ): WorkflowResult
}
```

------

# 4. Session Storage Specification

------

## Storage Model

```json
{
  "session_id": "string",
  "messages": [],
  "state": {},
  "workflow_log": []
}
```

------

## Message Schema

```json
{
  "role": "user|assistant|system",
  "content": "string",
  "timestamp": "ISO8601"
}
```

------

# 5. Runtime Constraints

------

## Context Limit

```text
MAX_HISTORY_TURNS = 5
```

------

## Workflow Limit

```text
MAX_WORKFLOW_STEPS = 3
```

------

## Token Budget

```text
MAX_PROMPT_TOKENS = configurable
recommended: 4k
```

------

# 6. Non-Functional Requirements

------

## Stability First

禁止将不稳定小模型放入核心控制链路。

------

## Deterministic Rules Preferred

优先规则，不依赖模型判断核心流程。

------

## Input Safety

禁止覆盖用户原始输入。

------

## Extensibility

新增模块必须满足统一接口。

------

# 7. Future Extension Modules (Optional)

不属于核心规范：

- long-term memory
- preference engine
- replay system
- ranking system
- model routing

全部为 optional extension。

------

# 8. Recommended Implementation Stack

推荐：

```text
Kotlin / Java
Spring Boot
Redis (session state)
PostgreSQL (history)
```

或：

```text
Python
FastAPI
Redis
PostgreSQL
```

------

# 9. Acceptance Criteria

系统满足以下条件视为基础设施完成：

- 多轮连续稳定
- 状态正确续接
- workflow 可控
- 输入不可变
- 历史上下文可配置