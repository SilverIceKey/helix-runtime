from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class WorkflowType(str, Enum):
    """工作流类型枚举"""
    DOCUMENT = "document"
    REVISION = "revision"


class UserRequest(BaseModel):
    """
    UserRequest - 用户请求模型
    """
    session_id: str
    user_input: str


class TriggerResult(BaseModel):
    """
    TriggerResult - 触发结果模型

    返回能力触发的判断结果。
    """
    trigger_context: bool = False
    trigger_workflow: bool = False
    mode: str = "direct"  # "direct" | "continue" | "workflow"


class PromptContext(BaseModel):
    """
    PromptContext - Prompt 上下文模型

    返回上下文管理器构建的 Prompt 内容。
    """
    context_blocks: List[str] = Field(default_factory=list)
    final_prompt_segments: List[str] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    """
    WorkflowResult - 工作流执行结果模型
    """
    success: bool = False
    output: Optional[str] = None
    step: int = 0
    error: Optional[str] = None


class ChatRequest(BaseModel):
    """
    ChatRequest - 聊天请求模型
    """
    user_input: str
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    """
    ChatResponse - 聊天响应模型
    """
    trigger_result: TriggerResult
    prompt_context: PromptContext
    session_state: Dict[str, Any]
    raw_user_input: str
    suggested_response: Optional[str] = None


class WorkflowRequest(BaseModel):
    """
    WorkflowRequest - 工作流请求模型
    """
    workflow_type: WorkflowType
    context: Optional[Dict[str, Any]] = None
