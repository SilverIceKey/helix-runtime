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


class SessionStreamChatRequest(BaseModel):
    """基于 Session 的流式聊天请求 - 使用完整基础设施"""
    session_id: str
    provider: str  # ollama, deepseek, minimax, volcengine
    model: str
    base_url: str
    api_key: Optional[str] = None
    user_input: str
    system_prompt: Optional[str] = None


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
        if request.provider == "minimax":
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

                                        # 其他可能的格式
                                        elif "content" in data:
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


@chat_router.post("/session-stream")
async def session_stream_chat(request: SessionStreamChatRequest):
    """
    基于 Session 的流式聊天接口 - 使用完整基础设施

    1. 使用 Session 存储消息
    2. 使用 ContextManager 智能选择历史上下文（不是全部消息）
    3. 使用 CapabilityTrigger 评估意图
    4. 使用 StateEngine 更新状态
    5. 流式调用 AI Provider
    """
    storage = get_storage()

    # 检查 Session 是否存在，不存在则创建
    session = storage.get_session(request.session_id)
    if session is None:
        session = storage.create_session(request.session_id)

    # 1. 评估触发
    trigger = get_trigger()
    trigger_result = trigger.evaluate(request.user_input)

    # 2. 构建 Prompt 上下文（使用 ContextManager 智能选择历史）
    context_manager = get_context_manager()
    prompt_context = context_manager.build_prompt_context(
        session=session,
        user_input=request.user_input,
        system_prompt=request.system_prompt,
    )

    # 3. 更新状态 - user input accepted
    state_engine = get_state_engine()
    state_engine.on_user_input_accepted(request.session_id)

    # 4. 保存用户消息
    storage.add_message(request.session_id, MessageRole.USER, request.user_input)

    # 构建发送给 AI 的消息（使用 ContextManager 处理后的上下文）
    # final_prompt_segments 包含了智能选择的历史和当前输入
    # 我们需要把它转换成 OpenAI 格式的 messages
    ai_messages = []

    # 添加历史消息（从 ContextManager 的 final_prompt_segments）
    # 解析 final_prompt_segments 来构建消息
    for segment in prompt_context.final_prompt_segments:
        # 简单解析：假设格式是 "ROLE: content"
        if segment.startswith("USER: "):
            ai_messages.append({"role": "user", "content": segment[6:]})
        elif segment.startswith("ASSISTANT: "):
            ai_messages.append({"role": "assistant", "content": segment[11:]})
        elif segment and not segment.startswith("(No history)"):
            # 如果是纯文本，作为 user 消息（兼容旧格式）
            ai_messages.append({"role": "user", "content": segment})

    # 如果没有从 segments 解析出消息，使用原始的方式
    if not ai_messages:
        # 获取最近的消息作为历史
        recent_messages = context_manager._get_recent_messages(
            session.messages,
            context_manager._max_recent_turns
        )
        for msg in recent_messages:
            ai_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        # 添加当前用户输入
        ai_messages.append({"role": "user", "content": request.user_input})

    # 5. 流式调用 AI Provider
    async def generate():
        headers = {"Content-Type": "application/json"}
        if request.api_key:
            headers["Authorization"] = f"Bearer {request.api_key}"

        # 根据 provider 选择 endpoint
        if request.provider == "minimax":
            endpoint = f"{request.base_url}/agent/code"
        else:
            endpoint = f"{request.base_url}/chat/completions"

        payload = {
            "model": request.model,
            "messages": ai_messages,
            "stream": True
        }

        logger.info(f"Session stream request to {request.provider} at {endpoint}, model={request.model}, session={request.session_id}")
        logger.info(f"Using {len(ai_messages)} messages from context manager")

        # 首先发送 trigger_result 和 prompt_context 给前端
        initial_data = {
            "trigger_result": trigger_result.model_dump(),
            "context_blocks": prompt_context.context_blocks,
            "session_id": request.session_id,
            "content": ""
        }
        yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n".encode()

        full_content = ""
        model_used = request.model

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
                            while b"\n" in buffer:
                                line, buffer = buffer.split(b"\n", 1)
                                line_str = line.decode("utf-8", errors="ignore").strip()
                                line_count += 1

                                if line_str.startswith("data: "):
                                    data_str = line_str[6:]
                                    if data_str == "[DONE]":
                                        continue

                                    try:
                                        data = json.loads(data_str)
                                        content = ""

                                        if "choices" in data and len(data["choices"]) > 0:
                                            choice = data["choices"][0]
                                            if "delta" in choice and "content" in choice["delta"]:
                                                content = choice["delta"]["content"]
                                            elif "text" in choice:
                                                content = choice["text"]

                                        elif "content" in data:
                                            content = data["content"]
                                        elif "message" in data and "content" in data["message"]:
                                            content = data["message"]["content"]

                                        if "model" in data:
                                            model_used = data["model"]

                                        if content:
                                            content_received = True
                                            full_content += content
                                            output = {
                                                "content": content,
                                                "model": model_used
                                            }
                                            yield f"data: {json.dumps(output, ensure_ascii=False)}\n\n".encode()
                                    except json.JSONDecodeError:
                                        continue

                    logger.info(f"Stream ended. Lines processed: {line_count}, content received: {content_received}")

                    # 保存 assistant 消息
                    if full_content:
                        storage.add_message(request.session_id, MessageRole.ASSISTANT, full_content)

                    # 发送结束标记
                    yield b"data: [DONE]\n\n"

        except httpx.TimeoutException as e:
            logger.error(f"Timeout error: {e}")
            error_data = json.dumps({"error": "timeout", "content": f"请求超时: {str(e)}"})
            yield f"data: {error_data}\n\n".encode()
        except Exception as e:
            logger.exception(f"Unexpected error in session stream")
            error_data = json.dumps({"error": str(e), "content": f"错误: {str(e)}"})
            yield f"data: {error_data}\n\n".encode()

    return StreamingResponse(generate(), media_type="text/event-stream")
