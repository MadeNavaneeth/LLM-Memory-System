"""
API dependencies for FastAPI
"""
from app.database.sql_connection import get_db
from app.database.nosql_connection import get_mongo_db
from app.services.user_service import get_user_service
from app.services.session_service import get_session_service
from app.services.conversation_service import get_conversation_service
from app.services.memory_service import get_memory_service
from app.services.nlp_service import get_nlp_service


def get_sql_db():
    """Dependency for SQL database"""
    return get_db()


def get_nosql_db():
    """Dependency for NoSQL database"""
    return get_mongo_db()


def get_users_service():
    """Dependency for user service"""
    return get_user_service()


def get_sessions_service():
    """Dependency for session service"""
    return get_session_service()


def get_conversations_service():
    """Dependency for conversation service"""
    return get_conversation_service()


def get_memories_service():
    """Dependency for memory service"""
    return get_memory_service()


def get_nlp():
    """Dependency for NLP service"""
    return get_nlp_service()
