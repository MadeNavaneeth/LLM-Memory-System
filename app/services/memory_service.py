"""
Memory Service
Handles memory storage, retrieval, and management
"""
from typing import Optional, List
from datetime import datetime
import re

from app.database.sql_connection import get_db
from app.database.models import (
    MemoryItemCreate, MemoryItem, MemoryItemResponse,
    EntityRelationCreate, EntityRelation, EntityRelationResponse,
    MemoryAccessLog, MemorySearchQuery, MemoryRetrievalResult,
    generate_uuid
)
from app.config import MAX_MEMORY_ITEMS_PER_QUERY, MEMORY_CONFIDENCE_THRESHOLD
import logging

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for memory management"""
    
    def __init__(self):
        self.db = get_db()
    
    # ============================================
    # Memory Items Operations
    # ============================================
    
    def store_memory(self, memory_data: MemoryItemCreate) -> MemoryItemResponse:
        """Store a new memory item"""
        memory_id = generate_uuid()
        created_at = datetime.utcnow().isoformat()
        
        self.db.execute(
            """
            INSERT INTO memory_items 
            (memory_id, user_id, memory_type, content, confidence_score, 
             source_message_id, created_at, last_accessed, importance_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                memory_data.user_id,
                memory_data.memory_type,
                memory_data.content,
                memory_data.confidence_score,
                memory_data.source_message_id,
                created_at,
                created_at,
                memory_data.importance_weight
            )
        )
        
        return MemoryItemResponse(
            memory_id=memory_id,
            user_id=memory_data.user_id,
            memory_type=memory_data.memory_type,
            content=memory_data.content,
            confidence_score=memory_data.confidence_score,
            source_message_id=memory_data.source_message_id,
            created_at=created_at,
            last_accessed=created_at,
            importance_weight=memory_data.importance_weight
        )
    
    def get_memory(self, memory_id: str) -> Optional[MemoryItemResponse]:
        """Get a memory item by ID"""
        row = self.db.fetch_one(
            "SELECT * FROM memory_items WHERE memory_id = ?",
            (memory_id,)
        )
        
        if row:
            return self._row_to_memory_response(row)
        return None
    
    def get_user_memories(
        self, 
        user_id: str, 
        memory_type: Optional[str] = None,
        limit: int = 50
    ) -> List[MemoryItemResponse]:
        """Get memories for a user, optionally filtered by type"""
        if memory_type:
            rows = self.db.fetch_all(
                """
                SELECT * FROM memory_items 
                WHERE user_id = ? AND memory_type = ?
                ORDER BY importance_weight DESC, created_at DESC
                LIMIT ?
                """,
                (user_id, memory_type, limit)
            )
        else:
            rows = self.db.fetch_all(
                """
                SELECT * FROM memory_items 
                WHERE user_id = ?
                ORDER BY importance_weight DESC, created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            )
        
        return [self._row_to_memory_response(row) for row in rows]
    
    def search_memories(self, search_query: MemorySearchQuery) -> List[MemoryItemResponse]:
        """Full-text search in user's memories"""
        # Sanitize query for FTS5 - escape special characters
        search_terms = search_query.query.strip()
        if not search_terms:
            search_terms = "*"  # Match all if empty
        
        # Try FTS5 search first
        try:
            # Use FTS5 for search
            base_query = """
                SELECT m.* FROM memory_items m
                JOIN memory_fts fts ON m.memory_id = fts.memory_id
                WHERE fts.content MATCH ? 
                AND m.user_id = ?
                AND m.confidence_score >= ?
            """
            
            params = [search_terms, search_query.user_id, search_query.min_confidence]
            
            if search_query.memory_types:
                placeholders = ",".join(["?" for _ in search_query.memory_types])
                base_query += f" AND m.memory_type IN ({placeholders})"
                params.extend(search_query.memory_types)
            
            base_query += " ORDER BY m.importance_weight DESC LIMIT ?"
            params.append(search_query.limit)
            
            rows = self.db.fetch_all(base_query, tuple(params))
            
            # Log memory access
            for row in rows:
                self._log_memory_access(row["memory_id"], "search")
            
            return [self._row_to_memory_response(row) for row in rows]
        
        except Exception as e:
            # Fallback to simple LIKE search if FTS5 fails
            logger.warning(f"FTS5 search failed: {e}, falling back to LIKE search")
            try:
                base_query = """
                    SELECT m.* FROM memory_items m
                    WHERE m.user_id = ?
                    AND m.confidence_score >= ?
                    AND m.content LIKE ?
                """
                
                params = [search_query.user_id, search_query.min_confidence, f"%{search_terms}%"]
                
                if search_query.memory_types:
                    placeholders = ",".join(["?" for _ in search_query.memory_types])
                    base_query += f" AND m.memory_type IN ({placeholders})"
                    params.extend(search_query.memory_types)
                
                base_query += " ORDER BY m.importance_weight DESC LIMIT ?"
                params.append(search_query.limit)
                
                rows = self.db.fetch_all(base_query, tuple(params))
                return [self._row_to_memory_response(row) for row in rows]
            except Exception as e2:
                logger.error(f"Both FTS5 and LIKE search failed: {e2}")
                # Return empty list if both fail
                return []
    
    def update_memory_access(self, memory_id: str) -> None:
        """Update last accessed time for a memory"""
        now = datetime.utcnow().isoformat()
        self.db.execute(
            "UPDATE memory_items SET last_accessed = ? WHERE memory_id = ?",
            (now, memory_id)
        )
    
    def update_memory_importance(self, memory_id: str, importance: float) -> None:
        """Update importance weight of a memory"""
        self.db.execute(
            "UPDATE memory_items SET importance_weight = ? WHERE memory_id = ?",
            (importance, memory_id)
        )
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory item"""
        self.db.execute(
            "DELETE FROM memory_items WHERE memory_id = ?",
            (memory_id,)
        )
        return True
    
    # ============================================
    # Entity Relations Operations
    # ============================================
    
    def store_entity_relation(self, relation_data: EntityRelationCreate) -> EntityRelationResponse:
        """Store a new entity relation"""
        relation_id = generate_uuid()
        created_at = datetime.utcnow().isoformat()
        
        self.db.execute(
            """
            INSERT INTO entity_relations 
            (relation_id, user_id, entity_1, entity_2, relation_type, 
             confidence_score, source_message_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                relation_id,
                relation_data.user_id,
                relation_data.entity_1,
                relation_data.entity_2,
                relation_data.relation_type,
                relation_data.confidence_score,
                relation_data.source_message_id,
                created_at
            )
        )
        logger.debug(f"[MEM] Stored relation {relation_id}: {relation_data.entity_1} - {relation_data.relation_type} - {relation_data.entity_2}")
        
        return EntityRelationResponse(
            relation_id=relation_id,
            user_id=relation_data.user_id,
            entity_1=relation_data.entity_1,
            entity_2=relation_data.entity_2,
            relation_type=relation_data.relation_type,
            confidence_score=relation_data.confidence_score,
            source_message_id=relation_data.source_message_id,
            created_at=created_at
        )
    
    def get_entity_relations(self, user_id: str, entity: Optional[str] = None) -> List[EntityRelationResponse]:
        """Get entity relations for a user"""
        if entity:
            rows = self.db.fetch_all(
                """
                SELECT * FROM entity_relations 
                WHERE user_id = ? AND (entity_1 = ? OR entity_2 = ?)
                ORDER BY confidence_score DESC
                """,
                (user_id, entity, entity)
            )
        else:
            rows = self.db.fetch_all(
                """
                SELECT * FROM entity_relations 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (user_id,)
            )
        
        resp = [self._row_to_relation_response(row) for row in rows]
        logger.debug(f"[MEM] get_entity_relations returned {len(resp)} relations for user {user_id} (filter entity={entity})")
        return resp

    def get_entities(self, user_id: str) -> List[str]:
        """Return a deduplicated list of entity names for a user.
        Aggregates from entity_relations and memory_items content heuristically.
        """
        entities = set()

        # From relations
        rows = self.db.fetch_all(
            "SELECT entity_1, entity_2 FROM entity_relations WHERE user_id = ?",
            (user_id,)
        )
        for r in rows:
            if r.get("entity_1"):
                entities.add(r["entity_1"])
            if r.get("entity_2"):
                entities.add(r["entity_2"])

        # From memory contents (heuristic extraction)
        mem_rows = self.db.fetch_all(
            "SELECT content FROM memory_items WHERE user_id = ?",
            (user_id,)
        )
        token_regex = r"\b[A-Z][a-zA-Z0-9.+#-]{2,}\b"
        known_techs = {"python","javascript","docker","kubernetes","react","django","flask","redis","postgresql","mysql","mongodb","aws","fastapi","tailwind","node","express","scikit","pandas","numpy","typescript"}

        for m in mem_rows:
            text = m.get("content","")
            # capitalized tokens
            for match in re.finditer(token_regex, text):
                entities.add(match.group())
            # lowercase tech tokens
            words = re.split(r'[^a-z0-9+#+-]+', text.lower())
            for w in words:
                if w in known_techs:
                    entities.add(w.capitalize())

        return sorted(entities)

    
    # ============================================
    # Memory Retrieval for LLM Context
    # ============================================
    
    def retrieve_context(
        self, 
        user_id: str, 
        current_message: str,
        max_items: int = MAX_MEMORY_ITEMS_PER_QUERY
    ) -> MemoryRetrievalResult:
        """Retrieve relevant memories for LLM context injection"""
        
        # Search for relevant memories based on current message
        search_query = MemorySearchQuery(
            user_id=user_id,
            query=current_message,
            limit=max_items,
            min_confidence=MEMORY_CONFIDENCE_THRESHOLD
        )
        
        memories = self.search_memories(search_query)
        logger.debug(f"[MEM] Initial search found {len(memories)} memories. Query='{current_message}'")
        
        # Always include important memories even if not in search results
        query_lower = current_message.lower()
        
        # Detect query type to prioritize relevant memories
        is_name_query = any(word in query_lower for word in ['name', 'who am', 'what am', 'my name', 'call me', 'who are you'])
        is_skill_query = any(word in query_lower for word in ['skill', 'can you', 'what can', 'know how', 'expert', 'proficient', 'experience', 'programming', 'coding'])
        is_preference_query = any(word in query_lower for word in ['like', 'prefer', 'favorite', 'love', 'hate', 'enjoy', 'what do you like', 'what are your'])
        
        if is_name_query or is_skill_query or is_preference_query or len(memories) < 3:
            # Build query based on detected query type
            if is_name_query:
                # Prioritize name-related facts
                important_memories = self.db.fetch_all(
                    """
                    SELECT * FROM memory_items 
                    WHERE user_id = ? 
                    AND (
                        content LIKE '%name%' OR 
                        content LIKE '%Name%' OR 
                        (memory_type = 'fact' AND importance_weight >= 0.7)
                    )
                    ORDER BY 
                        CASE WHEN content LIKE '%name%' THEN 1 ELSE 2 END,
                        importance_weight DESC, 
                        confidence_score DESC
                    LIMIT 5
                    """,
                    (user_id,)
                )
            elif is_skill_query:
                # Prioritize skills
                important_memories = self.db.fetch_all(
                    """
                    SELECT * FROM memory_items 
                    WHERE user_id = ? 
                    AND memory_type = 'skill'
                    ORDER BY importance_weight DESC, confidence_score DESC
                    LIMIT 8
                    """,
                    (user_id,)
                )
            elif is_preference_query:
                # Prioritize preferences
                important_memories = self.db.fetch_all(
                    """
                    SELECT * FROM memory_items 
                    WHERE user_id = ? 
                    AND memory_type = 'preference'
                    ORDER BY importance_weight DESC, confidence_score DESC
                    LIMIT 8
                    """,
                    (user_id,)
                )
            else:
                # General: get high-importance memories of all types
                important_memories = self.db.fetch_all(
                    """
                    SELECT * FROM memory_items 
                    WHERE user_id = ? 
                    AND (
                        importance_weight >= 0.7 OR
                        (memory_type IN ('fact', 'skill', 'preference') AND confidence_score >= 0.6)
                    )
                    ORDER BY 
                        CASE memory_type 
                            WHEN 'fact' THEN 1
                            WHEN 'skill' THEN 2
                            WHEN 'preference' THEN 3
                            ELSE 4
                        END,
                        importance_weight DESC, 
                        confidence_score DESC
                    LIMIT 8
                    """,
                    (user_id,)
                )
            
            # Add important memories that aren't already in the results
            existing_memory_ids = {mem.memory_id for mem in memories}
            for row in important_memories:
                if row["memory_id"] not in existing_memory_ids:
                    memories.append(self._row_to_memory_response(row))
        
        # KEYWORD FALLBACK:
        # If we still have few memories, try a keyword overlap search
        # This helps with questions like "What is my secret password?" -> "My secret password is..."
        # where "secret" and "password" are key shared terms.
        if len(memories) < 3:
            stopwords = {"what", "is", "my", "the", "a", "an", "and", "or", "to", "in", "on", "at", "do", "you", "know", "tell", "me"}
            keywords = {word for word in query_lower.split() if word not in stopwords and len(word) > 2}
            
            if keywords:
                # Construct OR query for keywords
                keyword_conditions = " OR ".join([f"content LIKE ?" for _ in keywords])
                params = [user_id] + [f"%{kw}%" for kw in keywords]
                
                keyword_memories = self.db.fetch_all(
                    f"""
                    SELECT * FROM memory_items 
                    WHERE user_id = ? 
                    AND ({keyword_conditions})
                    ORDER BY importance_weight DESC, confidence_score DESC
                    LIMIT 5
                    """,
                    tuple(params)
                )
                
                for row in keyword_memories:
                    if row["memory_id"] not in existing_memory_ids:
                        memories.append(self._row_to_memory_response(row))
                        existing_memory_ids.add(row["memory_id"])
                logger.debug(f"[MEM] Keyword fallback found index {len(keyword_memories)} items. Total memories now: {len(memories)}")
        
        # Sort by importance and limit to max_items
        memories.sort(key=lambda m: (m.importance_weight, m.confidence_score), reverse=True)
        memories = memories[:max_items]
        
        # Get related entity relations
        entity_relations = []
        for memory in memories:
            # Extract potential entities from memory content
            words = memory.content.split()
            for word in words:
                if len(word) > 3:  # Simple heuristic
                    relations = self.get_entity_relations(user_id, word)
                    entity_relations.extend(relations)
        
        # Deduplicate relations
        seen_relation_ids = set()
        unique_relations = []
        for rel in entity_relations:
            if rel.relation_id not in seen_relation_ids:
                seen_relation_ids.add(rel.relation_id)
                unique_relations.append(rel)
        
        return MemoryRetrievalResult(
            memories=memories,
            entity_relations=unique_relations[:20],  # Limit relations
            total_count=len(memories)
        )
    
    # ============================================
    # Memory Access Logging
    # ============================================
    
    def _log_memory_access(self, memory_id: str, context: str) -> None:
        """Log memory access for analytics"""
        access_id = generate_uuid()
        access_time = datetime.utcnow().isoformat()
        
        self.db.execute(
            """
            INSERT INTO memory_access_logs (access_id, memory_id, access_time, usage_context)
            VALUES (?, ?, ?, ?)
            """,
            (access_id, memory_id, access_time, context)
        )
        
        # Update last_accessed in memory_items
        self.update_memory_access(memory_id)
    
    def get_memory_access_stats(self, memory_id: str) -> dict:
        """Get access statistics for a memory"""
        row = self.db.fetch_one(
            """
            SELECT COUNT(*) as access_count, 
                   MAX(access_time) as last_access
            FROM memory_access_logs 
            WHERE memory_id = ?
            """,
            (memory_id,)
        )
        
        return {
            "memory_id": memory_id,
            "access_count": row["access_count"] if row else 0,
            "last_access": row["last_access"] if row else None
        }
    
    # ============================================
    # Helper Methods
    # ============================================
    
    def _row_to_memory_response(self, row: dict) -> MemoryItemResponse:
        return MemoryItemResponse(
            memory_id=row["memory_id"],
            user_id=row["user_id"],
            memory_type=row["memory_type"],
            content=row["content"],
            confidence_score=row["confidence_score"],
            source_message_id=row["source_message_id"],
            created_at=str(row["created_at"]),
            last_accessed=str(row["last_accessed"]),
            importance_weight=row["importance_weight"]
        )
    
    def _row_to_relation_response(self, row: dict) -> EntityRelationResponse:
        return EntityRelationResponse(
            relation_id=row["relation_id"],
            user_id=row["user_id"],
            entity_1=row["entity_1"],
            entity_2=row["entity_2"],
            relation_type=row["relation_type"],
            confidence_score=row["confidence_score"],
            source_message_id=row["source_message_id"],
            created_at=str(row["created_at"])
        )


# Singleton instance
memory_service = MemoryService()


def get_memory_service() -> MemoryService:
    return memory_service
