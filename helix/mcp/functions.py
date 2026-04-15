"""
Helix Runtime - MCP Functions 定义

定义暴露给 Claude Code 的 Functions（工具）
"""

from typing import List, Dict, Any


# Helix Runtime 暴露给 Claude Code 的 Functions
FUNCTIONS = [
    {
        "name": "create_session",
        "description": "创建新的 Helix Session",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "可选的 session ID，如果不提供则自动生成"
                }
            }
        }
    },
    {
        "name": "get_session_state",
        "description": "获取 Session 的当前状态，包括任务状态、工作流步骤等",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "switch_provider",
        "description": "切换当前 Session 使用的 AI Provider",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "provider_type": {
                    "type": "string",
                    "description": "Provider 类型（ollama, deepseek, minimax, volcengine）"
                },
                "model": {
                    "type": "string",
                    "description": "模型名称（可选）"
                }
            },
            "required": ["session_id", "provider_type"]
        }
    },
    {
        "name": "list_providers",
        "description": "列出当前可用的 AI Providers",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_session_history",
        "description": "获取 Session 的消息历史",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回的消息数量限制",
                    "default": 10
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "health_check",
        "description": "检查 Helix Runtime 和各 Provider 的健康状态",
        "parameters": {
            "type": "object",
            "properties": {
                "provider_name": {
                    "type": "string",
                    "description": "Provider 名称（intent_detection, user_ai），如果不提供则检查所有"
                }
            }
        }
    }
]


def get_functions() -> List[Dict[str, Any]]:
    """获取所有 Functions 定义"""
    return FUNCTIONS


def get_function_by_name(name: str) -> Dict[str, Any] | None:
    """根据名称获取 Function 定义"""
    for func in FUNCTIONS:
        if func["name"] == name:
            return func
    return None
