# Helix Runtime 核心运行时基础设施 实施计划

- Req ID: REQ-20260415-helix-runtime-core
- Plan Version: v1
- Status: drafting
- Created At: 2026-04-15
- Updated At: 2026-04-15

## 实施范围

实现 Helix Runtime 核心运行时基础设施的 4 个核心模块 + Session Storage，基于 Python + FastAPI 技术栈。

## 涉及模块与文件

### 目录结构

```text
helix-runtime/
├── pyproject.toml              # 项目依赖配置
├── README.md
├── helix/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── api/
│   │   ├── __init__.py
│   │   ├── sessions.py         # Session 相关 API
│   │   ├── chat.py             # Chat 处理 API
│   │   └── workflows.py        # Workflow 相关 API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── capability_trigger.py   # Capability Trigger Layer
│   │   ├── context_manager.py      # Context Manager
│   │   ├── state_engine.py         # State Engine
│   │   └── workflow_runtime.py     # Post Workflow Runtime
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── memory.py           # 内存存储（初期用）
│   │   ├── redis.py            # Redis 存储
│   │   └── postgres.py         # PostgreSQL 存储（可选）
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py          # Session 数据模型
│   │   ├── message.py          # Message 数据模型
│   │   ├── state.py            # State 数据模型
│   │   └── trigger.py          # Trigger 相关模型
│   └── tests/
│       ├── __init__.py
│       ├── test_capability_trigger.py
│       ├── test_context_manager.py
│       ├── test_state_engine.py
│       ├── test_workflow_runtime.py
│       └── test_api.py
└── docs/
    └── ... (现有文档)
```

## 数据模型设计

