# Helix Runtime

轻量级 AI 应用运行时基础设施，支持多 Provider、意图检测和 Claude Code MCP 集成。

## 特性

- **多 AI Provider 支持**：Ollama、DeepSeek、Minimax、火山引擎
- **意图检测**：自动识别用户输入类型（继续、修改、问答等）
- **状态管理**：多轮对话状态持久化
- **Workflow 引擎**：Document、Revision 等处理流程
- **MCP Server**：接入 Claude Code，暴露 Skills 和 Functions
- **前端界面**：可视化配置和状态监控

## 安装

```bash
pip install -e ".[dev]"
```

## 快速开始

### 1. 启动服务

```bash
# 启动完整服务（前端 + API）
helix run

# 或直接使用 uvicorn
uvicorn helix.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 使用前端界面。

### 2. 配置 Provider

```bash
helix setup
```

按提示配置：
- Intent Detection Provider（用于意图识别）
- User AI Provider（实际使用的 AI）

### 3. 接入 Claude Code

```bash
helix setup --mcp
```

或手动添加到 `~/.claude/mcp.json`：

```json
{
  "mcpServers": {
    "helix-runtime": {
      "command": "helix",
      "args": ["mcp"]
    }
  }
}
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `helix run` | 启动完整服务（前端 + API） |
| `helix mcp` | 仅作为 MCP Server 运行 |
| `helix setup` | 交互式配置 Provider 和 MCP |
| `helix setup --mcp` | 仅配置 MCP |
| `helix version` | 显示版本 |

## API 文档

启动服务后访问：
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc
- MCP Endpoint：http://localhost:8000/mcp

## 使用文档

- [Windows 使用指南](docs/usage-windows.md)
- [Linux/macOS 使用指南](docs/usage-linux-mac.md)
- [智能体中断恢复与切换协作规则](docs/agent-handoff-rules.md)

## 开发文档

- [技术规格文档](AI%20Runtime%20Infrastructure%20Technical%20Specification.md)
- [需求文档](docs/requirements/REQ-20260415-helix-runtime-core.md)
- [实施计划](docs/plans/PLAN-REQ-20260415-helix-runtime-core-v1.md)
- [进度记录](docs/progress/PROGRESS-REQ-20260415-helix-runtime-core.md)
