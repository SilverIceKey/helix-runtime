# Helix Runtime

轻量级 AI 应用运行时基础设施。

## 快速开始

### 安装依赖

```bash
pip install -e ".[dev]"
```

### 运行服务

```bash
uvicorn helix.main:app --reload
```

访问 http://localhost:8000/docs 查看 API 文档。

## 文档

- [智能体中断恢复与切换协作规则](docs/agent-handoff-rules.md)
- [技术规格文档](AI%20Runtime%20Infrastructure%20Technical%20Specification.md)
- [需求文档](docs/requirements/REQ-20260415-helix-runtime-core.md)
- [实施计划](docs/plans/PLAN-REQ-20260415-helix-runtime-core-v1.md)
- [进度记录](docs/progress/PROGRESS-REQ-20260415-helix-runtime-core.md)
