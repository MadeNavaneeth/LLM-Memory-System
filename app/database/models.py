"""
Pydantic Models for the LLM Memory Management System
Defines data models for all entities
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ============================================
# User Models
# ============================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    preferences_summary: Optional[str] = None


class User(BaseModel):
    user_id: str = Field(default_factory=generate_uuid)
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    preferences_summary: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    username: str
    created_at: str
    preferences_summary: Optional[str] = None


# ============================================
# Session Models
# ============================================

class SessionCreate(BaseModel):
    user_id: str


class Session(BaseModel):
    session_id: str = Field(default_factory=generate_uuid)
    user_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    started_at: str
    ended_at: Optional[str] = None


# ============================================
# Conversation Models
# ============================================

class MessageCreate(BaseModel):
    user_id: str
    session_id: str
    role: Literal["user", "assistant", "system"]
    message_text: str
    token_count: Optional[int] = 0


class ConversationLog(BaseModel):
    message_id: str = Field(default_factory=generate_uuid)
    user_id: str
    session_id: str
    role: Literal["user", "assistant", "system"]
    message_text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    token_count: int = 0


class ConversationResponse(BaseModel):
    message_id: str
    user_id: str
    session_id: str
    role: str
    message_text: str
    timestamp: str
    token_count: int


# ============================================
# Memory Models
# ============================================

class MemoryItemCreate(BaseModel):
    user_id: str
    memory_type: Literal["fact", "preference", "rule", "skill", "context"]
    content: str
    confidence_score: float = Field(default=0.5, ge=0, le=1)
    source_message_id: Optional[str] = None
    importance_weight: float = Field(default=0.5, ge=0, le=1)


class MemoryItem(BaseModel):
    memory_id: str = Field(default_factory=generate_uuid)
    user_id: str
    memory_type: Literal["fact", "preference", "rule", "skill", "context"]
    content: str
    confidence_score: float = 0.5
    source_message_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    importance_weight: float = 0.5


class MemoryItemResponse(BaseModel):
    memory_id: str
    user_id: str
    memory_type: str
    content: str
    confidence_score: float
    source_message_id: Optional[str] = None
    created_at: str
    last_accessed: str
    importance_weight: float


# ============================================
# Entity Relation Models
# ============================================

class EntityRelationCreate(BaseModel):
    user_id: str
    entity_1: str
    entity_2: str
    relation_type: Literal[
        "associated_with", "depends_on", "overrides", "similar_to", "opposite_of", "part_of",
        "likes", "knows", "uses", "prefers", "has", "lives_in", "works_with", "related_to"
    ]
    confidence_score: float = Field(default=0.5, ge=0, le=1)
    source_message_id: Optional[str] = None


class EntityRelation(BaseModel):
    relation_id: str = Field(default_factory=generate_uuid)
    user_id: str
    entity_1: str
    entity_2: str
    relation_type: Literal[
        "associated_with", "depends_on", "overrides", "similar_to", "opposite_of", "part_of",
        "likes", "knows", "uses", "prefers", "has", "lives_in", "works_with", "related_to"
    ]
    confidence_score: float = 0.5
    source_message_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EntityRelationResponse(BaseModel):
    relation_id: str
    user_id: str
    entity_1: str
    entity_2: str
    relation_type: str
    confidence_score: float
    source_message_id: Optional[str] = None
    created_at: str


# ============================================
# Memory Access Log Models
# ============================================

class MemoryAccessLog(BaseModel):
    access_id: str = Field(default_factory=generate_uuid)
    memory_id: str
    access_time: datetime = Field(default_factory=datetime.utcnow)
    usage_context: Optional[str] = None


# ============================================
# NLP Processing Models (for MongoDB)
# ============================================

class ExtractedEntity(BaseModel):
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0


class NLPProcessingLog(BaseModel):
    message_id: str
    user_id: str
    memory_type: Optional[str] = None  # Added for report compliance
    extracted_entities: List[ExtractedEntity] = []
    extracted_intents: List[str] = []
    sentiment: Optional[dict] = None
    keywords: List[str] = []
    processing_time_ms: int = 0
    nlp_model_version: str = "en_core_web_sm"


# ============================================
# Search & Retrieval Models
# ============================================

class MemorySearchQuery(BaseModel):
    user_id: str
    query: str
    memory_types: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=50)
    min_confidence: float = Field(default=0.0, ge=0, le=1)


class MemoryRetrievalResult(BaseModel):
    memories: List[MemoryItemResponse]
    entity_relations: List[EntityRelationResponse]
    total_count: int


class ContextRequest(BaseModel):
    user_id: str
    current_message: str
    max_context_items: int = Field(default=10, ge=1, le=50)
