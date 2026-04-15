# AI 接口统一文档（完整版 V1）

> 面向 AI 应用基础设施、网关层、SDK 封装、Agent 系统的完整接口整理文档。
> 这次不给你搞那种能看不能用的样子货，直接按工程可落地标准来。

---

# 1. 文档目标

本文档用于统一整理当前主流三类接口协议，并给出可直接落地的请求 / 响应结构、类型定义、错误处理规范与统一抽象方案。

覆盖范围：

- OpenAI Compatible V1 接口
- Claude Code / Coding Agent 接口
- Planner / Code Plan 接口
- Tool Calling 协议
- Streaming 协议
- Error 协议
- Adapter 统一抽象

---

# 2. 接口分类

| 类型 | 路径风格 | 用途 | 流式 | Tool支持 |
|---|---|---|---|---|
| Chat Completion | /v1/chat/completions | 通用对话 | 支持 | 支持 |
| Responses | /v1/responses | 新一代统一接口 | 强支持 | 强支持 |
| Claude Code | /agent/code | 编码代理 | 强流式 | 强支持 |
| Planner | /plan/create | 任务规划 | 可选 | 一般 |

---

# 3. OpenAI Compatible V1

## 3.1 Chat Completions

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer <api_key>
```

## Request

```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system",
      "content": "You are an AI coding assistant"
    },
    {
      "role": "user",
      "content": "帮我写一个fastapi接口"
    }
  ],
  "temperature": 0.3,
  "max_tokens": 4096,
  "stream": true,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "读取文件",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string"
            }
          },
          "required": ["path"]
        }
      }
    }
  ]
}
```

## Response

```json
{
  "id": "chatcmpl_xxx",
  "object": "chat.completion",
  "created": 1710000000,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "下面是 FastAPI 示例"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 300,
    "total_tokens": 420
  }
}
```

---

## 3.2 Responses API（推荐统一层）

```http
POST /v1/responses
```

```json
{
  "model": "gpt-4.1",
  "input": "实现一个带JWT鉴权的接口",
  "tools": [],
  "stream": true
}
```

返回：

```json
{
  "id": "resp_xxx",
  "status": "completed",
  "output": [
    {
      "type": "message",
      "content": [
        {
          "type": "output_text",
          "text": "完整实现如下"
        }
      ]
    }
  ]
}
```

这层建议作为你自己的统一 Provider Adapter 基准层。

别再死抱 chat completions，不然后面 tool / multimodal / agent 全得重构，纯属给未来自己埋雷。

---

# 4. Claude Code 类接口

这类不是普通聊天接口，本质是 **Agent Runtime Protocol**。

## Request

```json
{
  "task": "重构当前仓库中的认证模块",
  "workspace": "/repo/project",
  "context": {
    "branch": "main",
    "language": "python"
  },
  "tools": [
    "read_file",
    "edit_file",
    "bash",
    "search_code"
  ],
  "stream": true
}
```

## Response

```json
{
  "status": "running",
  "steps": [
    {
      "type": "tool_call",
      "tool": "read_file",
      "args": {
        "path": "auth/service.py"
      }
    },
    {
      "type": "patch",
      "file": "auth/service.py",
      "diff": "@@ ..."
    }
  ]
}
```

---

# 5. Planner / Code Plan 接口

这个必须独立，不要和 chat 混。

## Request

```json
{
  "goal": "构建企业级RAG系统",
  "constraints": [
    "必须支持stream",
    "必须支持缓存"
  ],
  "context": {
    "stack": "python fastapi redis"
  }
}
```

## Response

```json
{
  "plan": [
    {
      "step": 1,
      "name": "设计检索层"
    },
    {
      "step": 2,
      "name": "设计缓存层"
    },
    {
      "step": 3,
      "name": "实现流式输出"
    }
  ]
}
```

---

# 6. Streaming 协议

建议统一 SSE。

```http
Content-Type: text/event-stream
```

```text
data: {"type":"delta","content":"hello"}

data: {"type":"delta","content":" world"}

data: [DONE]
```

统一格式建议：

```ts
interface StreamChunk {
  type: "delta" | "tool_call" | "done" | "error"
  content?: string
  tool?: string
  args?: Record<string, any>
}
```

---

# 7. Tool Call 协议

```json
{
  "type": "tool_call",
  "tool_name": "search_docs",
  "arguments": {
    "query": "fastapi jwt"
  }
}
```

Tool Result:

```json
{
  "type": "tool_result",
  "tool_name": "search_docs",
  "result": "found 5 docs"
}
```

---

# 8. 错误协议（必须统一）

很多人这里写得跟屎一样，后面排查线上问题直接火化。

统一：

```json
{
  "error": {
    "code": "MODEL_TIMEOUT",
    "message": "upstream timeout",
    "provider": "openai",
    "retryable": true
  }
}
```

建议错误码：

```text
INVALID_REQUEST
MODEL_TIMEOUT
RATE_LIMIT
TOOL_EXECUTION_FAILED
CONTEXT_OVERFLOW
PROVIDER_UNAVAILABLE
STREAM_BROKEN
```

---

# 9. 推荐统一 TypeScript 抽象

```ts
interface UnifiedAIRequest {
  type: "chat" | "agent" | "plan"
  model?: string
  input: string
  stream?: boolean
  tools?: Tool[]
  metadata?: Record<string, any>
}

interface UnifiedAIResponse {
  id: string
  status: string
  output: any
  usage?: TokenUsage
}
```

---

# 10. 推荐架构

```text
Client SDK
   ↓
Gateway API
   ↓
Provider Adapter Layer
   ├── OpenAI Adapter
   ├── Claude Adapter
   ├── Planner Adapter
   ↓
Tool Runtime
   ↓
Business Services
```

这一层你必须提前拆干净。

否则后面 chat、agent、workflow、tool 调用全揉一起，代码会长成你半夜看了都想报警的样子。

