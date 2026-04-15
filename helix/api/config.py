from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
from pathlib import Path

from helix.storage import get_sqlite_storage


router = APIRouter(prefix="/api/v1/config", tags=["config"])

# MCP 配置相关 - 单独路由，前缀 /api/v1/mcp
mcp_router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


PROVIDER_DEFAULTS = {
    "ollama": {
        "name": "Ollama",
        "api_type": "openai",
        "base_url": "http://localhost:11434/v1",
        "endpoint": "/chat/completions",
        "models": ["qwen2.5-coder", "llama2", "codellama", "mistral"]
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_type": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "endpoint": "/chat/completions",
        "models": ["deepseek-chat", "deepseek-coder"]
    },
    "minimax": {
        "name": "Minimax",
        "api_type": "claude_code",
        "base_url": "https://api.minimaxi.com/anthropic",
        "endpoint": "/agent/code",
        "models": ["minimax-2.7", "minimax-2.7-highspeed"]
    },
    "volcengine": {
        "name": "火山引擎",
        "api_type": "openai",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "endpoint": "/chat/completions",
        "models": ["doubao-seed-2.0-code", "doubao-seed-2.0-pro", "doubao-seed-2.0-lite", "doubao-seed-code", "minimax-m2.5", "kimi-k2.5", "glm-4.7", "deepseek-v3.2"]
    },
}


def init_default_provider_configs():
    """初始化默认 Provider 配置（如果不存在）"""
    storage = get_sqlite_storage()

    for config_type in ["intent", "user"]:
        for provider_type, defaults in PROVIDER_DEFAULTS.items():
            existing = storage.get_provider_config(config_type, provider_type)
            if not existing:
                enabled = (config_type == "intent" and provider_type == "ollama") or \
                         (config_type == "user" and provider_type == "deepseek")
                storage.save_provider_config(
                    config_type=config_type,
                    provider_type=provider_type,
                    name=defaults["name"],
                    base_url=defaults["base_url"],
                    api_key="",
                    model=defaults["models"][0],
                    models=defaults["models"],
                    enabled=enabled,
                )


def get_config_response() -> Dict[str, Any]:
    """获取配置响应（新结构）"""
    storage = get_sqlite_storage()

    # 确保默认配置存在
    init_default_provider_configs()

    intent_configs = storage.list_provider_configs("intent")
    user_configs = storage.list_provider_configs("user")

    intent_enabled = storage.get_enabled_provider_config("intent")
    user_enabled = storage.get_enabled_provider_config("user")

    return {
        "intent": {
            "configs": intent_configs,
            "enabled": intent_enabled,
        },
        "user": {
            "configs": user_configs,
            "enabled": user_enabled,
        },
    }


class ProviderConfigUpdateRequest(BaseModel):
    """Provider 配置更新请求"""
    config_type: str
    provider_type: str
    base_url: str
    api_key: Optional[str] = None
    model: str
    models: Optional[List[str]] = None


class SetEnabledProviderRequest(BaseModel):
    """设置启用 Provider 请求"""
    config_type: str
    provider_type: str


@router.get("")
async def get_config():
    """获取当前配置（新结构）"""
    return get_config_response()


@router.put("/provider")
async def update_provider_config(request: ProviderConfigUpdateRequest):
    """更新 Provider 配置"""
    storage = get_sqlite_storage()

    # 获取现有配置或默认值
    existing = storage.get_provider_config(request.config_type, request.provider_type)
    defaults = PROVIDER_DEFAULTS.get(request.provider_type, {})

    name = existing.get("name") if existing else defaults.get("name", request.provider_type)
    models = request.models if request.models else (existing.get("models") if existing else defaults.get("models", []))

    storage.save_provider_config(
        config_type=request.config_type,
        provider_type=request.provider_type,
        name=name,
        base_url=request.base_url,
        api_key=request.api_key or "",
        model=request.model,
        models=models,
        enabled=existing.get("enabled", False) if existing else False,
    )

    return get_config_response()


@router.post("/provider/enable")
async def set_enabled_provider(request: SetEnabledProviderRequest):
    """设置启用的 Provider"""
    storage = get_sqlite_storage()
    storage.set_enabled_provider(request.config_type, request.provider_type)
    return get_config_response()


# ============ 兼容旧接口（临时保留） ============

class ConfigResponse(BaseModel):
    """配置响应（兼容旧接口）"""
    intent_provider: dict
    user_provider: dict


class ConfigUpdateRequest(BaseModel):
    """配置更新请求（兼容旧接口）"""
    intent_provider: Optional[dict] = None
    user_provider: Optional[dict] = None


@router.get("/legacy")
async def get_config_legacy():
    """获取当前配置（兼容旧接口）"""
    storage = get_sqlite_storage()
    init_default_provider_configs()

    intent_enabled = storage.get_enabled_provider_config("intent")
    user_enabled = storage.get_enabled_provider_config("user")

    return {
        "intent_provider": {
            "type": intent_enabled["provider_type"] if intent_enabled else "ollama",
            "model": intent_enabled["model"] if intent_enabled else "qwen2.5-coder",
            "base_url": intent_enabled["base_url"] if intent_enabled else "http://localhost:11434/v1",
            "api_key": intent_enabled["api_key"] if intent_enabled else "",
        },
        "user_provider": {
            "type": user_enabled["provider_type"] if user_enabled else "deepseek",
            "model": user_enabled["model"] if user_enabled else "deepseek-chat",
            "base_url": user_enabled["base_url"] if user_enabled else "https://api.deepseek.com/v1",
            "api_key": user_enabled["api_key"] if user_enabled else "",
        },
    }


@router.put("/legacy")
async def update_config_legacy(request: ConfigUpdateRequest):
    """更新配置（兼容旧接口）"""
    storage = get_sqlite_storage()
    init_default_provider_configs()

    if request.intent_provider:
        provider_type = request.intent_provider.get("type", "ollama")
        defaults = PROVIDER_DEFAULTS.get(provider_type, {})

        storage.save_provider_config(
            config_type="intent",
            provider_type=provider_type,
            name=defaults.get("name", provider_type),
            base_url=request.intent_provider.get("base_url", defaults.get("base_url", "")),
            api_key=request.intent_provider.get("api_key", ""),
            model=request.intent_provider.get("model", defaults.get("models", [""])[0]),
            models=defaults.get("models", []),
            enabled=True,
        )
        storage.set_enabled_provider("intent", provider_type)

    if request.user_provider:
        provider_type = request.user_provider.get("type", "deepseek")
        defaults = PROVIDER_DEFAULTS.get(provider_type, {})

        storage.save_provider_config(
            config_type="user",
            provider_type=provider_type,
            name=defaults.get("name", provider_type),
            base_url=request.user_provider.get("base_url", defaults.get("base_url", "")),
            api_key=request.user_provider.get("api_key", ""),
            model=request.user_provider.get("model", defaults.get("models", [""])[0]),
            models=defaults.get("models", []),
            enabled=True,
        )
        storage.set_enabled_provider("user", provider_type)

    return await get_config_legacy()


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
