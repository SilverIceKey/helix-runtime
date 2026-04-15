"""
Helix Runtime - CLI 入口

Usage:
    helix run         # 启动完整服务（前端 + API）
    helix mcp        # 作为 MCP Server 运行
    helix setup      # 配置 Provider 和 MCP
"""

import sys
from helix.cli import main

if __name__ == "__main__":
    main()
