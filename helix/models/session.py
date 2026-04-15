from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any
from helix.models.message import Message
from helix.models.state import SessionState


class Session(BaseModel):
    """
    Session - 会话模型

    包含完整的会话信息：消息历史、状态、工作流日志。
    """
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    state: SessionState
    workflow_log: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(self, message: Message) -> None:
        """
        添加消息并更新 updated_at
        """
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def add_workflow_log(self, log_entry: Dict[str, Any]) -> None:
        """
        添加工作流日志并更新 updated_at
        """
        self.workflow_log.append(log_entry)
        self.updated_at = datetime.utcnow()

    def get_recent_messages(self, limit: int = 5) -> List[Message]:
        """
        获取最近 N 条消息
        """
        return self.messages[-limit:] if limit > 0 else self.messages

    def get_history_count(self) -> int:
        """获取历史消息总数"""
        return len(self.messages)

    def clear_messages(self) -> None:
        """清空消息历史"""
        self.messages.clear()
        self.updated_at = datetime.utcnow()
