from app.services.memory_service import get_memory_service
from app.database.models import EntityRelationCreate, MemoryItemCreate

memory = get_memory_service()


def test_get_entities_from_relations_and_memories():
    user_id = "test_user_entities"

    # Clean state: insert a memory and a relation
    mem = MemoryItemCreate(
        user_id=user_id,
        memory_type="skill",
        content="I use Python and Redis for caching.",
        confidence_score=0.9
    )
    memory.store_memory(mem)

    relation = EntityRelationCreate(
        user_id=user_id,
        entity_1="Alice",
        entity_2="Django",
        relation_type="associated_with",
        confidence_score=0.8
    )
    memory.store_entity_relation(relation)

    entities = memory.get_entities(user_id)

    assert "Alice" in entities
    assert "Django" in entities
    # Python and Redis should be extracted from memory
    assert any(e.lower().startswith("python") for e in entities)
    assert any(e.lower().startswith("redis") for e in entities)
