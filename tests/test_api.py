"""
Tests for API Endpoints
"""
import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health and info endpoints"""
    
    def test_health_check(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "sqlite" in data
    
    def test_api_info(self, client):
        """Test API info endpoint"""
        response = client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "endpoints" in data


class TestUserEndpoints:
    """Test user API endpoints"""
    
    def test_create_user(self, client):
        """Test user creation"""
        response = client.post(
            "/api/users",
            json={"username": "api_test_user"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["username"] == "api_test_user"
    
    def test_get_users(self, client):
        """Test getting all users"""
        response = client.get("/api/users")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_duplicate_user(self, client):
        """Test creating duplicate username fails"""
        client.post("/api/users", json={"username": "duplicate_user"})
        
        response = client.post(
            "/api/users",
            json={"username": "duplicate_user"}
        )
        assert response.status_code == 400


class TestSessionEndpoints:
    """Test session API endpoints"""
    
    @pytest.fixture
    def test_user(self, client):
        """Create a test user"""
        response = client.post(
            "/api/users",
            json={"username": "session_api_test_user"}
        )
        return response.json()
    
    def test_create_session(self, client, test_user):
        """Test session creation"""
        response = client.post(
            "/api/sessions",
            json={"user_id": test_user["user_id"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["user_id"] == test_user["user_id"]
    
    def test_get_active_session(self, client, test_user):
        """Test getting active session"""
        response = client.get(
            f"/api/sessions/user/{test_user['user_id']}/active"
        )
        assert response.status_code == 200


class TestConversationEndpoints:
    """Test conversation API endpoints"""
    
    @pytest.fixture
    def test_session(self, client):
        """Create a test user and session"""
        user_response = client.post(
            "/api/users",
            json={"username": "conv_api_test_user"}
        )
        user = user_response.json()
        
        session_response = client.post(
            "/api/sessions",
            json={"user_id": user["user_id"]}
        )
        session = session_response.json()
        
        return user, session
    
    def test_add_message(self, client, test_session):
        """Test adding a message"""
        user, session = test_session
        
        response = client.post(
            "/api/conversations",
            json={
                "user_id": user["user_id"],
                "session_id": session["session_id"],
                "role": "user",
                "message_text": "Hello, this is a test!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["message_text"] == "Hello, this is a test!"
    
    def test_get_session_messages(self, client, test_session):
        """Test getting session messages"""
        user, session = test_session
        
        # Add a message first
        client.post(
            "/api/conversations",
            json={
                "user_id": user["user_id"],
                "session_id": session["session_id"],
                "role": "user",
                "message_text": "Test message"
            }
        )
        
        response = client.get(
            f"/api/conversations/session/{session['session_id']}"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestMemoryEndpoints:
    """Test memory API endpoints"""
    
    @pytest.fixture
    def test_user(self, client):
        """Create a test user"""
        response = client.post(
            "/api/users",
            json={"username": "memory_api_test_user"}
        )
        return response.json()
    
    def test_store_memory(self, client, test_user):
        """Test storing a memory"""
        response = client.post(
            "/api/memory",
            json={
                "user_id": test_user["user_id"],
                "memory_type": "fact",
                "content": "I work as a software engineer",
                "confidence_score": 0.9
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "memory_id" in data
        assert data["memory_type"] == "fact"
    
    def test_get_user_memories(self, client, test_user):
        """Test getting user memories"""
        # Store a memory first
        client.post(
            "/api/memory",
            json={
                "user_id": test_user["user_id"],
                "memory_type": "preference",
                "content": "I prefer dark mode"
            }
        )
        
        response = client.get(
            f"/api/memory/user/{test_user['user_id']}"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_search_memories(self, client, test_user):
        """Test memory search"""
        # Store a memory
        client.post(
            "/api/memory",
            json={
                "user_id": test_user["user_id"],
                "memory_type": "skill",
                "content": "I know Python programming"
            }
        )
        
        response = client.post(
            "/api/memory/search",
            json={
                "user_id": test_user["user_id"],
                "query": "Python",
                "limit": 10
            }
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
