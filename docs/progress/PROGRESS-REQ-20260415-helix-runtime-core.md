# Helix Runtime 核心运行时基础设施 进度记录

- Req ID: REQ-20260415-helix-runtime-core
- Status: in_progress (v3: 前端 + API 文档)
- Created At: 2026-04-15
- Updated At: 2026-04-16

## 当前快照

- Current Phase: v3 前端重构完成
- Current Task: 等待用户测试验证
- Last Completed: 前端重构（调试模式 + 流式输出 + 真实 API 调用）
- Next Action: 用户测试验证
- Blockers: 无

## Provider 接口配置

| Provider | API 端点 | 接口协议 | 模型 |
|----------|----------|----------|------|
| Ollama | `http://localhost:11434/v1` | OpenAI `/v1/chat/completions` | qwen2.5-coder, llama2, codellama, mistral |
| DeepSeek | `https://api.deepseek.com/v1` | OpenAI `/v1/chat/completions` | deepseek-chat, deepseek-coder |
| Minimax | `https://api.minimaxi.com/anthropic` | Claude Code `/agent/code` | minimax-2.7, minimax-2.7-highspeed |
| 火山引擎 | `https://ark.cn-beijing.volces.com/api/v3` | OpenAI `/v1/chat/completions` | doubao-seed-2.0-*, minimax-m2.5, kimi-k2.5, glm-4.7, deepseek-v3.2 |

## 关键节点记录

### [2026-04-15] v1 全部完成

- 背景: 完成计划文档的 Step 9，验证所有验收标准
- 本次完成:
  - 创建 helix/tests/test_integration.py（集成测试文件）
  - 验证多轮连续稳定（5 轮对话测试通过）
  - 验证状态正确续接（Session 状态正确恢复和续接）
  - 验证 workflow 可控（Document/Revision Workflow 正常触发和执行）
  - 验证输入不可变（用户原始输入保持不变）
  - 验证历史上下文可配置（MAX_HISTORY_TURNS 可配置）
- 验证:
  - ✅ 多轮连续稳定 - 连续 5 轮对话，上下文正确传递
  - ✅ 状态正确续接 - Session 状态正确恢复和续接
  - ✅ workflow 可控 - Document/Revision Workflow 正常触发和执行
  - ✅ 输入不可变 - 用户原始输入保持不变
  - ✅ 历史上下文可配置 - MAX_HISTORY_TURNS 可配置
- 风险/遗留: 无
- 下一步: v2 - AI Provider 层

### [2026-04-16] v2 实现 - AI Provider 抽象层

- 背景: 实现 AI Provider 抽象层，支持多种后端
- 本次完成:
  - 创建 helix/providers/base.py（BaseProvider 抽象类、ChatMode 枚举）
  - 创建 helix/providers/registry.py（Provider 注册表）
  - 创建 helix/providers/ollama.py（Ollama Provider）
  - 创建 helix/providers/deepseek.py（DeepSeek Provider）
  - 创建 helix/providers/minimax.py（Minimax Claude Code 协议）
  - 创建 helix/providers/volcengine.py（火山引擎 Doubao）
- 接口协议:
  - Ollama/DeepSeek/火山引擎: `/v1/chat/completions` (OpenAI 兼容)
  - Minimax: `/agent/code` (Claude Code 协议)
- 下一步: MCP Server 实现

### [2026-04-16] v2 实现 - MCP Server

- 背景: 实现 MCP Server，支持接入 Claude Code
- 本次完成:
  - 创建 helix/mcp/skills.py（5 个 Skill）
  - 创建 helix/mcp/functions.py（6 个 Function）
  - 创建 helix/mcp/handlers.py（MCP 消息处理器）
  - 创建 helix/mcp/server.py（MCP Server 主入口）
- 验证: Skills 5 个, Functions 6 个, MCP 挂载 /mcp

### [2026-04-16] v3 完成 - 前端界面

- 背景: 添加前端界面，支持配置和聊天
- 本次完成:
  - helix/templates/index.html - Vue 3 + Vuetify 前端
  - helix/api/config.py - 配置 API（/api/v1/config, /api/v1/mcp）
  - helix/api/chat.py - 流式聊天 API（/api/v1/chat/stream）
  - helix/cli.py - CLI 命令（run/mcp/setup/version）
  - helix/__main__.py - CLI 入口
- 前端功能:
  - 调试模式开关（显示请求/响应详情）
  - 流式输出（thinking 过程实时显示）
  - 真实 API 调用
  - Provider 配置（Intent Detection / User AI）
  - MCP 配置（全局/本地）
- 下一步: 测试验证
