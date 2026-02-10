"""
Session API Routes
"""
from typing import List
from fastapi import APIRouter, HTTPException

from app.database.models import SessionCreate, SessionResponse
from app.services.session_service import get_session_service
from app.services.user_service import get_user_service

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse)
async def create_session(session: SessionCreate):
    """Create a new session"""
    # Verify user exists
    user_service = get_user_service()
    if not user_service.get_user(session.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    service = get_session_service()
    return service.create_session(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session by ID"""
    service = get_session_service()
    session = service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.get("/user/{user_id}", response_model=List[SessionResponse])
async def get_user_sessions(user_id: str, limit: int = 20):
    """Get all sessions for a user"""
    service = get_session_service()
    return service.get_user_sessions(user_id, limit)


@router.get("/user/{user_id}/active", response_model=SessionResponse)
async def get_active_session(user_id: str):
    """Get or create active session for a user"""
    service = get_session_service()
    return service.get_or_create_session(user_id)


@router.put("/{session_id}/end")
async def end_session(session_id: str):
    """End a session"""
    service = get_session_service()
    
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    service.end_session(session_id)
    return {"message": "Session ended"}
