"""
User Service
Handles all user-related operations
"""
from typing import Optional, List
from datetime import datetime

from app.database.sql_connection import get_db
from app.database.models import UserCreate, User, UserResponse, generate_uuid


class UserService:
    """Service for user management operations"""
    
    def __init__(self):
        self.db = get_db()
    
    def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user"""
        user_id = generate_uuid()
        created_at = datetime.utcnow().isoformat()
        
        self.db.execute(
            """
            INSERT INTO users (user_id, username, created_at, preferences_summary)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, user_data.username, created_at, user_data.preferences_summary)
        )
        
        return UserResponse(
            user_id=user_id,
            username=user_data.username,
            created_at=created_at,
            preferences_summary=user_data.preferences_summary
        )
    
    def get_user(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID"""
        row = self.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        if row:
            return UserResponse(
                user_id=row["user_id"],
                username=row["username"],
                created_at=str(row["created_at"]),
                preferences_summary=row["preferences_summary"]
            )
        return None
    
    def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """Get user by username"""
        row = self.db.fetch_one(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        
        if row:
            return UserResponse(
                user_id=row["user_id"],
                username=row["username"],
                created_at=str(row["created_at"]),
                preferences_summary=row["preferences_summary"]
            )
        return None
    
    def get_all_users(self) -> List[UserResponse]:
        """Get all users"""
        rows = self.db.fetch_all("SELECT * FROM users ORDER BY created_at DESC")
        
        return [
            UserResponse(
                user_id=row["user_id"],
                username=row["username"],
                created_at=str(row["created_at"]),
                preferences_summary=row["preferences_summary"]
            )
            for row in rows
        ]
    
    def update_preferences(self, user_id: str, preferences_summary: str) -> bool:
        """Update user preferences"""
        self.db.execute(
            """
            UPDATE users SET preferences_summary = ?
            WHERE user_id = ?
            """,
            (preferences_summary, user_id)
        )
        return True
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user (cascades to all related data)"""
        self.db.execute(
            "DELETE FROM users WHERE user_id = ?",
            (user_id,)
        )
        return True


# Singleton instance
user_service = UserService()


def get_user_service() -> UserService:
    return user_service
