from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

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
