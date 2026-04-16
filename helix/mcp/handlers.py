"""
Helix Runtime - MCP Handlers

MCP 消息处理器
"""

import json
from typing import Dict, Any, Optional, Callable
from helix.storage import get_storage
from helix.providers import (
    get_intent_provider,
    get_user_provider,
    set_intent_provider,
    set_user_provider,
    ProviderRegistry,
    ProviderConfig,
    ProviderType,
    Message,
    IntentType,
)
from helix.core import get_context_manager, get_state_engine


class MCPHandlers:
    """
    MCP 消息处理器

    处理 MCP 协议的各种请求
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._register_handlers()

    def _register_handlers(self):
        """注册所有处理方法"""
        self._handlers["initialize"] = self._handle_initialize
        self._handlers["tools/list"] = self._handle_tools_list
        self._handlers["tools/call"] = self._handle_tools_call
        self._handlers["resources/list"] = self._handle_resources_list
        self._handlers["resources/read"] = self._handle_resources_read
        self._handlers["prompts/list"] = self._handle_prompts_list
        self._handlers["prompts/get"] = self._handle_prompts_get

    async def handle(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理 MCP 请求

        Args:
            method: MCP 方法名
            params: 参数

        Returns:
            MCP 响应
        """
        handler = self._handlers.get(method)
        if handler is None:
            return {
                "error": {
                    "code": "METHOD_NOT_FOUND",
                    "message": f"Unknown method: {method}",
                    "retryable": False
                }
            }

        try:
            result = await handler(params or {})
            return {"result": result}
        except Exception as e:
            return {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "retryable": True
                }
            }

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 initialize 请求"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
            },
            "serverInfo": {
                "name": "helix-runtime",
                "version": "0.2.0",
            }
        }

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 tools/list 请求"""
        from helix.mcp.skills import get_skills
        from helix.mcp.functions import get_functions

        tools = []
        for skill in get_skills():
            tools.append({
                "name": skill["name"],
                "description": skill["description"],
                "inputSchema": skill["parameters"],
            })
        for func in get_functions():
            tools.append({
                "name": func["name"],
                "description": func["description"],
                "inputSchema": func["parameters"],
            })

        return {"tools": tools}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 tools/call 请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        # Skill handlers
        if tool_name == "helix-chat":
            return await self._tool_helix_chat(arguments)
        elif tool_name == "helix-code":
            return await self._tool_helix_code(arguments)
        elif tool_name == "helix-continue":
            return await self._tool_helix_continue(arguments)
        elif tool_name == "helix-document":
            return await self._tool_helix_document(arguments)
        elif tool_name == "helix-revision":
            return await self._tool_helix_revision(arguments)

        # Function handlers
        elif tool_name == "create_session":
            return await self._tool_create_session(arguments)
        elif tool_name == "get_session_state":
            return await self._tool_get_session_state(arguments)
        elif tool_name == "switch_provider":
            return await self._tool_switch_provider(arguments)
        elif tool_name == "list_providers":
            return await self._tool_list_providers(arguments)
        elif tool_name == "get_session_history":
            return await self._tool_get_session_history(arguments)
        elif tool_name == "health_check":
            return await self._tool_health_check(arguments)

        return {"error": f"Unknown tool: {tool_name}"}

    async def _tool_helix_chat(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """helix-chat tool"""
        session_id = args.get("session_id") or f"mcp-{id(args)}"
        message = args.get("message", "")

        storage = get_storage()

        # 获取或创建 session
        session = storage.get_session(session_id)
        if session is None:
            session = storage.create_session(session_id)

        # Intent Detection
        intent_provider = get_intent_provider()
        if intent_provider:
            intent_result = await intent_provider.detect_intent(message, {"session_id": session_id})
        else:
            intent_result = None

        # User AI Response
        user_provider = get_user_provider()
        response_text = ""
        if user_provider:
            messages = [
                Message(role="user", content=message)
            ]
            completion = await user_provider.chat(messages)
            response_text = completion.content

            # 保存消息
            storage.add_message(session_id, "user", message)
            storage.add_message(session_id, "assistant", response_text)
        else:
            response_text = "[No user AI provider configured] Use /providers to configure."

        return {
            "session_id": session_id,
            "response": response_text,
            "intent": intent_result.intent.value if intent_result else "unknown",
            "confidence": intent_result.confidence if intent_result else 0.0,
        }

    async def _tool_helix_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """helix-code tool - 强制使用 Code Plan AI"""
        session_id = args.get("session_id", "")
        code_request = args.get("code_request", "")
        language = args.get("language", "python")

        # 强制使用用户 AI Provider
        user_provider = get_user_provider()
        if not user_provider:
            return {"error": "No user AI provider configured"}

        full_request = f"Write {language} code: {code_request}"
        messages = [Message(role="user", content=full_request)]
        completion = await user_provider.chat(messages)

        return {
            "session_id": session_id,
            "response": completion.content,
            "language": language,
            "forced_provider": user_provider.provider_type.value,
        }

    async def _tool_helix_continue(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """helix-continue tool"""
        session_id = args.get("session_id", "")
        message = args.get("message", "")

        storage = get_storage()
        session = storage.get_session(session_id)
        if session is None:
            return {"error": f"Session {session_id} not found"}

        user_provider = get_user_provider()
        if user_provider:
            # 获取历史消息
            history = storage.get_messages(session_id, limit=10)
            messages = [Message(role="user", content=msg.content) if msg.role.value == "user" else Message(role="assistant", content=msg.content) for msg in history]
            messages.append(Message(role="user", content=message))

            completion = await user_provider.chat(messages)
            response_text = completion.content

            storage.add_message(session_id, "user", message)
            storage.add_message(session_id, "assistant", response_text)
        else:
            response_text = "[No user AI provider configured]"

        return {
            "session_id": session_id,
            "response": response_text,
            "intent": "continue",
        }

    async def _tool_helix_document(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """helix-document tool"""
        session_id = args.get("session_id", "")
        document_type = args.get("document_type", "report")
        topic = args.get("topic", "")

        user_provider = get_user_provider()
        if user_provider:
            full_request = f"Generate a {document_type} about: {topic}"
            messages = [Message(role="user", content=full_request)]
            completion = await user_provider.chat(messages)
            response_text = completion.content
        else:
            response_text = "[No user AI provider configured]"

        return {
            "session_id": session_id,
            "document_type": document_type,
            "topic": topic,
            "response": response_text,
            "intent": "workflow_document",
        }

    async def _tool_helix_revision(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """helix-revision tool"""
        session_id = args.get("session_id", "")
        issue = args.get("issue", "")

        user_provider = get_user_provider()
        if user_provider:
            revision_request = f"Please revise the previous response. Issue: {issue}"
            messages = [Message(role="user", content=revision_request)]
            completion = await user_provider.chat(messages)
            response_text = completion.content
        else:
            response_text = "[No user AI provider configured]"

        return {
            "session_id": session_id,
            "issue": issue,
            "response": response_text,
            "intent": "workflow_revision",
        }

    async def _tool_create_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """create_session function"""
        session_id = args.get("session_id")
        storage = get_storage()
        session = storage.create_session(session_id)
        return {"session_id": session.session_id, "created_at": session.created_at.isoformat()}

    async def _tool_get_session_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """get_session_state function"""
        session_id = args.get("session_id", "")
        storage = get_storage()
        session = storage.get_session(session_id)
        if session is None:
            return {"error": f"Session {session_id} not found"}
        return {
            "session_id": session.session_id,
            "state": session.state.model_dump(),
            "message_count": len(session.messages),
        }

    async def _tool_switch_provider(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """switch_provider function"""
        session_id = args.get("session_id", "")
        provider_type = args.get("provider_type", "")
        model = args.get("model")

        # 这需要根据实际配置重新创建 Provider
        return {
            "session_id": session_id,
            "provider_type": provider_type,
            "model": model,
            "status": "not_implemented_yet",
        }

    async def _tool_list_providers(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """list_providers function"""
        providers = ProviderRegistry.list_providers()
        return {
            "registered_providers": providers,
            "intent_provider": get_intent_provider().provider_type.value if get_intent_provider() else None,
            "user_provider": get_user_provider().provider_type.value if get_user_provider() else None,
        }

    async def _tool_get_session_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """get_session_history function"""
        session_id = args.get("session_id", "")
        limit = args.get("limit", 10)
        storage = get_storage()
        messages = storage.get_messages(session_id, limit=limit)
        if messages is None:
            return {"error": f"Session {session_id} not found"}
        return {
            "session_id": session_id,
            "count": len(messages),
            "messages": [
                {"role": m.role.value, "content": m.content, "timestamp": m.timestamp.isoformat()}
                for m in messages
            ],
        }

    async def _tool_health_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """health_check function"""
        provider_name = args.get("provider_name")

        result = {}
        if provider_name in (None, "intent_detection"):
            provider = get_intent_provider()
            result["intent_detection"] = await provider.health_check() if provider else False
        if provider_name in (None, "user_ai"):
            provider = get_user_provider()
            result["user_ai"] = await provider.health_check() if provider else False

        return result

    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 resources/list 请求"""
        return {"resources": []}

    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 resources/read 请求"""
        return {"contents": []}

    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 prompts/list 请求"""
        return {
            "prompts": [
                {
                    "name": "summarize_session",
                    "description": "Summarize the current session history",
                    "arguments": [
                        {
                            "name": "session_id",
                            "description": "Session ID to summarize",
                            "required": True
                        },
                        {
                            "name": "output_style",
                            "description": "Output style (brief, detailed, action_items)",
                            "required": False
                        }
                    ]
                },
                {
                    "name": "generate_code_plan",
                    "description": "Generate a code implementation plan",
                    "arguments": [
                        {
                            "name": "requirement",
                            "description": "Requirement description",
                            "required": True
                        },
                        {
                            "name": "language",
                            "description": "Programming language",
                            "required": False
                        }
                    ]
                }
            ]
        }

    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 prompts/get 请求"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name == "summarize_session":
            session_id = arguments.get("session_id")
            output_style = arguments.get("output_style", "brief")
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Please summarize session {session_id} in {output_style} style"
                    }
                ]
            }
        elif name == "generate_code_plan":
            requirement = arguments.get("requirement")
            language = arguments.get("language", "python")
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Generate a code implementation plan for: {requirement} in {language}"
                    }
                ]
            }
        else:
            return {
                "error": {
                    "code": "PROMPT_NOT_FOUND",
                    "message": f"Prompt not found: {name}",
                    "retryable": False
                }
            }
