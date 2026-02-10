"""
Session Service
Handles session lifecycle management
"""
from typing import Optional, List
from datetime import datetime

from app.database.sql_connection import get_db
from app.database.models import SessionCreate, Session, SessionResponse, generate_uuid


class SessionService:
    """Service for session management"""
    
    def __init__(self):
        self.db = get_db()
    
    def create_session(self, session_data: SessionCreate) -> SessionResponse:
        """Create a new session for a user"""
        session_id = generate_uuid()
        started_at = datetime.utcnow().isoformat()
        
        self.db.execute(
            """
            INSERT INTO sessions (session_id, user_id, started_at)
            VALUES (?, ?, ?)
            """,
            (session_id, session_data.user_id, started_at)
        )
        
        return SessionResponse(
            session_id=session_id,
            user_id=session_data.user_id,
            started_at=started_at,
            ended_at=None
        )
    
    def get_session(self, session_id: str) -> Optional[SessionResponse]:
        """Get session by ID"""
        row = self.db.fetch_one(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        
        if row:
            return SessionResponse(
                session_id=row["session_id"],
                user_id=row["user_id"],
                started_at=str(row["started_at"]),
                ended_at=str(row["ended_at"]) if row["ended_at"] else None
            )
        return None
    
    def get_user_sessions(self, user_id: str, limit: int = 20) -> List[SessionResponse]:
        """Get all sessions for a user"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM sessions 
            WHERE user_id = ? 
            ORDER BY started_at DESC 
            LIMIT ?
            """,
            (user_id, limit)
        )
        
        return [
            SessionResponse(
                session_id=row["session_id"],
                user_id=row["user_id"],
                started_at=str(row["started_at"]),
                ended_at=str(row["ended_at"]) if row["ended_at"] else None
            )
            for row in rows
        ]
    
    def get_active_session(self, user_id: str) -> Optional[SessionResponse]:
        """Get the current active (non-ended) session for a user"""
        row = self.db.fetch_one(
            """
            SELECT * FROM sessions 
            WHERE user_id = ? AND ended_at IS NULL
            ORDER BY started_at DESC 
            LIMIT 1
            """,
            (user_id,)
        )
        
        if row:
            return SessionResponse(
                session_id=row["session_id"],
                user_id=row["user_id"],
                started_at=str(row["started_at"]),
                ended_at=None
            )
        return None
    
    def end_session(self, session_id: str) -> bool:
        """End a session"""
        ended_at = datetime.utcnow().isoformat()
        
        self.db.execute(
            """
            UPDATE sessions SET ended_at = ?
            WHERE session_id = ?
            """,
            (ended_at, session_id)
        )
        return True
    
    def get_or_create_session(self, user_id: str) -> SessionResponse:
        """Get active session or create a new one"""
        active_session = self.get_active_session(user_id)
        
        if active_session:
            return active_session
        
        return self.create_session(SessionCreate(user_id=user_id))


# Singleton instance
session_service = SessionService()


def get_session_service() -> SessionService:
    return session_service