### SessionState（状态引擎）

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class TaskStatus(str, Enum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class FeedbackType(str, Enum):
    NONE = "none"
    CONFIRM = "confirm"
    REVISION = "revision"

class SessionState(BaseModel):
    session_id: str
    current_topic: Optional[str] = None
    current_task: Optional[str] = None
    task_status: TaskStatus = TaskStatus.IDLE
    workflow_step: int = 0
    last_feedback_type: FeedbackType = FeedbackType.NONE
```

### Message（消息模型）

```python
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### Session（会话模型）

```python
from typing import List, Dict, Any

class Session(BaseModel):
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    state: SessionState
    workflow_log: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Trigger 相关模型

```python
class TriggerResult(BaseModel):
    trigger_context: bool
    trigger_workflow: bool
    mode: str  # "direct" | "continue" | "workflow"

class UserRequest(BaseModel):
    session_id: str
    user_input: str
```

### Context Manager 相关模型

```python
class PromptContext(BaseModel):
    context_blocks: List[str]
    final_prompt_segments: List[str]
```

### Workflow 相关模型

```python
class WorkflowType(str, Enum):
    DOCUMENT = "document"
    REVISION = "revision"

class WorkflowResult(BaseModel):
    success: bool
    output: Optional[str] = None
    step: int
    error: Optional[str] = None
```

## 接口设计

### 1. 创建 Session

- Method: `POST`
- Path: `/api/v1/sessions`
- Request Body:
  ```json
  {
    "session_id": "optional-string"
  }
  ```
- Response Body:
  ```json
  {
    "session_id": "string",
    "created_at": "ISO8601"
  }
  ```

### 2. 获取 Session

- Method: `GET`
- Path: `/api/v1/sessions/{session_id}`
- Path Params: `session_id`
- Response Body: `Session`（见数据模型）

### 3. 发送 Chat 请求（核心接口）

- Method: `POST`
- Path: `/api/v1/sessions/{session_id}/chat`
- Path Params: `session_id`
- Request Body:
  ```json
  {
    "user_input": "string",
    "system_prompt": "optional-string"
  }
  ```
- Response Body:
  ```json
  {
    "trigger_result": "TriggerResult",
    "prompt_context": "PromptContext",
    "session_state": "SessionState",
    "raw_user_input": "string",
    "suggested_response": "optional-string"
  }
  ```
- Validation: `user_input` 非空
- Error Cases:
  - 404: Session not found
  - 400: Invalid input

### 4. 触发 Workflow

- Method: `POST`
- Path: `/api/v1/sessions/{session_id}/workflows`
- Path Params: `session_id`
- Request Body:
  ```json
  {
    "workflow_type": "document|revision",
    "context": "optional-object"
  }
  ```
- Response Body: `WorkflowResult`

### 5. 获取历史消息

- Method: `GET`
- Path: `/api/v1/sessions/{session_id}/messages`
- Path Params: `session_id`
- Query Params: `limit: int = 5`
- Response Body: `List[Message]`

## 前端交互与状态

本阶段暂不实现前端，仅提供 REST API。未来可通过以下方式接入：

- Claude Code/opencode 通过 HTTP 调用 API
- 或者封装为 MCP 服务器

## 兼容性要求

- 初期使用内存存储，无需迁移
- API 路径统一使用 `/api/v1/` 前缀，便于未来版本管理
- 配置项通过环境变量或配置文件提供，支持热加载（可选）

## 实施步骤

### Step 1: 项目初始化与配置

- 目标: 搭建 Python + FastAPI 项目骨架
- 改动:
  - 创建 `pyproject.toml`（依赖：fastapi, uvicorn, pydantic, python-dotenv, redis）
  - 创建目录结构
  - 创建 `helix/config.py`（配置管理）
  - 创建 `helix/main.py`（FastAPI 应用入口）
- 完成标准:
  - `uvicorn helix.main:app --reload` 能成功启动
  - 访问 `/docs` 能看到 FastAPI 自动文档

### Step 2: 数据模型实现

- 目标: 实现所有 Pydantic 模型
- 改动:
  - 创建 `helix/models/session.py`
  - 创建 `helix/models/message.py`
  - 创建 `helix/models/state.py`
  - 创建 `helix/models/trigger.py`
- 完成标准:
  - 所有模型定义完成
  - 有基本的类型验证

### Step 3: 内存存储实现

- 目标: 实现 Session 内存存储（初期不依赖 Redis/PostgreSQL）
- 改动:
  - 创建 `helix/storage/memory.py`
  - 实现 Session 的增删改查
  - 实现 Message 的追加与查询
- 完成标准:
  - 能创建、获取 Session
  - 能向 Session 追加消息
  - 能获取历史消息（支持 limit）

### Step 4: Capability Trigger Layer 实现

- 目标: 实现能力触发层
- 改动:
  - 创建 `helix/core/capability_trigger.py`
  - 实现 Context Trigger 规则（关键词匹配：continue, continue previous, based on above, modify previous, not correct）
  - 实现 Workflow Trigger 规则（关键词匹配：document generation, multi-step analysis, revision task, formatting task）
- 完成标准:
  - 单元测试覆盖主要触发场景
  - 能正确识别 context trigger
  - 能正确识别 workflow trigger

### Step 5: Context Manager 实现

- 目标: 实现上下文管理器
- 改动:
  - 创建 `helix/core/context_manager.py`
  - 实现最近历史策略（MAX_RECENT_TURNS = 5）
  - 实现历史优先级排序
  - 实现 Prompt Layout 拼接
  - 强制约束：raw_user_input 不被修改
- 完成标准:
  - 单元测试验证历史选择逻辑
  - Prompt 按预期格式拼接
  - 用户原始输入保持不变

### Step 6: State Engine 实现

- 目标: 实现状态引擎
- 改动:
  - 创建 `helix/core/state_engine.py`
  - 实现 getState()
  - 实现 updateState()
  - 在指定时机触发状态更新（user input accepted / workflow step completed / model response returned / revision detected）
- 完成标准:
  - 状态能正确读取和更新
  - 状态更新时机正确触发

### Step 7: Post Workflow Runtime 实现（框架）

- 目标: 实现工作流运行时框架
- 改动:
  - 创建 `helix/core/workflow_runtime.py`
  - 定义 Workflow 接口
  - 实现 Document Workflow 骨架（4 个步骤）
  - 实现 Revision Workflow 骨架（4 个步骤）
  - 实现重试策略（MAX_RETRY = 2）
- 完成标准:
  - Workflow 框架能运行
  - 重试策略生效
  - 具体步骤内容可后续填充（本阶段不实现具体 LLM 调用）

### Step 8: API 层实现

- 目标: 实现所有 REST API
- 改动:
  - 创建 `helix/api/sessions.py`（POST /sessions, GET /sessions/{session_id}）
  - 创建 `helix/api/chat.py`（POST /sessions/{session_id}/chat）
  - 创建 `helix/api/workflows.py`（POST /sessions/{session_id}/workflows）
  - 集成所有核心模块
- 完成标准:
  - 所有 API 端点可访问
  - 通过 FastAPI 文档可测试
  - 输入输出符合接口设计

### Step 9: 集成测试

- 目标: 端到端测试完整流程
- 改动:
  - 创建 `helix/tests/test_api.py`
  - 测试多轮对话场景
  - 测试状态续接
  - 测试 workflow 触发
- 完成标准:
  - 集成测试通过
  - 验收标准的 5 项条件全部满足

## 验证方案

### 单元测试

- 每个核心模块都有对应的单元测试
- 使用 pytest 框架
- 测试文件位于 `helix/tests/`

### 手动验证

通过 FastAPI 自动文档（`/docs`）进行手动测试：

1. 创建 Session
2. 发送第一轮消息
3. 发送 "continue" 触发 context trigger
4. 验证状态正确更新
5. 发送 "document generation" 触发 workflow trigger

### 验收标准检查清单

- [ ] 多轮连续稳定：连续 5 轮对话，上下文正确传递
- [ ] 状态正确续接：中断后重新获取 Session，state 保持不变
- [ ] workflow 可控：Document Workflow 和 Revision Workflow 能被触发
- [ ] 输入不可变：raw_user_input 在整个流程中保持不变
- [ ] 历史上下文可配置：MAX_HISTORY_TURNS 可通过配置修改

## 风险与回退

### 风险 1: 存储层切换

- 风险: 初期用内存存储，后续切换到 Redis/PostgreSQL 可能需要重构
- 应对: 定义统一的 Storage 接口，内存存储和 Redis/PostgreSQL 都实现同一接口

### 风险 2: Workflow 具体实现复杂

- 风险: Document Workflow 和 Revision Workflow 的具体步骤可能需要 LLM 调用，复杂度高
- 应对: 本阶段只实现 Workflow 框架，具体步骤内容留空或用 mock 实现，后续迭代补充

### 回退方案

如果某步遇到阻塞，可以：
- 回退到上一步的提交
- 或者调整范围，将阻塞项移到下一阶段
