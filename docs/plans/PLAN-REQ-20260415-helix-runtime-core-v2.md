# Helix Runtime v2 实施计划 - AI Provider + MCP Server

- Req ID: REQ-20260415-helix-runtime-core
- Plan Version: v2
- Status: in_progress
- Created At: 2026-04-16
- Updated At: 2026-04-16

## 实施范围

在 v1 基础上，新增：

1. AI Provider 抽象层（意图检测 + 用户 AI）
2. MCP Server 实现（接入 Claude Code）

## 涉及模块与文件

```text
helix/
├── providers/
│   ├── __init__.py
│   ├── base.py              # Provider 基类和接口定义
│   ├── ollama.py            # Ollama Provider
│   ├── deepseek.py          # DeepSeek Provider
│   ├── minimax.py           # Minimax Provider (Code Plan)
│   ├── volcengine.py        # 火山引擎 Provider (Code Plan)
│   └── registry.py          # Provider 注册表
├── mcp/
│   ├── __init__.py
│   ├── server.py            # MCP Server 主入口
│   ├── skills.py            # Skill 定义
│   ├── functions.py         # Function 定义
│   └── handlers.py          # MCP 消息处理器
├── config.py                # 更新：添加 Provider 配置
└── main.py                  # 更新：注册 MCP 路由
```

## 数据模型

### Provider 配置

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum


class ProviderType(str, Enum):
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    MINIMAX = "minimax"
    VOLCENGINE = "volcengine"


class IntentDetectionConfig(BaseModel):
    """Intent Detection Provider 配置"""
    type: ProviderType
    model: str
    base_url: str
    api_key: Optional[str] = None


class UserAIConfig(BaseModel):
    """User AI Provider 配置"""
    type: ProviderType
    model: str
    base_url: str
    api_key: Optional[str] = None


class HelixConfig(BaseModel):
    """Helix Runtime 配置"""
    intent_provider: IntentDetectionConfig
    user_provider: UserAIConfig
    mcp_server_enabled: bool = True
    mcp_server_port: int = 8765
```

### Intent 类型

```python
class IntentType(str, Enum):
    """意图类型"""
    CHAT = "chat"                    # 普通对话
    CONTINUE = "continue"             # 继续之前的对话
    WORKFLOW_DOCUMENT = "workflow_document"  # 文档生成
    WORKFLOW_REVISION = "workflow_revision"  # 修订任务
    CODE_GENERATION = "code_generation"      # 代码生成
    ANALYSIS = "analysis"            # 分析任务
    UNKNOWN = "unknown"               # 未知意图


class IntentResult(BaseModel):
    """意图检测结果"""
    intent: IntentType
    confidence: float  # 0.0 - 1.0
    reasoning: str
    suggested_provider: Optional[str] = None
```

### Chat Request/Response

```python
class HelixChatRequest(BaseModel):
    """Helix Chat 请求"""
    session_id: str
    user_input: str
    system_prompt: Optional[str] = None
    force_provider: Optional[str] = None  # 强制使用特定 Provider


class HelixChatResponse(BaseModel):
    """Helix Chat 响应"""
    session_id: str
    response: str
    intent: IntentType
    provider_used: str
    model_used: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
