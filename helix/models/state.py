from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class FeedbackType(str, Enum):
    """反馈类型枚举"""
    NONE = "none"
    CONFIRM = "confirm"
    REVISION = "revision"


class SessionState(BaseModel):
    """
    SessionState - 状态引擎维护的会话状态

    负责维护系统运行状态，而非历史文本。
    """
    session_id: str
    current_topic: Optional[str] = None
    current_task: Optional[str] = None
    task_status: TaskStatus = TaskStatus.IDLE
    workflow_step: int = 0
    last_feedback_type: FeedbackType = FeedbackType.NONE

    def update(
        self,
        current_topic: Optional[str] = None,
        current_task: Optional[str] = None,
        task_status: Optional[TaskStatus] = None,
        workflow_step: Optional[int] = None,
        last_feedback_type: Optional[FeedbackType] = None,
    ) -> None:
        """
        更新状态字段（仅更新非 None 的字段）
        """
        if current_topic is not None:
            self.current_topic = current_topic
        if current_task is not None:
            self.current_task = current_task
        if task_status is not None:
            self.task_status = task_status
        if workflow_step is not None:
            self.workflow_step = workflow_step
        if last_feedback_type is not None:
            self.last_feedback_type = last_feedback_type

    def on_user_input_accepted(self) -> None:
        """用户输入被接受时调用"""
        self.task_status = TaskStatus.IN_PROGRESS

    def on_workflow_step_completed(self) -> None:
        """工作流步骤完成时调用"""
        self.workflow_step += 1

    def on_model_response_returned(self) -> None:
        """模型响应返回时调用"""
        self.task_status = TaskStatus.COMPLETED

    def on_revision_detected(self) -> None:
        """检测到修订时调用"""
        self.last_feedback_type = FeedbackType.REVISION
        self.task_status = TaskStatus.IN_PROGRESS
