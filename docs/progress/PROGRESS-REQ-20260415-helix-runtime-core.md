# Helix Runtime 核心运行时基础设施 进度记录

- Req ID: REQ-20260415-helix-runtime-core
- Status: in_progress (v2: AI Provider + MCP)
- Created At: 2026-04-15
- Updated At: 2026-04-16

## 当前快照

- Current Phase: v2 主要代码实现完成
- Current Task: 测试和文档完善
- Last Completed: v2 Provider 抽象层和 MCP Server 实现
- Next Action: 提交 v2 代码
- Blockers: 无
- Latest Verified: v2 模块导入测试通过
- Latest Unverified: 端到端测试

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

### [2026-04-16] v2 开始 - 扩展架构

- 背景: 扩展架构，添加 AI Provider 抽象层和 MCP Server 层
- 本次完成:
  - 更新需求文档（添加 AI Provider 和 MCP Server 需求）
  - 创建计划文档 v2（PLAN-REQ-20260415-helix-runtime-core-v2.md）
  - 创建进度文档 v2 起始状态
- 修改文件:
  - `docs/requirements/REQ-20260415-helix-runtime-core.md`
  - `docs/plans/PLAN-REQ-20260415-helix-runtime-core-v2.md`
- 验证: 文档更新完成
- 风险/遗留: 无
- 下一步: Step 1 - Provider 抽象层实现

### [2026-04-16] v2 实现 - AI Provider 抽象层

- 背景: 实现 AI Provider 抽象层，支持多种后端
- 本次完成:
  - 创建 helix/providers/base.py（BaseProvider 抽象类和接口定义）
  - 创建 helix/providers/registry.py（Provider 注册表）
  - 创建 helix/providers/ollama.py（Ollama Provider，支持 OpenAI 兼容格式）
  - 创建 helix/providers/deepseek.py（DeepSeek Provider）
  - 创建 helix/providers/minimax.py（Minimax Provider，Code Plan）
  - 创建 helix/providers/volcengine.py（火山引擎 Provider，Code Plan）
  - 创建 helix/providers/__init__.py（导出所有 Provider）
- 修改文件:
  - `helix/providers/base.py`
  - `helix/providers/registry.py`
  - `helix/providers/ollama.py`
  - `helix/providers/deepseek.py`
  - `helix/providers/minimax.py`
  - `helix/providers/volcengine.py`
  - `helix/providers/__init__.py`
- 验证: 所有 Provider 模块导入测试通过
- 风险/遗留: 各 Provider 的具体 API 格式可能需要根据实际文档调整
- 下一步: MCP Server 实现

### [2026-04-16] v2 实现 - MCP Server

- 背景: 实现 MCP Server，支持接入 Claude Code
- 本次完成:
  - 创建 helix/mcp/skills.py（Skill 定义：helix-chat, helix-code, helix-continue, helix-document, helix-revision）
  - 创建 helix/mcp/functions.py（Function 定义：create_session, get_session_state, switch_provider 等）
  - 创建 helix/mcp/handlers.py（MCP 消息处理器）
  - 创建 helix/mcp/server.py（MCP Server 主入口）
  - 创建 helix/mcp/__init__.py
  - 更新 helix/main.py（整合 MCP Server）
- 修改文件:
  - `helix/mcp/skills.py`
  - `helix/mcp/functions.py`
  - `helix/mcp/handlers.py`
  - `helix/mcp/server.py`
  - `helix/mcp/__init__.py`
  - `helix/main.py`
  - `pyproject.toml`（添加 httpx 依赖，版本更新到 0.2.0）
- 验证:
  - Skills: 5 个
  - Functions: 6 个
  - MCP Server 挂载在 /mcp 路径
- 风险/遗留: MCP 协议的具体实现可能需要根据 Claude Code 的 MCP 适配
- 下一步: 提交 v2 代码

### [2026-04-16] v3 完成 - 前端 + MCP 配置

- 背景: 添加前端界面和自动 MCP 配置
- 本次完成:
  - 创建 helix/templates/index.html（Vue 3 + Vuetify 前端）
  - 更新 helix/main.py（服务前端页面）
  - 创建 helix/api/config.py（配置 API）
  - 更新 helix/api/sessions.py（添加 list_sessions 端点）
  - 更新 docs/usage-windows.md（包含 MCP 配置教程）
  - 创建 docs/usage-linux-mac.md（包含 MCP 配置教程）
- 修改文件:
  - `helix/templates/index.html`
  - `helix/main.py`
  - `helix/api/config.py`
  - `helix/api/sessions.py`
  - `docs/usage-windows.md`
  - `docs/usage-linux-mac.md`
- 验证:
  - 前端页面可访问
  - Provider 配置功能
  - MCP 配置教程完整
- 风险/遗留: 无
- 下一步: 提交 v3 代码
