# Windows 使用指南

本文档介绍如何在 Windows 系统上运行 Helix Runtime。

## 前置要求

### 1. 安装 Python

推荐使用 Python 3.11 或更高版本。

**方式一：使用 Python 官网安装包**
- 访问 https://www.python.org/downloads/
- 下载并安装 Python 3.11+
- 安装时勾选 "Add Python to PATH"

**方式二：使用 winget（Windows 10/11）**
```powershell
winget install Python.Python.3.11
```

**方式三：使用 Chocolatey**
```powershell
choco install python311
```

**验证安装**
```powershell
python --version
# 应显示 Python 3.11.x
```

### 2. 安装 Git（如果还没有）

```powershell
winget install Git.Git
```

## 安装与运行

### 1. 克隆项目

```powershell
git clone <repository-url>
cd helix-runtime
```

### 2. 创建虚拟环境（推荐）

```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate
```

### 3. 安装依赖

```powershell
pip install -e ".[dev]"
```

### 4. 运行服务

```powershell
uvicorn helix.main:app --reload --host 0.0.0.0 --port 8000
```

或者使用 Python 直接运行：

```powershell
python -m uvicorn helix.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问 API 文档

打开浏览器访问：http://localhost:8000/docs

## 使用方式

### 方式一：通过 HTTP API 调用

Helix Runtime 提供 REST API，可以通过 HTTP 请求调用。

**创建 Session**
```powershell
# 使用 curl
curl -X POST http://localhost:8000/api/v1/sessions

# 使用 PowerShell
Invoke-RestMethod -Method POST -Uri http://localhost:8000/api/v1/sessions
```

**发送 Chat 请求**
```powershell
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/chat `
     -H "Content-Type: application/json" `
     -d '{"user_input": "Hello"}'
```

### 方式二：作为 Claude Code/opencode MCP 服务器

Helix Runtime 可以作为 MCP (Model Context Protocol) 服务器接入 Claude Code 或 opencode，实现 AI 运行时能力扩展。

**配置 MCP 服务器**

在 Claude Code 的配置中添加：

```json
{
  "mcpServers": {
    "helix-runtime": {
      "command": "uvicorn",
      "args": ["helix.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    }
  }
}
```

**或使用 Python 直接启动 MCP 服务器**

```powershell
python -m helix.mcp_server
```

### 方式三：作为独立 Python 包使用

```python
from helix.storage import get_storage
from helix.core import get_trigger, get_context_manager, get_state_engine, get_workflow_runtime
from helix.models import MessageRole, WorkflowType

# 初始化
storage = get_storage()
trigger = get_trigger()
context_manager = get_context_manager()
state_engine = get_state_engine()
workflow_runtime = get_workflow_runtime()

# 创建 Session
session = storage.create_session("my-session")

# 评估用户输入
trigger_result = trigger.evaluate("continue")
print(f"Trigger mode: {trigger_result.mode}")

# 执行 Workflow
result = workflow_runtime.execute(WorkflowType.DOCUMENT, {"topic": "Test"})
print(f"Workflow success: {result.success}")
```

## 常见问题

### Q: pip install 报错 " Microsoft Visual C++ 14.0 is required"

**解决方案**：安装 Visual Studio Build Tools 或使用预编译包。

```powershell
# 使用预编译包安装 wheel
pip install --only-binary :all: fastapi
```

### Q: uvicorn 启动报错 "Port 8000 is already in use"

**解决方案**：更换端口或关闭占用端口的进程。

```powershell
# 更换端口
uvicorn helix.main:app --reload --port 8001
```

### Q: 虚拟环境激活失败

**解决方案**：确保使用 PowerShell 或 CMD（不是 Git Bash），并以管理员权限运行。

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\activate
```

## 项目结构

```
helix-runtime/
├── helix/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── api/                 # API 路由
│   ├── core/                # 核心模块
│   ├── storage/             # 存储层
│   ├── models/              # 数据模型
│   └── tests/               # 测试
├── docs/                    # 文档
├── pyproject.toml           # 项目配置
└── README.md                 # 项目说明
```

## 配置说明

配置文件 `.env`（从 `.env.example` 复制）：

```ini
# 应用基本配置
DEBUG=true

# 运行时约束
MAX_RECENT_TURNS=5
MAX_HISTORY_TURNS=5
MAX_WORKFLOW_STEPS=3
MAX_PROMPT_TOKENS=4096
MAX_WORKFLOW_RETRY=2
```
