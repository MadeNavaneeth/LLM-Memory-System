"""
Memory API Routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.database.models import (
    MemoryItemCreate, MemoryItemResponse, 
    EntityRelationCreate, EntityRelationResponse,
    MemorySearchQuery, MemoryRetrievalResult, ContextRequest
)
from app.services.memory_service import get_memory_service
from app.database.nosql_connection import get_mongo_db

router = APIRouter(prefix="/memory", tags=["Memory"])


# ============================================
# Memory Items Endpoints
# ============================================

@router.post("/", response_model=MemoryItemResponse)
async def store_memory(memory: MemoryItemCreate):
    """Store a new memory item"""
    service = get_memory_service()
    return service.store_memory(memory)


@router.get("/{memory_id}", response_model=MemoryItemResponse)
async def get_memory(memory_id: str):
    """Get memory by ID"""
    service = get_memory_service()
    memory = service.get_memory(memory_id)
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return memory


@router.get("/user/{user_id}", response_model=List[MemoryItemResponse])
async def get_user_memories(
    user_id: str,
    memory_type: Optional[str] = None,
    limit: int = 50
):
    """Get memories for a user"""
    service = get_memory_service()
    return service.get_user_memories(user_id, memory_type, limit)


@router.post("/search", response_model=List[MemoryItemResponse])
async def search_memories(search_query: MemorySearchQuery):
    """Search user's memories with full-text search"""
    service = get_memory_service()
    return service.search_memories(search_query)


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory item"""
    service = get_memory_service()
    
    memory = service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    service.delete_memory(memory_id)
    return {"message": "Memory deleted"}


@router.put("/{memory_id}/importance")
async def update_importance(memory_id: str, importance: float):
    """Update memory importance weight"""
    if not 0 <= importance <= 1:
        raise HTTPException(status_code=400, detail="Importance must be between 0 and 1")
    
    service = get_memory_service()
    
    memory = service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    service.update_memory_importance(memory_id, importance)
    return {"message": "Importance updated"}


# ============================================
# Entity Relations Endpoints
# ============================================

@router.post("/relations", response_model=EntityRelationResponse)
async def store_relation(relation: EntityRelationCreate):
    """Store a new entity relation"""
    service = get_memory_service()
    return service.store_entity_relation(relation)


@router.get("/relations/{user_id}", response_model=List[EntityRelationResponse])
async def get_relations(user_id: str, entity: Optional[str] = None):
    """Get entity relations for a user"""
    service = get_memory_service()
    return service.get_entity_relations(user_id, entity)


@router.get("/entities/{user_id}")
async def get_entities(user_id: str):
    """Get list of unique entities for a user (from relations and memories)."""
    service = get_memory_service()
    return service.get_entities(user_id)


# ============================================
# Context Retrieval Endpoints
# ============================================

@router.post("/retrieve", response_model=MemoryRetrievalResult)
async def retrieve_context(request: ContextRequest):
    """Retrieve relevant memories for LLM context injection"""
    service = get_memory_service()
    return service.retrieve_context(
        request.user_id,
        request.current_message,
        request.max_context_items
    )


# ============================================
# NLP Logs Endpoints (MongoDB)
# ============================================

@router.get("/nlp-logs/{message_id}")
async def get_nlp_log(message_id: str):
    """Get NLP processing log from MongoDB"""
    mongo = get_mongo_db()
    
    if not mongo.is_connected:
        raise HTTPException(status_code=503, detail="MongoDB not available")
    
    log = mongo.get_nlp_log(message_id)
    if not log:
        raise HTTPException(status_code=404, detail="NLP log not found")
    
    # Convert ObjectId to string
    log["_id"] = str(log["_id"])
    return log


@router.get("/nlp-logs/user/{user_id}")
async def get_user_nlp_logs(user_id: str, limit: int = 50):
    """Get NLP logs for a user"""
    mongo = get_mongo_db()
    
    if not mongo.is_connected:
        return {"message": "MongoDB not available", "logs": []}
    
    logs = mongo.get_user_nlp_logs(user_id, limit)
    
    # Convert ObjectIds to strings
    for log in logs:
        log["_id"] = str(log["_id"])
    
    return {"logs": logs}


# ============================================
# Statistics Endpoints
# ============================================

@router.get("/stats/{memory_id}")
async def get_memory_stats(memory_id: str):
    """Get access statistics for a memory"""
    service = get_memory_service()
    return service.get_memory_access_stats(memory_id)


# ============================================
# NoSQL Database Endpoints
# ============================================

@router.get("/nosql/status")
async def get_nosql_status():
    """Get MongoDB connection status and statistics"""
    mongo = get_mongo_db()
    return mongo.get_collection_stats()


@router.get("/nosql/collections/{collection_name}")
async def get_collection_documents(collection_name: str, limit: int = 50):
    """Get documents from a MongoDB collection"""
    mongo = get_mongo_db()
    
    if not mongo.is_connected:
        return {"connected": False, "documents": []}
    
    valid_collections = ["nlp_processing_logs", "embedding_cache", "raw_extractions"]
    if collection_name not in valid_collections:
        return {"error": f"Invalid collection. Valid: {valid_collections}"}
    
    docs = mongo.get_all_documents(collection_name, limit)
    return {"collection": collection_name, "count": len(docs), "documents": docs}


@router.get("/nosql/user/{user_id}/all")
async def get_all_user_nosql_data(user_id: str):
    """Get all NoSQL data for a user (for UI display)"""
    mongo = get_mongo_db()
    
    if not mongo.is_connected:
        return {
            "connected": False,
            "nlp_logs": [],
            "message": "MongoDB not connected"
        }
    
    nlp_logs = mongo.get_user_nlp_logs(user_id, limit=20)
    
    return {
        "connected": True,
        "nlp_logs": nlp_logs,
        "total_logs": len(nlp_logs)
    }