```

## 接口设计

### 1. Intent Detection

```
POST /api/v1/intent/detect
```

Request:
```json
{
  "user_input": "continue where we left off",
  "context": {
    "session_id": "xxx",
    "message_history": [...]
  }
}
```

Response:
```json
{
  "intent": "continue",
  "confidence": 0.95,
  "reasoning": "User is asking to continue the previous conversation",
  "suggested_provider": "ollama"
}
```

### 2. Chat (统一入口)

```
POST /api/v1/chat
```

Request:
```json
{
  "session_id": "xxx",
  "user_input": "Write a Python function to sort a list",
  "system_prompt": "You are a helpful assistant",
  "force_provider": null
}
```

Response:
```json
{
  "session_id": "xxx",
  "response": "Here is a Python function...",
  "intent": "code_generation",
  "provider_used": "minimax",
  "model_used": "abab6.5s-chat",
  "tokens_used": 1234,
  "latency_ms": 500
}
```

### 3. Provider 管理

```
GET /api/v1/providers
POST /api/v1/providers/test
GET /api/v1/providers/{type}/models
```

## MCP Server 设计

### 暴露的 Skills

```python
SKILLS = [
    {
        "name": "helix-chat",
        "description": "使用 Helix Runtime 进行对话，自动意图检测和路由",
        "parameters": {
            "session_id": "string",
            "message": "string"
        }
    },
    {
        "name": "helix-code",
        "description": "强制使用 Code Plan AI（Minimax/火山引擎）进行代码生成",
        "parameters": {
            "session_id": "string",
            "code_request": "string",
            "language": "string"
        }
    },
    {
        "name": "helix-continue",
        "description": "继续之前的对话上下文",
        "parameters": {
            "session_id": "string",
            "message": "string"
        }
    }
]
```

### 暴露的 Functions

```python
FUNCTIONS = [
    {
        "name": "create_session",
        "description": "创建新的 Helix Session",
        "parameters": {
            "session_id": "optional string"
        }
    },
    {
        "name": "get_session_state",
        "description": "获取 Session 状态",
        "parameters": {
            "session_id": "string"
        }
    },
    {
        "name": "switch_provider",
        "description": "切换当前 Session 使用的 AI Provider",
        "parameters": {
            "session_id": "string",
            "provider_type": "string"
        }
    }
]
```

## 实施步骤

### Step 1: Provider 抽象层

- 目标: 实现 Provider 基类和接口定义
- 改动:
  - 创建 `helix/providers/base.py`（BaseProvider 抽象类）
  - 创建 `helix/providers/registry.py`（Provider 注册表）
  - 实现统一的 `chat()` 和 `detect_intent()` 接口
- 完成标准:
  - Provider 接口统一
  - 可以动态注册和获取 Provider

### Step 2: 实现 Ollama Provider

- 目标: 实现 Ollama Provider
- 改动:
  - 创建 `helix/providers/ollama.py`
  - 支持 OpenAI 兼容格式的 API 调用
- 完成标准:
  - 可以调用本地或远程 Ollama
  - 支持 chat 和 embed 接口

### Step 3: 实现 DeepSeek Provider

- 目标: 实现 DeepSeek Provider
- 改动:
  - 创建 `helix/providers/deepseek.py`
  - 支持 DeepSeek API 格式
- 完成标准:
  - 可以调用 DeepSeek API
  - 支持 chat 接口

### Step 4: 实现 Minimax Provider (Code Plan)

- 目标: 实现 Minimax Provider
- 改动:
  - 创建 `helix/providers/minimax.py`
  - 支持 Minimax Code Plan API
- 完成标准:
  - 可以调用 Minimax API
  - 支持 chat 接口

### Step 5: 实现火山引擎 Provider (Code Plan)

- 目标: 实现火山引擎 Provider
- 改动:
  - 创建 `helix/providers/volcengine.py`
  - 支持火山引擎 API
- 完成标准:
  - 可以调用火山引擎 API
  - 支持 chat 接口

### Step 6: Intent Detection 集成

- 目标: 将 Intent Detection 集成到 Chat 流程
- 改动:
  - 更新 `helix/api/chat.py`
  - 添加 Intent Detection 步骤
- 完成标准:
  - 用户输入先经过 Intent Detection
  - 根据意图路由到不同处理流程

### Step 7: MCP Server 实现

- 目标: 实现 MCP Server
- 改动:
  - 创建 `helix/mcp/server.py`
  - 创建 `helix/mcp/skills.py`
  - 创建 `helix/mcp/functions.py`
  - 创建 `helix/mcp/handlers.py`
- 完成标准:
  - MCP Server 可以启动
  - 暴露 Skills 和 Functions

### Step 8: 配置更新

- 目标: 更新配置管理
- 改动:
  - 更新 `helix/config.py`
  - 支持从环境变量读取 Provider 配置
- 完成标准:
  - 配置可以从 YAML/ENV 加载
  - Provider 可以动态切换

### Step 9: 集成测试

- 目标: 验证完整流程
- 改动:
  - 更新 `helix/tests/test_integration.py`
  - 测试 Intent Detection
  - 测试多 Provider 切换
  - 测试 MCP Server
- 完成标准:
  - 意图检测正确工作
  - Provider 切换正常
  - MCP Server 可用

## 验证方案

### 单元测试

- 每个 Provider 实现都有对应的单元测试
- Provider 接口测试
- 配置加载测试

### 手动验证

1. 启动 Ollama（如果本地）
2. 测试 Intent Detection
3. 测试不同 Provider 的 Chat
4. 测试 Claude Code MCP 接入

### 验收标准检查清单

- [ ] Intent Detection - 意图检测 Provider 可配置并正常工作
- [ ] User AI Provider - 用户 AI Provider 可配置并正常工作
- [ ] Multi-Provider Support - 支持 Ollama、DeepSeek、Minimax、火山引擎
- [ ] MCP Server - 可作为 MCP Server 接入 Claude Code
- [ ] Claude Code Integration - Claude Code 可通过 Helix Runtime 使用指定 Provider

## 风险与回退

### 风险 1: 不同 Provider API 格式差异

- 风险: 各 Provider 的 API 格式可能不同，需要适配
- 应对: 使用统一的抽象接口，内部实现针对每个 Provider 的适配器

### 风险 2: MCP 协议兼容性

- 风险: MCP 协议可能有版本差异
- 应对: 使用标准 MCP SDK，逐步适配

### 回退方案

如果某步遇到阻塞：
- 可以先实现核心的 Ollama Provider
- MCP Server 可以后续迭代
