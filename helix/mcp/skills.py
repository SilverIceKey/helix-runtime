"""
Helix Runtime - MCP Skills 定义

定义暴露给 Claude Code 的 Skills
"""

from typing import List, Dict, Any


# Helix Runtime 暴露给 Claude Code 的 Skills
SKILLS = [
    {
        "name": "helix-chat",
        "description": "使用 Helix Runtime 进行对话，自动意图检测和路由。根据用户输入自动判断是否需要触发工作流。",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID，如果为空则自动创建"
                },
                "message": {
                    "type": "string",
                    "description": "用户消息"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "helix-code",
        "description": "强制使用 Code Plan AI（Minimax/火山引擎）进行代码生成任务。此 Skill 强制路由到用户配置的代码专用 Provider。",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "code_request": {
                    "type": "string",
                    "description": "代码请求描述"
                },
                "language": {
                    "type": "string",
                    "description": "编程语言（python, javascript, go, rust 等）",
                    "default": "python"
                }
            },
            "required": ["session_id", "code_request"]
        }
    },
    {
        "name": "helix-continue",
        "description": "继续之前的对话上下文。当用户说 'continue', 'resume', '基于以上' 等时使用此 Skill。",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "message": {
                    "type": "string",
                    "description": "继续对话的消息"
                }
            },
            "required": ["session_id", "message"]
        }
    },
    {
        "name": "helix-document",
        "description": "生成文档工作流。用于长文档、报告、规范等文档生成任务。",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "document_type": {
                    "type": "string",
                    "description": "文档类型（report, spec, proposal, guide 等）",
                    "default": "report"
                },
                "topic": {
                    "type": "string",
                    "description": "文档主题"
                }
            },
            "required": ["session_id", "topic"]
        }
    },
    {
        "name": "helix-revision",
        "description": "修订工作流。当用户说 'not correct', '修改', '重新' 等时使用此 Skill。",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "issue": {
                    "type": "string",
                    "description": "需要修订的问题描述"
                },
                "original_content": {
                    "type": "string",
                    "description": "原始内容（可选）"
                }
            },
            "required": ["session_id", "issue"]
        }
    }
]


def get_skills() -> List[Dict[str, Any]]:
    """获取所有 Skills 定义"""
    return SKILLS


def get_skill_by_name(name: str) -> Dict[str, Any] | None:
    """根据名称获取 Skill 定义"""
    for skill in SKILLS:
        if skill["name"] == name:
            return skill
    return None
