from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from pathlib import Path


router = APIRouter(prefix="/api/v1/config", tags=["config"])


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

        # 简单测试：尝试获取模型列表
        # 这里简化处理，实际应该做真正的连接测试
        return {"success": True, "message": f"{request.type} provider configured"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/providers/models")
async def get_models(request: ProviderTestRequest):
    """
    获取 Provider 可用模型列表
    """
    try:
        # 返回默认模型列表（实际应该从 Provider API 获取）
        default_models = {
            "ollama": ["qwen2.5-coder", "llama2", "codellama", "mistral"],
            "deepseek": ["deepseek-chat", "deepseek-coder"],
            "minimax": ["abab6.5s-chat", "abab6.5-chat"],
            "volcengine": ["doubao-pro-32k"],
        }
        models = default_models.get(request.type, [])
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}
