"""
Helix Runtime - CLI 模块

支持以下命令：
- helix run: 启动完整服务（前端 + API）
- helix mcp: 作为 MCP Server 运行
- helix setup: 配置 Provider 和 MCP
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="helix",
        description="Helix Runtime - AI 应用运行时基础设施",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # run 命令 - 默认启动完整服务
    run_parser = subparsers.add_parser("run", help="运行 Helix Runtime（前端 + API）")
    run_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    run_parser.add_argument("--port", type=int, default=8000, help="监听端口")
    run_parser.add_argument("--reload", action="store_true", help="热重载")
    run_parser.set_defaults(func=run_server)

    # mcp 命令 - MCP 模式
    mcp_parser = subparsers.add_parser("mcp", help="作为 MCP Server 运行（供 Claude Code 调用）")
    mcp_parser.add_argument("--http", action="store_true", help="使用 HTTP 模式而非 stdio 模式")
    mcp_parser.add_argument("--host", default="0.0.0.0", help="HTTP 模式监听地址")
    mcp_parser.add_argument("--port", type=int, default=8765, help="HTTP 模式监听端口")
    mcp_parser.add_argument("--reload", action="store_true", help="HTTP 模式热重载")
    mcp_parser.set_defaults(func=run_mcp)

    # setup 命令 - 配置
    setup_parser = subparsers.add_parser("setup", help="配置 Provider 和 MCP")
    setup_parser.add_argument("--mcp", action="store_true", help="仅配置 MCP")
    setup_parser.add_argument("--provider", action="store_true", help="仅配置 Provider")
    setup_parser.add_argument(
        "--global",
        dest="global_install",
        action="store_true",
        help="全局安装 MCP（添加到 ~/.claude/mcp.json）",
    )
    setup_parser.set_defaults(func=run_setup)

    # version 命令
    version_parser = subparsers.add_parser("version", help="显示版本")
    version_parser.set_defaults(func=show_version)

    args = parser.parse_args()

    if args.command is None:
        # 默认命令：启动完整服务
        run_server(args)
    else:
        args.func(args)


def run_server(args):
    """启动完整服务（前端 + API）"""
    import uvicorn
    from helix.main import app

    print(f"🚀 启动 Helix Runtime 服务...")
    print(f"   前端: http://{args.host}:{args.port}")
    print(f"   API 文档: http://{args.host}:{args.port}/docs")
    print(f"   MCP: http://{args.host}:{args.port}/mcp")

    uvicorn.run(
        "helix.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def run_mcp(args):
    """作为 MCP Server 运行"""
    if args.http:
        # HTTP 模式
        import uvicorn
        from helix.main import app

        print(f"🔌 启动 Helix Runtime MCP Server (HTTP 模式)...")
        print(f"   MCP 端点: http://{args.host}:{args.port}/mcp")
        print(f"   Skills: http://{args.host}:{args.port}/mcp/skills")
        print(f"   Functions: http://{args.host}:{args.port}/mcp/functions")

        # MCP Server 监听不同端口
        uvicorn.run(
            "helix.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    else:
        # Stdio 模式（默认，用于 Claude Code 集成）
        from helix.mcp.stdio_server import run_stdio_server
        run_stdio_server()


def run_setup(args):
    """配置 Provider 和 MCP"""
    print("🔧 Helix Runtime 配置向导")
    print("=" * 50)

    if args.mcp:
        setup_mcp()
    elif args.provider:
        setup_provider()
    else:
        # 完整配置流程
        print("\n[1/2] 配置 Provider")
        setup_provider()
        print("\n[2/2] 配置 MCP")
        setup_mcp(args.global_install)


def setup_provider():
    """交互式配置 Provider"""
    print("\n请配置 Intent Detection Provider（用于意图检测）:")
    print("(直接回车使用默认值)")

    intent_type = input("  Provider 类型 [ollama]: ").strip() or "ollama"
    intent_model = input("  模型名称 [qwen2.5-coder]: ").strip() or "qwen2.5-coder"
    intent_url = input("  API 地址 [http://localhost:11434/v1]: ").strip() or "http://localhost:11434/v1"
    intent_key = input("  API Key (可选): ").strip()

    print("\n请配置 User AI Provider（用户实际使用的 AI）:")
    user_type = input("  Provider 类型 [minimax]: ").strip() or "minimax"
    user_model = input("  模型名称 [abab6.5s-chat]: ").strip() or "abab6.5s-chat"
    user_url = input("  API 地址: ").strip()
    user_key = input("  API Key: ").strip()

    # 生成配置
    config = {
        "intent_provider": {
            "type": intent_type,
            "model": intent_model,
            "base_url": intent_url,
        },
        "user_provider": {
            "type": user_type,
            "model": user_model,
            "base_url": user_url,
        },
    }

    if intent_key:
        config["intent_provider"]["api_key"] = intent_key
    if user_key:
        config["user_provider"]["api_key"] = user_key

    # 保存配置
    config_dir = Path.home() / ".config" / "helix"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✅ 配置已保存到: {config_file}")


def setup_mcp(global_install: bool = False):
    """配置 MCP"""
    mcp_config_path = Path.home() / ".claude" / "mcp.json"

    # 读取或创建配置
    if mcp_config_path.exists():
        with open(mcp_config_path) as f:
            mcp_config = json.load(f)
    else:
        mcp_config = {"mcpServers": {}}

    # 检查是否已存在
    if "helix-runtime" in mcp_config.get("mcpServers", {}):
        print("\n⚠️  helix-runtime MCP 已存在配置中")
        overwrite = input("是否覆盖? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("跳过 MCP 配置")
            return

    # 添加 helix-runtime 配置
    mcp_config.setdefault("mcpServers", {})["helix-runtime"] = {
        "command": "helix",
        "args": ["mcp"],
        "env": {
            "HELIX_CONFIG": str(Path.home() / ".config" / "helix" / "config.json"),
        },
    }

    # 确保目录存在
    mcp_config_path.parent.mkdir(parents=True, exist_ok=True)

    # 写回配置
    with open(mcp_config_path, "w") as f:
        json.dump(mcp_config, f, indent=2)

    print(f"\n✅ MCP 配置已添加到: {mcp_config_path}")
    print("\n请重启 Claude Code 以加载新的 MCP 配置")


def show_version(args):
    """显示版本"""
    from helix import __version__
    print(f"Helix Runtime v{__version__}")


if __name__ == "__main__":
    main()
