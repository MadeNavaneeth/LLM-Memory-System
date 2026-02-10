"""
Conversation Service
Handles conversation logging and retrieval
"""
from typing import Optional, List
from datetime import datetime

from app.database.sql_connection import get_db
from app.database.models import MessageCreate, ConversationLog, ConversationResponse, generate_uuid


class ConversationService:
    """Service for conversation management"""
    
    def __init__(self):
        self.db = get_db()
    
    def add_message(self, message_data: MessageCreate) -> ConversationResponse:
        """Add a new message to conversation log"""
        message_id = generate_uuid()
        timestamp = datetime.utcnow().isoformat()
        
        # Estimate token count (rough approximation: 1 token ≈ 4 characters)
        token_count = message_data.token_count or len(message_data.message_text) // 4
        
        self.db.execute(
            """
            INSERT INTO conversation_logs 
            (message_id, user_id, session_id, role, message_text, timestamp, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                message_data.user_id,
                message_data.session_id,
                message_data.role,
                message_data.message_text,
                timestamp,
                token_count
            )
        )
        
        return ConversationResponse(
            message_id=message_id,
            user_id=message_data.user_id,
            session_id=message_data.session_id,
            role=message_data.role,
            message_text=message_data.message_text,
            timestamp=timestamp,
            token_count=token_count
        )
    
    def get_message(self, message_id: str) -> Optional[ConversationResponse]:
        """Get a specific message by ID"""
        row = self.db.fetch_one(
            "SELECT * FROM conversation_logs WHERE message_id = ?",
            (message_id,)
        )
        
        if row:
            return ConversationResponse(
                message_id=row["message_id"],
                user_id=row["user_id"],
                session_id=row["session_id"],
                role=row["role"],
                message_text=row["message_text"],
                timestamp=str(row["timestamp"]),
                token_count=row["token_count"]
            )
        return None
    
    def get_session_messages(self, session_id: str, limit: int = 100) -> List[ConversationResponse]:
        """Get all messages in a session"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM conversation_logs 
            WHERE session_id = ? 
            ORDER BY timestamp ASC 
            LIMIT ?
            """,
            (session_id, limit)
        )
        
        return [
            ConversationResponse(
                message_id=row["message_id"],
                user_id=row["user_id"],
                session_id=row["session_id"],
                role=row["role"],
                message_text=row["message_text"],
                timestamp=str(row["timestamp"]),
                token_count=row["token_count"]
            )
            for row in rows
        ]
    
    def get_user_history(self, user_id: str, limit: int = 50) -> List[ConversationResponse]:
        """Get conversation history for a user across all sessions"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM conversation_logs 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (user_id, limit)
        )
        
        return [
            ConversationResponse(
                message_id=row["message_id"],
                user_id=row["user_id"],
                session_id=row["session_id"],
                role=row["role"],
                message_text=row["message_text"],
                timestamp=str(row["timestamp"]),
                token_count=row["token_count"]
            )
            for row in rows
        ]
    
    def search_conversations(self, user_id: str, query: str, limit: int = 20) -> List[ConversationResponse]:
        """Full-text search in user's conversations"""
        # Use FTS5 for full-text search
        rows = self.db.fetch_all(
            """
            SELECT c.* FROM conversation_logs c
            JOIN conversation_fts fts ON c.message_id = fts.message_id
            WHERE fts.message_text MATCH ? AND c.user_id = ?
            ORDER BY c.timestamp DESC
            LIMIT ?
            """,
            (query, user_id, limit)
        )
        
        return [
            ConversationResponse(
                message_id=row["message_id"],
                user_id=row["user_id"],
                session_id=row["session_id"],
                role=row["role"],
                message_text=row["message_text"],
                timestamp=str(row["timestamp"]),
                token_count=row["token_count"]
            )
            for row in rows
        ]
    
    def get_recent_context(self, user_id: str, n_messages: int = 10) -> List[ConversationResponse]:
        """Get the most recent N messages for context"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM conversation_logs 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (user_id, n_messages)
        )
        
        # Reverse to get chronological order
        return [
            ConversationResponse(
                message_id=row["message_id"],
                user_id=row["user_id"],
                session_id=row["session_id"],
                role=row["role"],
                message_text=row["message_text"],
                timestamp=str(row["timestamp"]),
                token_count=row["token_count"]
            )
            for row in reversed(rows)
        ]


# Singleton instance
conversation_service = ConversationService()


def get_conversation_service() -> ConversationService:
    return conversation_service
