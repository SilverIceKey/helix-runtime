from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from helix.storage import get_storage
from helix.core import get_workflow_runtime, get_state_engine
from helix.models import WorkflowType, WorkflowRequest, WorkflowResult


router = APIRouter(prefix="/api/v1/sessions", tags=["workflows"])


@router.post("/{session_id}/workflows", response_model=dict)
async def execute_workflow(session_id: str, request: WorkflowRequest):
    """
    触发 Workflow
    """
    storage = get_storage()

    # 检查 Session 是否存在
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # 执行工作流
    workflow_runtime = get_workflow_runtime()

    # 构建上下文
    context = request.context or {}
    context["session_id"] = session_id
    context["session_state"] = session.state.model_dump()

    # 执行工作流
    result = workflow_runtime.execute(
        workflow_type=request.workflow_type,
        context=context,
    )

    # 更新状态 - workflow step completed
    if result.success:
        state_engine = get_state_engine()
        state_engine.on_workflow_step_completed(session_id)

    # 记录工作流日志
    storage.get_session(session_id).add_workflow_log({
        "workflow_type": request.workflow_type.value,
        "step": result.step,
        "success": result.success,
        "output": result.output,
        "error": result.error,
    })

    return {
        "success": result.success,
        "output": result.output,
        "step": result.step,
        "error": result.error,
    }


@router.get("/{session_id}/workflows/steps")
async def get_workflow_steps():
    """
    获取支持的工作流步骤

    注意：这个端点不需要 session_id，主要用于客户端了解支持的工作流
    """
    workflow_runtime = get_workflow_runtime()

    return {
        "document_workflow": {
            "type": WorkflowType.DOCUMENT.value,
            "steps": [s.value for s in workflow_runtime.get_workflow_steps(WorkflowType.DOCUMENT)],
        },
        "revision_workflow": {
            "type": WorkflowType.REVISION.value,
            "steps": [s.value for s in workflow_runtime.get_workflow_steps(WorkflowType.REVISION)],
        },
    }
