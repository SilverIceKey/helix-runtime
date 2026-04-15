from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from helix.storage import get_storage


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=list)
async def list_sessions():
    """
    列出所有 Session
    """
    storage = get_storage()
    sessions = storage.list_sessions()
    return [
        {
            "session_id": s.session_id,
            "message_count": len(s.messages),
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


class CreateSessionRequest(BaseModel):
    """创建 Session 请求"""
    session_id: Optional[str] = None


class CreateSessionResponse(BaseModel):
    """创建 Session 响应"""
    session_id: str
    created_at: datetime


class SessionResponse(BaseModel):
    """Session 响应"""
    session_id: str
    state: dict
    message_count: int
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=CreateSessionResponse, status_code=201)
async def create_session(request: CreateSessionRequest = None):
    """
    创建新 Session
    """
    storage = get_storage()
    session_id = request.session_id if request else None

    try:
        session = storage.create_session(session_id)
        return CreateSessionResponse(
            session_id=session.session_id,
            created_at=session.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    获取 Session
    """
    storage = get_storage()
    session = storage.get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionResponse(
        session_id=session.session_id,
        state=session.state.model_dump(),
        message_count=len(session.messages),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    删除 Session
    """
    storage = get_storage()
    deleted = storage.delete_session(session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {"message": f"Session {session_id} deleted"}


@router.get("/{session_id}/messages")
async def get_messages(session_id: str, limit: Optional[int] = 5):
    """
    获取 Session 的消息历史
    """
    storage = get_storage()
    messages = storage.get_messages(session_id, limit)

    if messages is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ],
    }
