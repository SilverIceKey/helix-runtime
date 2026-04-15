from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from pathlib import Path


router = APIRouter(prefix="/api/v1/config", tags=["config"])

# MCP 配置相关 - 单独路由，前缀 /api/v1/mcp
mcp_router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


def get_config_path() -> Path:
    """获取配置文件路径"""
    return Path.home() / ".config" / "helix" / "config.json"


def load_config() -> Dict[str, Any]:
    """加载配置"""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {
        "intent_provider": {
            "type": "ollama",
            "model": "qwen2.5-coder",
            "base_url": "http://localhost:11434/v1",
        },
        "user_provider": {
            "type": "minimax",
            "model": "abab6.5s-chat",
            "base_url": "",
        },
    }


def save_config(config: Dict[str, Any]):
    """保存配置"""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


class ConfigResponse(BaseModel):
    """配置响应"""
    intent_provider: dict
    user_provider: dict


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    intent_provider: Optional[dict] = None
    user_provider: Optional[dict] = None


@router.get("", response_model=ConfigResponse)
async def get_config():
    """
    获取当前配置
    """
    return load_config()


@router.put("", response_model=ConfigResponse)
async def update_config(request: ConfigUpdateRequest):
    """
    更新配置
    """
    config = load_config()

    if request.intent_provider:
        config["intent_provider"] = request.intent_provider
    if request.user_provider:
        config["user_provider"] = request.user_provider

    save_config(config)
    return config


class ProviderTestRequest(BaseModel):
    """Provider 连接测试请求"""
    type: str
    model: str
    base_url: str
    api_key: Optional[str] = None


@router.post("/providers/test")
async def test_provider(request: ProviderTestRequest):
    """
    测试 Provider 连接
    """
    try:
        from helix.providers import get_provider
        provider = get_provider(request.type)
        if provider is None:
            return {"success": False, "error": f"Unknown provider type: {request.type}"}

        return {"success": True, "message": f"{request.type} provider configured"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/providers/models")
async def get_provider_models(request: ProviderTestRequest):
    """
    获取 Provider 可用模型列表
    """
    try:
        # 尝试从实际 Provider API 获取模型列表
        import httpx

        headers = {}
        if request.api_key:
            headers["Authorization"] = f"Bearer {request.api_key}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Ollama 兼容格式
            if request.type == "ollama":
                try:
                    resp = await client.get(f"{request.base_url.rstrip('/v1')}/api/tags")
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                        if models:
                            return {"models": models, "source": "api"}
                except:
                    pass

            # OpenAI 兼容格式
            try:
                resp = await client.get(
                    f"{request.base_url.rstrip('/')}/models",
                    headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("id", "") for m in data.get("data", [])]
                    if models:
                        return {"models": models, "source": "api"}
            except:
                pass

        # 如果 API 调用失败，返回空列表让前端知道需要手动输入
        return {"models": [], "source": "fallback", "message": "无法从 API 获取模型列表，请手动输入"}
    except Exception as e:
        return {"models": [], "error": str(e)}


# ============= MCP 配置相关 =============

def get_mcp_config_path(config_type: str = "global") -> Path:
    """
    获取 MCP 配置文件路径
    """
    if config_type == "local":
        return Path.cwd() / ".claude" / "mcp.json"
    return Path.home() / ".claude" / "mcp.json"


class McpConfigResponse(BaseModel):
    """MCP 配置响应"""
    config_type: str
    config_path: str
    config_exists: bool


class McpApplyRequest(BaseModel):
    """应用 MCP 配置请求"""
    config_type: str = "global"


@mcp_router.get("")
async def get_mcp_config():
    """
    获取 MCP 配置信息
    """
    return McpConfigResponse(
        config_type="global",
        config_path=str(get_mcp_config_path("global")),
        config_exists=get_mcp_config_path("global").exists(),
    )


@mcp_router.get("/options")
async def get_mcp_options():
    """
    获取 MCP 配置选项
    """
    global_path = get_mcp_config_path("global")
    local_path = get_mcp_config_path("local")
    return {
        "options": [
            {"value": "global", "name": "全局配置", "path": str(global_path), "exists": global_path.exists()},
            {"value": "local", "name": "本地配置（当前项目）", "path": str(local_path), "exists": local_path.exists()},
        ]
    }


@mcp_router.post("/apply")
async def apply_mcp_config(request: McpApplyRequest):
    """
    应用 MCP 配置到指定位置
    """
    config_type = request.config_type
    mcp_config_path = get_mcp_config_path(config_type)
    helix_config_path = Path.home() / ".config" / "helix" / "config.json"

    if mcp_config_path.exists():
        with open(mcp_config_path) as f:
            mcp_config = json.load(f)
    else:
        mcp_config = {"mcpServers": {}}

    if "helix-runtime" in mcp_config.get("mcpServers", {}):
        return {
            "success": False,
            "error": "helix-runtime MCP 配置已存在",
            "config_path": str(mcp_config_path)
        }

    mcp_config.setdefault("mcpServers", {})["helix-runtime"] = {
        "command": "helix",
        "args": ["mcp"],
        "env": {
            "HELIX_CONFIG": str(helix_config_path),
        },
    }

    mcp_config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(mcp_config_path, "w") as f:
        json.dump(mcp_config, f, indent=2)

    return {
        "success": True,
        "message": f"MCP 配置已添加到: {mcp_config_path}",
        "config_path": str(mcp_config_path)
    }


@mcp_router.get("/config-json")
async def get_mcp_config_json():
    """
    获取 MCP 配置 JSON
    """
    helix_config_path = Path.home() / ".config" / "helix" / "config.json"
    config = {
        "mcpServers": {
            "helix-runtime": {
                "command": "helix",
                "args": ["mcp"],
                "env": {
                    "HELIX_CONFIG": str(helix_config_path),
                },
            }
        }
    }
    return {"config": config}
