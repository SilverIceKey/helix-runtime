from typing import Dict, Optional, List
import threading
import uuid
from datetime import datetime

from helix.models import Session, Message, SessionState, MessageRole


class MemoryStorage:
    """
    内存存储 -  Session 增删改查

    初期使用内存存储，无需依赖 Redis/PostgreSQL。
    线程安全，支持并发访问。
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def create_session(self, session_id: Optional[str] = None) -> Session:
        """
        创建新 Session

        Args:
            session_id: 可选的 session_id，如果为空则自动生成

        Returns:
            创建的 Session 对象
        """
        with self._lock:
            if session_id is None:
                session_id = str(uuid.uuid4())

            if session_id in self._sessions:
                raise ValueError(f"Session {session_id} already exists")

            state = SessionState(session_id=session_id)
            session = Session(
                session_id=session_id,
                state=state,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取 Session

        Args:
            session_id: Session ID

        Returns:
            Session 对象，如果不存在则返回 None
        """
        with self._lock:
            return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        删除 Session

        Args:
            session_id: Session ID

        Returns:
            是否成功删除
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def update_session(self, session: Session) -> None:
        """
        更新 Session（自动更新 updated_at）

        Args:
            session: Session 对象
        """
        with self._lock:
            session.updated_at = datetime.utcnow()
            self._sessions[session.session_id] = session

    def list_sessions(self) -> List[str]:
        """
        列出所有 Session ID

        Returns:
            Session ID 列表
        """
        with self._lock:
            return list(self._sessions.keys())

    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
    ) -> Optional[Message]:
        """
        向 Session 添加消息

        Args:
            session_id: Session ID
            role: 消息角色
            content: 消息内容

        Returns:
            创建的 Message 对象，如果 Session 不存在则返回 None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            message = Message(role=role, content=content)
            session.add_message(message)
            session.updated_at = datetime.utcnow()
            return message

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> Optional[List[Message]]:
        """
        获取 Session 的消息历史

        Args:
            session_id: Session ID
            limit: 限制返回的消息数量，None 表示返回全部

        Returns:
            Message 列表，如果 Session 不存在则返回 None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if limit is None:
                return list(session.messages)
            return session.get_recent_messages(limit)

    def get_history_count(self, session_id: str) -> Optional[int]:
        """
        获取 Session 的消息数量

        Args:
            session_id: Session ID

        Returns:
            消息数量，如果 Session 不存在则返回 None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session.get_history_count()

    def clear_messages(self, session_id: str) -> bool:
        """
        清空 Session 的消息历史

        Args:
            session_id: Session ID

        Returns:
            是否成功清空
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.clear_messages()
            return True


# 全局单例
_storage: Optional[MemoryStorage] = None


def get_storage() -> MemoryStorage:
    """
    获取全局存储实例（单例模式）
    """
    global _storage
    if _storage is None:
        _storage = MemoryStorage()
    return _storage


def reset_storage() -> None:
    """
    重置存储（主要用于测试）
    """
    global _storage
    _storage = None
