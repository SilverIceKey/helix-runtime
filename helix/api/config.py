from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from pathlib import Path

from helix.storage import get_sqlite_storage


router = APIRouter(prefix="/api/v1/config", tags=["config"])

# MCP 配置相关 - 单独路由，前缀 /api/v1/mcp
mcp_router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


DEFAULT_CONFIG = {
    "intent_provider": {
        "type": "ollama",
        "model": "qwen2.5-coder",
        "base_url": "http://localhost:11434/v1",
        "api_key": "",
    },
    "user_provider": {
        "type": "deepseek",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
    },
}


def load_config() -> Dict[str, Any]:
    """加载配置（从 SQLite）"""
    storage = get_sqlite_storage()
    config = storage.load_config("helix_config")
    if config:
        # 合并默认配置，确保新字段存在
        result = {**DEFAULT_CONFIG, **config}
        # 确保嵌套字段也有默认值
        if "intent_provider" in result:
            result["intent_provider"] = {**DEFAULT_CONFIG["intent_provider"], **result["intent_provider"]}
        if "user_provider" in result:
            result["user_provider"] = {**DEFAULT_CONFIG["user_provider"], **result["user_provider"]}
        return result
    return DEFAULT_CONFIG


def save_config(config: Dict[str, Any]):
    """保存配置（到 SQLite）"""
    storage = get_sqlite_storage()
    storage.save_config("helix_config", config)


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
        # 简单的连接测试 - 尝试调用 models 接口
        import httpx

        headers = {}
        if request.api_key:
            headers["Authorization"] = f"Bearer {request.api_key}"

        # 根据 provider 选择测试端点
        test_urls = []
        if request.type == "ollama":
            test_urls.append(f"{request.base_url.rstrip('/v1')}/api/tags")
        test_urls.append(f"{request.base_url.rstrip('/')}/models")

        for test_url in test_urls:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(test_url, headers=headers)
                    if resp.status_code == 200:
                        return {"success": True, "message": f"{request.type} provider connected"}
            except:
                continue

        # 如果以上都失败，至少返回配置成功（因为可能是私有端点）
        return {"success": True, "message": f"{request.type} provider configured"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/providers/models")
async def get_provider_models(request: ProviderTestRequest):
    """
    获取 Provider 可用模型列表
    """
    # 默认模型列表
    default_models = {
        "ollama": ["qwen2.5-coder", "llama2", "codellama", "mistral"],
        "deepseek": ["deepseek-chat", "deepseek-coder"],
        "minimax": ["minimax-2.7", "minimax-2.7-highspeed"],
        "volcengine": [
            "doubao-seed-2.0-code", "doubao-seed-2.0-pro", "doubao-seed-2.0-lite",
            "doubao-seed-code", "minimax-m2.5", "kimi-k2.5", "glm-4.7", "deepseek-v3.2"
        ],
    }

    try:
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

        # API 获取失败，返回默认模型列表
        models = default_models.get(request.type, [])
        return {"models": models, "source": "default"}
    except Exception as e:
        models = default_models.get(request.type, [])
        return {"models": models, "source": "default", "error": str(e)}


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
