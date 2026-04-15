from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

from helix.storage import get_storage
from helix.core import (
    get_trigger,
    get_context_manager,
    get_state_engine,
)
from helix.models import (
    ChatRequest,
    ChatResponse,
    MessageRole,
)


router = APIRouter(prefix="/api/v1/sessions", tags=["chat"])

# 单独的 chat stream 路由
chat_router = APIRouter(prefix="/api/v1/chat", tags=["chat-stream"])


class StreamChatRequest(BaseModel):
    """流式聊天请求"""
    provider: str  # ollama, deepseek, minimax, volcengine
    model: str
    base_url: str
    api_key: Optional[str] = None
    messages: List[Dict[str, str]]
    stream: bool = True


@chat_router.post("/stream")
async def stream_chat(request: StreamChatRequest):
    """
    流式聊天接口 - 代理到 AI Provider 并标准化输出格式
    """
    async def generate():
        headers = {"Content-Type": "application/json"}
        if request.api_key:
            headers["Authorization"] = f"Bearer {request.api_key}"

        # 根据 provider 选择 endpoint
        if request.provider == "minimax" or request.provider == "volcengine":
            endpoint = f"{request.base_url}/agent/code"
        else:
            endpoint = f"{request.base_url}/chat/completions"

        payload = {
            "model": request.model,
            "messages": request.messages,
            "stream": True
        }

        logger.info(f"Streaming request to {request.provider} at {endpoint}, model={request.model}")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                    logger.info(f"Response status: {response.status_code}")

                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Error response: {error_text}")
                        error_data = json.dumps({"error": f"HTTP {response.status_code}", "content": f"请求失败: {error_text.decode('utf-8', errors='ignore')}"})
                        yield f"data: {error_data}\n\n".encode()
                        yield b"data: [DONE]\n\n"
                        return

                    buffer = b""
                    line_count = 0
                    content_received = False

                    async for chunk in response.aiter_bytes():
                        if chunk:
                            buffer += chunk
                            # 处理完整的 SSE 行
                            while b"\n" in buffer:
                                line, buffer = buffer.split(b"\n", 1)
                                line_str = line.decode("utf-8", errors="ignore").strip()
                                line_count += 1

                                if line_str.startswith("data: "):
                                    data_str = line_str[6:]
                                    if data_str == "[DONE]":
                                        logger.info(f"Received [DONE] after {line_count} lines")
                                        continue

                                    try:
                                        data = json.loads(data_str)
                                        # 标准化输出格式 - 支持多种 API 响应格式
                                        content = ""
                                        model = request.model

                                        # OpenAI 兼容格式
                                        if "choices" in data and len(data["choices"]) > 0:
                                            choice = data["choices"][0]
                                            if "delta" in choice and "content" in choice["delta"]:
                                                content = choice["delta"]["content"]
                                            elif "text" in choice:
                                                content = choice["text"]
                                            # 检查是否有 finish_reason
                                            if "finish_reason" in choice and choice["finish_reason"]:
                                                logger.info(f"Finish reason: {choice['finish_reason']}")

                                        # Claude Code 协议格式
                                        elif "content" in data:
                                            # content 可能是数组或字符串
                                            if isinstance(data["content"], list):
                                                # 数组格式，查找 text 类型
                                                for item in data["content"]:
                                                    if isinstance(item, dict) and item.get("type") == "text":
                                                        content = item.get("text", "")
                                                        break
                                                    elif isinstance(item, str):
                                                        content = item
                                                        break
                                            else:
                                                # 字符串格式
                                                content = data["content"]
                                        elif "message" in data and "content" in data["message"]:
                                            content = data["message"]["content"]

                                        if "model" in data:
                                            model = data["model"]

                                        if content:
                                            content_received = True
                                            output = {
                                                "content": content,
                                                "model": model
                                            }
                                            yield f"data: {json.dumps(output, ensure_ascii=False)}\n\n".encode()
                                    except json.JSONDecodeError as e:
                                        logger.debug(f"JSON decode error: {e}, line: {data_str}")
                                        continue
                                elif line_str:
                                    # 非 data: 开头的行，记录日志
                                    logger.debug(f"Non-data line: {line_str}")

                    logger.info(f"Stream ended. Lines processed: {line_count}, content received: {content_received}")

                    # 如果没有收到任何内容，发送提示
                    if not content_received:
                        logger.warning("No content received from stream")
                        error_data = json.dumps({"error": "no_content", "content": "警告: 未收到模型返回内容，请检查配置"})
                        yield f"data: {error_data}\n\n".encode()

                    # 发送结束标记
                    yield b"data: [DONE]\n\n"

        except httpx.TimeoutException as e:
            logger.error(f"Timeout error: {e}")
            error_data = json.dumps({"error": "timeout", "content": f"请求超时: {str(e)}"})
            yield f"data: {error_data}\n\n".encode()
        except Exception as e:
            logger.exception(f"Unexpected error in stream")
            error_data = json.dumps({"error": str(e), "content": f"错误: {str(e)}"})
            yield f"data: {error_data}\n\n".encode()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{session_id}/chat", response_model=dict)
async def chat(session_id: str, request: ChatRequest):
    """
    发送 Chat 请求（核心接口）

    1. 评估是否触发 Context Trigger 或 Workflow Trigger
    2. 构建 Prompt 上下文
    3. 更新状态
    4. 返回结果
    """
    storage = get_storage()

    # 检查 Session 是否存在
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # 1. 评估触发
    trigger = get_trigger()
    trigger_result = trigger.evaluate(request.user_input)

    # 2. 构建 Prompt 上下文
    context_manager = get_context_manager()
    prompt_context = context_manager.build_prompt_context(
        session=session,
        user_input=request.user_input,
        system_prompt=request.system_prompt,
    )

    # 3. 更新状态 - user input accepted
    state_engine = get_state_engine()
    state_engine.on_user_input_accepted(session_id)

    # 4. 保存用户消息
    storage.add_message(session_id, MessageRole.USER, request.user_input)

    # 重新获取 session（状态可能已更新）
    session = storage.get_session(session_id)

    # 5. 返回结果
    return {
        "trigger_result": trigger_result.model_dump(),
        "prompt_context": {
            "context_blocks": prompt_context.context_blocks,
            "final_prompt_segments": prompt_context.final_prompt_segments,
        },
        "session_state": session.state.model_dump() if session else None,
        "raw_user_input": request.user_input,
        "suggested_response": None,  # 后续可由 LLM 生成
    }
