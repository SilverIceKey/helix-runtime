from typing import Optional, Callable
from helix.models import SessionState, TaskStatus, FeedbackType
from helix.storage import get_storage


class StateEngine:
    """
    State Engine - 状态引擎

    负责维护系统运行状态，而非历史文本。

    状态更新时机：
    - user input accepted
    - workflow step completed
    - model response returned
    - revision detected
    """

    def __init__(self):
        self._storage = get_storage()

    def get_state(self, session_id: str) -> Optional[SessionState]:
        """
        获取 Session 的状态

        Args:
            session_id: Session ID

        Returns:
            SessionState 对象，如果 Session 不存在则返回 None
        """
        session = self._storage.get_session(session_id)
        if session is None:
            return None
        return session.state

    def update_state(
        self,
        session_id: str,
        patch: dict,
    ) -> Optional[SessionState]:
        """
        部分更新 Session 状态

        Args:
            session_id: Session ID
            patch: 要更新的字段字典

        Returns:
            更新后的 SessionState，如果 Session 不存在则返回 None
        """
        session = self._storage.get_session(session_id)
        if session is None:
            return None

        state = session.state

        # 更新各字段（仅更新非 None 的字段）
        if "current_topic" in patch and patch["current_topic"] is not None:
            state.current_topic = patch["current_topic"]
        if "current_task" in patch and patch["current_task"] is not None:
            state.current_task = patch["current_task"]
        if "task_status" in patch and patch["task_status"] is not None:
            state.task_status = TaskStatus(patch["task_status"])
        if "workflow_step" in patch and patch["workflow_step"] is not None:
            state.workflow_step = patch["workflow_step"]
        if "last_feedback_type" in patch and patch["last_feedback_type"] is not None:
            state.last_feedback_type = FeedbackType(patch["last_feedback_type"])

        self._storage.update_session(session)
        return state

    def on_user_input_accepted(self, session_id: str) -> Optional[SessionState]:
        """
        用户输入被接受时调用

        触发时机：用户输入被系统接收并处理
        """
        session = self._storage.get_session(session_id)
        if session is None:
            return None

        session.state.on_user_input_accepted()
        self._storage.update_session(session)
        return session.state

    def on_workflow_step_completed(self, session_id: str) -> Optional[SessionState]:
        """
        工作流步骤完成时调用

        触发时机：Post Workflow Runtime 完成一个步骤
        """
        session = self._storage.get_session(session_id)
        if session is None:
            return None

        session.state.on_workflow_step_completed()
        self._storage.update_session(session)
        return session.state

    def on_model_response_returned(self, session_id: str) -> Optional[SessionState]:
        """
        模型响应返回时调用

        触发时机：主 LLM 返回响应
        """
        session = self._storage.get_session(session_id)
        if session is None:
            return None

        session.state.on_model_response_returned()
        self._storage.update_session(session)
        return session.state

    def on_revision_detected(self, session_id: str) -> Optional[SessionState]:
        """
        检测到修订时调用

        触发时机：用户表示结果不正确、需要修改
        """
        session = self._storage.get_session(session_id)
        if session is None:
            return None

        session.state.on_revision_detected()
        self._storage.update_session(session)
        return session.state

    def reset_state(self, session_id: str) -> Optional[SessionState]:
        """
        重置 Session 状态

        Args:
            session_id: Session ID

        Returns:
            重置后的 SessionState，如果 Session 不存在则返回 None
        """
        session = self._storage.get_session(session_id)
        if session is None:
            return None

        # 创建新的默认状态
        session.state = SessionState(session_id=session_id)
        self._storage.update_session(session)
        return session.state


# 全局单例
_state_engine: Optional[StateEngine] = None


def get_state_engine() -> StateEngine:
    """
    获取全局 StateEngine 实例
    """
    global _state_engine
    if _state_engine is None:
        _state_engine = StateEngine()
    return _state_engine
