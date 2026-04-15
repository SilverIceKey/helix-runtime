"""
Helix Runtime - SQLite 持久化存储

支持配置和会话的持久化存储
"""
import sqlite3
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

from helix.models import Session, Message, SessionState, MessageRole


def get_db_path() -> Path:
    """获取 SQLite 数据库文件路径"""
    config_dir = Path.home() / ".config" / "helix"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "helix.db"


class SQLiteStorage:
    """
    SQLite 持久化存储

    支持配置和 Session 的持久化存储
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = get_db_path()
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # 配置表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Session 表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        state TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')

                # 消息表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                    )
                ''')

                conn.commit()
            finally:
                conn.close()

    # ============ 配置存储 ============

    def save_config(self, key: str, value: Dict[str, Any]) -> None:
        """保存配置"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, json.dumps(value, ensure_ascii=False)))
                conn.commit()
            finally:
                conn.close()

    def load_config(self, key: str) -> Optional[Dict[str, Any]]:
        """加载配置"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row['value'])
                return None
            finally:
                conn.close()

    def delete_config(self, key: str) -> bool:
        """删除配置"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM config WHERE key = ?', (key,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    # ============ Session 存储 ============

    def create_session(self, session_id: Optional[str] = None) -> Session:
        """创建新 Session"""
        with self._lock:
            if session_id is None:
                session_id = str(uuid.uuid4())

            conn = self._get_connection()
            try:
                # 检查是否已存在
                cursor = conn.cursor()
                cursor.execute('SELECT session_id FROM sessions WHERE session_id = ?', (session_id,))
                if cursor.fetchone():
                    raise ValueError(f"Session {session_id} already exists")

                # 创建 Session
                state = SessionState(session_id=session_id)
                now = datetime.utcnow()

                cursor.execute('''
                    INSERT INTO sessions (session_id, state, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, state.model_dump_json(), now.isoformat(), now.isoformat()))

                conn.commit()

                session = Session(
                    session_id=session_id,
                    state=state,
                    created_at=now,
                    updated_at=now,
                )
                return session
            finally:
                conn.close()

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取 Session"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # 获取 Session
                cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
                row = cursor.fetchone()
                if not row:
                    return None

                # 解析 state
                state_dict = json.loads(row['state'])
                state = SessionState(**state_dict)

                # 获取消息
                cursor.execute('''
                    SELECT role, content, timestamp
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id ASC
                ''', (session_id,))
                messages = []
                for msg_row in cursor.fetchall():
                    msg = Message(
                        role=MessageRole(msg_row['role']),
                        content=msg_row['content'],
                    )
                    messages.append(msg)

                session = Session(
                    session_id=row['session_id'],
                    state=state,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                )
                session._messages = messages
                return session
            finally:
                conn.close()

    def delete_session(self, session_id: str) -> bool:
        """删除 Session"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def update_session(self, session: Session) -> None:
        """更新 Session"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                now = datetime.utcnow()

                # 更新 Session
                cursor.execute('''
                    UPDATE sessions
                    SET state = ?, updated_at = ?
                    WHERE session_id = ?
                ''', (session.state.model_dump_json(), now.isoformat(), session.session_id))

                # 删除旧消息
                cursor.execute('DELETE FROM messages WHERE session_id = ?', (session.session_id,))

                # 插入新消息
                for msg in session.messages:
                    cursor.execute('''
                        INSERT INTO messages (session_id, role, content)
                        VALUES (?, ?, ?)
                    ''', (session.session_id, msg.role.value, msg.content))

                conn.commit()
            finally:
                conn.close()

    def list_sessions(self) -> List[str]:
        """列出所有 Session ID"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT session_id FROM sessions ORDER BY updated_at DESC')
                return [row['session_id'] for row in cursor.fetchall()]
            finally:
                conn.close()

    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
    ) -> Optional[Message]:
        """向 Session 添加消息"""
        with self._lock:
            conn = self._get_connection()
            try:
                # 先获取 Session
                session = self.get_session(session_id)
                if session is None:
                    return None

                message = Message(role=role, content=content)
                session.add_message(message)
                self.update_session(session)
                return message
            finally:
                conn.close()

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> Optional[List[Message]]:
        """获取 Session 的消息历史"""
        session = self.get_session(session_id)
        if session is None:
            return None

        if limit is None:
            return list(session.messages)
        return session.get_recent_messages(limit)

    def get_history_count(self, session_id: str) -> Optional[int]:
        """获取 Session 的消息数量"""
        session = self.get_session(session_id)
        if session is None:
            return None
        return session.get_history_count()

    def clear_messages(self, session_id: str) -> bool:
        """清空 Session 的消息历史"""
        session = self.get_session(session_id)
        if session is None:
            return False
        session.clear_messages()
        self.update_session(session)
        return True


# 全局单例
_sqlite_storage: Optional[SQLiteStorage] = None


def get_sqlite_storage() -> SQLiteStorage:
    """获取全局 SQLite 存储实例（单例模式）"""
    global _sqlite_storage
    if _sqlite_storage is None:
        _sqlite_storage = SQLiteStorage()
    return _sqlite_storage


def reset_sqlite_storage() -> None:
    """重置存储（主要用于测试）"""
    global _sqlite_storage
    _sqlite_storage = None
