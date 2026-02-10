"""
Tests for SQL Database Operations
"""
import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.sql_connection import SQLiteConnection
from app.database.models import UserCreate, SessionCreate, MessageCreate, MemoryItemCreate
from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService


class TestSQLiteConnection:
    """Test SQLite database connection and operations"""
    
    def test_connection_singleton(self):
        """Test that connection is a singleton"""
        db1 = SQLiteConnection()
        db2 = SQLiteConnection()
        assert db1 is db2
    
    def test_schema_initialization(self):
        """Test that schema is properly initialized"""
        db = SQLiteConnection()
        
        # Check tables exist
        tables = db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [t['name'] for t in tables]
        
        assert 'users' in table_names
        assert 'sessions' in table_names
        assert 'conversation_logs' in table_names
        assert 'memory_items' in table_names
        assert 'entity_relations' in table_names
        assert 'memory_access_logs' in table_names


class TestUserService:
    """Test User Service CRUD operations"""
    
    @pytest.fixture
    def user_service(self):
        return UserService()
    
    def test_create_user(self, user_service):
        """Test creating a new user"""
        user = user_service.create_user(
            UserCreate(username="test_user_1")
        )
        
        assert user.user_id is not None
        assert user.username == "test_user_1"
    
    def test_get_user(self, user_service):
        """Test retrieving a user"""
        created = user_service.create_user(
            UserCreate(username="test_user_2")
        )
        
        retrieved = user_service.get_user(created.user_id)
        
        assert retrieved is not None
        assert retrieved.user_id == created.user_id
        assert retrieved.username == created.username
    
    def test_get_user_by_username(self, user_service):
        """Test retrieving user by username"""
        user_service.create_user(
            UserCreate(username="test_user_3")
        )
        
        retrieved = user_service.get_user_by_username("test_user_3")
        
        assert retrieved is not None
        assert retrieved.username == "test_user_3"


class TestSessionService:
    """Test Session Service operations"""
    
    @pytest.fixture
    def setup_user(self):
        user_service = UserService()
        user = user_service.create_user(
            UserCreate(username="session_test_user")
        )
        return user
    
    @pytest.fixture
    def session_service(self):
        return SessionService()
    
    def test_create_session(self, session_service, setup_user):
        """Test creating a new session"""
        session = session_service.create_session(
            SessionCreate(user_id=setup_user.user_id)
        )
        
        assert session.session_id is not None
        assert session.user_id == setup_user.user_id
        assert session.ended_at is None
    
    def test_end_session(self, session_service, setup_user):
        """Test ending a session"""
        session = session_service.create_session(
            SessionCreate(user_id=setup_user.user_id)
        )
        
        session_service.end_session(session.session_id)
        
        updated = session_service.get_session(session.session_id)
        assert updated.ended_at is not None


class TestConversationService:
    """Test Conversation Service operations"""
    
    @pytest.fixture
    def setup_session(self):
        user_service = UserService()
        session_service = SessionService()
        
        user = user_service.create_user(
            UserCreate(username="conv_test_user")
        )
        session = session_service.create_session(
            SessionCreate(user_id=user.user_id)
        )
        
        return user, session
    
    @pytest.fixture
    def conversation_service(self):
        return ConversationService()
    
    def test_add_message(self, conversation_service, setup_session):
        """Test adding a message"""
        user, session = setup_session
        
        message = conversation_service.add_message(
            MessageCreate(
                user_id=user.user_id,
                session_id=session.session_id,
                role="user",
                message_text="Hello, this is a test message!"
            )
        )
        
        assert message.message_id is not None
        assert message.message_text == "Hello, this is a test message!"
        assert message.role == "user"
    
    def test_get_session_messages(self, conversation_service, setup_session):
        """Test retrieving session messages"""
        user, session = setup_session
        
        # Add multiple messages
        for i in range(3):
            conversation_service.add_message(
                MessageCreate(
                    user_id=user.user_id,
                    session_id=session.session_id,
                    role="user" if i % 2 == 0 else "assistant",
                    message_text=f"Message {i}"
                )
            )
        
        messages = conversation_service.get_session_messages(session.session_id)
        
        assert len(messages) >= 3


class TestMemoryService:
    """Test Memory Service operations"""
    
    @pytest.fixture
    def setup_user(self):
        user_service = UserService()
        user = user_service.create_user(
            UserCreate(username="memory_test_user")
        )
        return user
    
    @pytest.fixture
    def memory_service(self):
        return MemoryService()
    
    def test_store_memory(self, memory_service, setup_user):
        """Test storing a memory item"""
        memory = memory_service.store_memory(
            MemoryItemCreate(
                user_id=setup_user.user_id,
                memory_type="fact",
                content="My name is John and I live in New York.",
                confidence_score=0.85
            )
        )
        
        assert memory.memory_id is not None
        assert memory.memory_type == "fact"
        assert memory.confidence_score == 0.85
    
    def test_get_user_memories(self, memory_service, setup_user):
        """Test retrieving user memories"""
        # Store some memories
        for mem_type in ["fact", "preference", "skill"]:
            memory_service.store_memory(
                MemoryItemCreate(
                    user_id=setup_user.user_id,
                    memory_type=mem_type,
                    content=f"Test {mem_type} content"
                )
            )
        
        memories = memory_service.get_user_memories(setup_user.user_id)
        
        assert len(memories) >= 3
    
    def test_get_memories_by_type(self, memory_service, setup_user):
        """Test filtering memories by type"""
        memory_service.store_memory(
            MemoryItemCreate(
                user_id=setup_user.user_id,
                memory_type="preference",
                content="I love pizza"
            )
        )
        
        preferences = memory_service.get_user_memories(
            setup_user.user_id, 
            memory_type="preference"
        )
        
        for pref in preferences:
            assert pref.memory_type == "preference"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
