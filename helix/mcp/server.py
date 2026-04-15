"""
Helix Runtime - MCP Server

作为 MCP Server 接入 Claude Code
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from helix.mcp.handlers import MCPHandlers
from helix.mcp.skills import get_skills
from helix.mcp.functions import get_functions
from helix.providers import (
    ProviderRegistry,
    ProviderConfig,
    ProviderType,
    set_intent_provider,
    set_user_provider,
)


# MCP App
mcp_app = FastAPI(title="Helix Runtime MCP Server")
handlers = MCPHandlers()


class MCPRequest(BaseModel):
    """MCP 请求"""
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP 响应"""
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[Any] = None


@mcp_app.post("/mcp")
async def handle_mcp(request: MCPRequest) -> MCPResponse:
    """
    处理 MCP 请求

    MCP 协议使用 JSON-RPC 2.0
    """
    result = await handlers.handle(request.method, request.params)

    if "error" in result:
        return MCPResponse(
            id=request.id,
            error=result["error"]
        )

    return MCPResponse(
        id=request.id,
        result=result.get("result")
    )


@mcp_app.get("/mcp")
async def handle_mcp_get():
    """MCP GET 端点（用于检查）"""
    return {
        "service": "Helix Runtime MCP Server",
        "version": "0.2.0",
        "status": "running"
    }


@mcp_app.get("/skills")
async def list_skills():
    """列出所有可用的 Skills"""
    return {"skills": get_skills()}


@mcp_app.get("/functions")
async def list_functions():
    """列出所有可用的 Functions"""
    return {"functions": get_functions()}


# Provider 管理 API
@mcp_app.post("/providers/configure")
async def configure_providers(config: Dict[str, Any]):
    """
    配置 Provider

    配置示例：
    {
        "intent_provider": {
            "type": "ollama",
            "model": "qwen2.5-coder",
            "base_url": "http://localhost:11434/v1"
        },
        "user_provider": {
            "type": "minimax",
            "model": "abab6.5s-chat",
            "base_url": "https://api.minimax.chat/v1",
            "api_key": "your-api-key"
        }
    }
    """
    from helix.providers import ProviderRegistry

    configured = {}

    # 配置 Intent Provider
    if "intent_provider" in config:
        ip_config = config["intent_provider"]
        ip_provider_config = ProviderConfig(
            type=ProviderType(ip_config["type"]),
            model=ip_config["model"],
            base_url=ip_config.get("base_url", ""),
            api_key=ip_config.get("api_key"),
        )
        ip_provider = ProviderRegistry.create(ip_config["type"], ip_provider_config)
        set_intent_provider(ip_provider)
        configured["intent_provider"] = ip_config["type"]

    # 配置 User Provider
    if "user_provider" in config:
        up_config = config["user_provider"]
        up_provider_config = ProviderConfig(
            type=ProviderType(up_config["type"]),
            model=up_config["model"],
            base_url=up_config.get("base_url", ""),
            api_key=up_config.get("api_key"),
        )
        up_provider = ProviderRegistry.create(up_config["type"], up_provider_config)
        set_user_provider(up_provider)
        configured["user_provider"] = up_config["type"]

    return {"configured": configured}


def create_mcp_app() -> FastAPI:
    """创建 MCP App"""
    return mcp_app


# 导出
app = mcp_app
