# Linux / macOS 使用指南

本文档介绍如何在 Linux 或 macOS 系统上运行 Helix Runtime。

## 前置要求

### 1. 安装 Python

推荐使用 Python 3.11 或更高版本。

**macOS - 使用 Homebrew**
```bash
brew install python@3.11
```

**Linux - 使用包管理器**

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

Fedora/RHEL:
```bash
sudo dnf install python3.11
```

**验证安装**
```bash
python3 --version
# 应显示 Python 3.11.x
```

### 2. 安装 Git（如果还没有）

```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt install git
```

## 安装与运行

### 1. 克隆项目

```bash
git clone <repository-url>
cd helix-runtime
```

### 2. 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -e ".[dev]"
```

### 4. 运行服务

启动完整服务（前端 + API）：

```bash
helix run
```

或者使用 `helix` 命令：

```bash
helix run --host 0.0.0.0 --port 8000
```

### 5. 访问前端

打开浏览器访问：http://localhost:8000

前端界面提供：
- 服务状态监控
- Provider 配置管理
- MCP 配置教程
- API 文档链接

## Claude Code MCP 配置教程

Helix Runtime 可以作为 MCP Server 接入 Claude Code。

### 方式一：自动配置（推荐）

```bash
helix setup
```

这将启动交互式配置向导：
1. 配置 Intent Detection Provider（用于意图检测）
2. 配置 User AI Provider（用户实际使用的 AI）
3. 自动配置 MCP

### 方式二：手动配置

#### 步骤 1：安装 Helix Runtime

确保 `helix` 命令可用：

```bash
pip install -e .
```

#### 步骤 2：获取 MCP 配置

访问 http://localhost:8000 查看 MCP 配置 JSON，或直接使用以下配置：

```json
{
  "mcpServers": {
    "helix-runtime": {
      "command": "helix",
      "args": ["mcp"],
      "env": {
        "HELIX_CONFIG": "~/.config/helix/config.json"
      }
    }
  }
}
```

#### 步骤 3：配置 Claude Code

**方法 A：通过 Claude Code 设置**

1. 打开 Claude Code
2. 设置 → MCP Servers → 添加
3. 粘贴上面的 JSON 配置

**方法 B：编辑配置文件**

1. 打开 `~/.claude/mcp.json`（或创建）
2. 将 `helix-runtime` 配置添加到 `mcpServers` 对象中

```bash
# 使用编辑器打开配置文件
nano ~/.claude/mcp.json
# 或
vim ~/.claude/mcp.json
```

示例完整配置：

```json
{
  "mcpServers": {
    "helix-runtime": {
      "command": "helix",
      "args": ["mcp"],
      "env": {
        "HELIX_CONFIG": "~/.config/helix/config.json"
      }
    }
  }
}
```

#### 步骤 4：重启 Claude Code

配置完成后，重启 Claude Code 以加载 MCP 服务器。

### 验证 MCP 配置

在 Claude Code 中测试：

```
/skills
```

应该能看到 helix-chat, helix-code, helix-continue, helix-document, helix-revision 等 Skills。

## API 文档

启动服务后访问：
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc
- MCP Endpoint：http://localhost:8000/mcp

## 使用方式

### 方式一：通过前端界面

访问 http://localhost:8000 使用图形界面：
- 查看服务状态
- 配置 Provider
- 获取 MCP 配置

### 方式二：通过 HTTP API

```bash
# 创建 Session
curl -X POST http://localhost:8000/api/v1/sessions

# 发送 Chat 请求
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/chat \
     -H "Content-Type: application/json" \
     -d '{"user_input": "Hello"}'
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

### Q: pip install 报错

**解决方案**：确保 pip 是最新版本。

```bash
python3 -m pip install --upgrade pip
```

### Q: helix 命令找不到

**解决方案**：确保以开发模式安装。

```bash
pip install -e .
```

### Q: zsh: command not found: helix

**解决方案**：确保虚拟环境已激活，或将 pip install 的 bin 目录添加到 PATH。

```bash
# 永久添加 PATH（添加到 ~/.zshrc）
echo 'export PATH="$HOME/Library/Python/3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## 项目结构

```
helix-runtime/
├── helix/
│   ├── main.py              # FastAPI 应用入口
│   ├── cli.py               # CLI 命令
│   ├── config.py            # 配置管理
│   ├── api/                 # API 路由
│   ├── core/                # 核心模块
│   ├── storage/             # 存储层
│   ├── models/              # 数据模型
│   ├── providers/           # AI Provider 层
│   ├── mcp/                 # MCP Server
│   ├── templates/           # 前端模板
│   └── tests/               # 测试
├── docs/                    # 文档
├── pyproject.toml           # 项目配置
└── README.md                # 项目说明
```

## CLI 命令

```bash
# 启动完整服务（前端 + API）
helix run

# 仅启动 MCP Server
helix mcp

# 交互式配置 Provider 和 MCP
helix setup

# 仅配置 Provider
helix setup --provider

# 仅配置 MCP
helix setup --mcp

# 全局安装 MCP
helix setup --global

# 显示版本
helix version
```

## 后台运行

如果需要在后台运行服务，可以使用 `nohup` 或 `screen`/`tmux`：

### 使用 nohup

```bash
nohup helix run --host 0.0.0.0 --port 8000 > helix.log 2>&1 &
```

### 使用 tmux（推荐）

```bash
# 创建新的 tmux 会话
tmux new -s helix

# 在会话中运行
helix run --host 0.0.0.0 --port 8000

# 分离会话：按 Ctrl+B，然后按 D

# 重新连接会话
tmux attach -t helix
```
