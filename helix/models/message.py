from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """
    Message - 消息模型

    存储单条消息记录。
    """
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def is_user(self) -> bool:
        """是否为用户消息"""
        return self.role == MessageRole.USER

    def is_assistant(self) -> bool:
        """是否为助手消息"""
        return self.role == MessageRole.ASSISTANT

    def is_system(self) -> bool:
        """是否为系统消息"""
        return self.role == MessageRole.SYSTEM
