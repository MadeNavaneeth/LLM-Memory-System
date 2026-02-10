"""
Conversation API Routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.database.models import MessageCreate, ConversationResponse
from app.services.conversation_service import get_conversation_service
from app.services.session_service import get_session_service
from app.services.nlp_service import get_nlp_service
from app.services.memory_service import get_memory_service
from app.services.gemini_service import GeminiService, get_gemini_service
from app.services.openai_service import OpenAIService, get_openai_service
from app.services.openrouter_service import OpenRouterService
from app.api.routes.settings import get_current_model, get_selected_model, provider_for_model
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("/", response_model=ConversationResponse)
async def add_message(message: MessageCreate, background_tasks: BackgroundTasks):
    """Add a new message and process with NLP"""
    # Verify session exists
    session_service = get_session_service()
    session = session_service.get_session(message.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Store the message
    conv_service = get_conversation_service()
    stored_message = conv_service.add_message(message)
    
    # Process with NLP in background to reduce latency
    if message.role == "user":
        # Add to background tasks
        background_tasks.add_task(
            process_conversation_background,
            message.message_text,
            message.user_id,
            stored_message.message_id
        )
        
        # Determine which service + model to use
        selected_model = get_selected_model()
        provider = provider_for_model(selected_model)
        
        logger.info(f"Using provider={provider}, model={selected_model}")
        
        if provider == "openrouter":
            llm_service = OpenRouterService(model_name=selected_model)
            service_name = "OpenRouter"
        elif provider == "openai":
            llm_service = OpenAIService(model_name=selected_model)
            service_name = "OpenAI"
        else:
            llm_service = GeminiService(model_name=selected_model)
            service_name = "Gemini"
        
        logger.info(f"Using {service_name} service")
        
        # Retrieve relevant memories for context (from EXISTING memories only)
        memory_strings = []
        try:
            memory_context = get_memory_service().retrieve_context(
                message.user_id,
                message.message_text,
                max_items=10
            )
            logger.debug(f"[RAG] Retrieved context object: {memory_context}")
            # Format memories for LLM
            memory_strings = [
                f"{mem.memory_type.upper()}: {mem.content}" 
                for mem in memory_context.memories
            ]
            logger.debug(f"Retrieved {len(memory_strings)} memories for context")
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
            memory_strings = []
        
        # Get conversation history
        history = conv_service.get_session_messages(message.session_id, limit=10)
        history_formatted = [
            {"role": msg.role, "content": msg.message_text}
            for msg in history[:-1]  # Exclude the message we just added
        ]
        
        # Generate response
        try:
            logger.info(f"Calling {service_name} LLM ({selected_model})")
            assistant_response = llm_service.generate_response(
                user_message=message.message_text,
                conversation_history=history_formatted,
                retrieved_memories=memory_strings
            )
        except Exception as e:
            logger.error(f"{service_name} error: {e}")
            assistant_response = "I'm having trouble thinking right now, but I heard you."
        
        # Store assistant response
        conv_service.add_message(
            MessageCreate(
                user_id=message.user_id,
                session_id=message.session_id,
                role="assistant",
                message_text=assistant_response
            )
        )
    
    return stored_message


def process_conversation_background(text: str, user_id: str, message_id: str):
    """Background task for NLP processing and memory extraction"""
    logger.info(f"[BACKGROUND] Starting NLP processing for message {message_id}")
    try:
        nlp_service = get_nlp_service()
        memory_service = get_memory_service()
        
        # This includes the SECOND Gemini call for entity extraction
        nlp_result = nlp_service.process_message(text, user_id, message_id)
        
        # Store extracted memories
        count_mem = 0
        for memory_item in nlp_result.get("memory_items", []):
            memory_service.store_memory(memory_item)
            count_mem += 1
            
        # Store entity relations
        count_rel = 0
        relations_to_store = nlp_result.get("entity_relations", [])
        for relation in relations_to_store:
            memory_service.store_entity_relation(relation)
            count_rel += 1
            
        logger.info(f"[BACKGROUND] Completed. Stored {count_mem} memories and {count_rel} relations.")
        
    except Exception as e:
        logger.error(f"[BACKGROUND] Error in NLP processing: {e}")



@router.get("/session/{session_id}", response_model=List[ConversationResponse])
async def get_session_messages(session_id: str, limit: int = 100):
    """Get all messages in a session"""
    service = get_conversation_service()
    return service.get_session_messages(session_id, limit)


@router.get("/user/{user_id}", response_model=List[ConversationResponse])
async def get_user_history(user_id: str, limit: int = 50):
    """Get conversation history for a user"""
    service = get_conversation_service()
    return service.get_user_history(user_id, limit)


@router.get("/user/{user_id}/search", response_model=List[ConversationResponse])
async def search_conversations(
    user_id: str,
    q: str = Query(..., description="Search query"),
    limit: int = 20
):
    """Search user's conversations"""
    service = get_conversation_service()
    return service.search_conversations(user_id, q, limit)


@router.get("/user/{user_id}/context", response_model=List[ConversationResponse])
async def get_recent_context(user_id: str, n: int = 10):
    """Get recent context for LLM"""
    service = get_conversation_service()
    return service.get_recent_context(user_id, n)
