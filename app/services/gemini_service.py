"""
Google Gemini LLM Service
Handles communication with Google Gemini API using the modern google-genai SDK
"""
import os
import json
import re
import random
import logging
from typing import List, Dict, Optional, Tuple, Any
from google import genai
from google.genai import types

from app.api.routes.settings import get_next_api_key, mark_key_usage, mark_key_exhausted

# Configure logging
logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google Gemini API using google-genai SDK"""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        
    def _get_client(self, api_key: str):
        """Create and return a client instance with the given key"""
        try:
            return genai.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"⚠ Error creating Gemini client with key {api_key[:8]}...: {e}")
            return None
    
    def generate_response(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]] = None,
        retrieved_memories: List[str] = None
    ) -> str:
        """
        Generate a response using Gemini API with key rotation/fallback
        """
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            api_key = get_next_api_key("gemini")
            if not api_key:
                logger.warning("[Gemini] No active API keys available")
                break
                
            client = self._get_client(api_key)
            if not client:
                continue
        
            try:
                # Build system prompt context
                context_parts = [
                    "You are a helpful AI assistant with persistent memory.",
                    "Use the information you remember to answer questions accurately and personally."
                ]
                
                # Add memories
                if retrieved_memories and len(retrieved_memories) > 0:
                    context_parts.append("\nIMPORTANT: You remember the following about this user:")
                    for i, memory in enumerate(retrieved_memories[:10], 1):
                        context_parts.append(f"{i}. {memory}")
                    context_parts.append("\nUse this information to answer questions. If the user asks about something you remember, mention it directly.")
                
                # Add conversation history
                history_context = ""
                if conversation_history:
                    history_context = "\nConversation History:\n"
                    for msg in conversation_history[-5:]: # Keep last 5 messages for context
                        role = "User" if msg.get("role") == "user" else "Model"
                        history_context += f"{role}: {msg.get('content')}\n"
                
                full_prompt = "\n".join(context_parts) + history_context + f"\nUser: {user_message}\nModel:"
                
                logger.info(f"[Gemini] Generating response (Attempt {attempt+1}) using {self.model_name}")
                
                # Generate response
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt
                )
                
                if response and response.text:
                    content = response.text.strip()
                    logger.debug(f"[Gemini] SUCCESS: {content[:50]}...")
                    mark_key_usage("gemini", api_key, success=True)
                    return content
                else:
                    logger.warning(f"[Gemini] Empty response received")
                    mark_key_usage("gemini", api_key, success=False)
                    
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                logger.error(f"[Gemini] Exception with key {api_key[:8]}...: {error_msg}")
                
                if "429" in error_msg or "ResourceExhausted" in error_msg:
                    logger.warning(f"[Gemini] Key exhausted via Exception. Switching...")
                    mark_key_exhausted("gemini", api_key)
                else:
                    mark_key_usage("gemini", api_key, success=False)
                
        logger.error(f"[Gemini] All attempts failed. Last error: {last_error}")
        return self._fallback_response()
    
    def _fallback_response(self) -> str:
        """Fallback response when Gemini is unavailable"""
        responses = [
            "I'm having trouble connecting to my brain right now. Please try again in a moment.",
            "My thought process was interrupted. Could you repeat that?",
            "I'm experiencing high traffic. Give me a second to recover.",
            "Connection issue - I'll be back online shortly."
        ]
        return random.choice(responses)
    
    def is_available(self) -> bool:
        """Check if Gemini API is available (has at least one key)"""
        return bool(get_next_api_key("gemini"))
    
    def extract_entities_and_relations(self, text: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Use Gemini to extract entities and relations from text using key rotation.
        Returns (entities_list, relations_list) where each is a list of dicts.
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            api_key = get_next_api_key("gemini")
            if not api_key:
                return [], []
                
            client = self._get_client(api_key)
            if not client:
                continue
        
            # Create prompt for entity and relation extraction
            extraction_prompt = f"""
You are an expert at extracting structured information from text.
Extract entities and relationships from the following text: "{text}"

TASK 1 - Extract ENTITIES (that explicitly appear in text):
- PERSON: Names explicitly mentioned
- SKILL: Technologies or skills mentioned
- COLOR: Colors mentioned
- PLACE: Locations mentioned
- HOBBY: Activities mentioned
- PREFERENCE: Things liked/preferred

TASK 2 - Create RELATIONS:
- associated_with, likes, knows, uses, prefers, has, lives_in, works_with
- Connect extracted entities based on the text.

Return ONLY valid JSON with this structure:
{{
  "entities": [
    {{"text": "extracted_name", "label": "PERSON", "confidence": 0.95}}
  ],
  "relations": [
    {{"entity_1": "name", "entity_2": "skill", "relation_type": "knows", "reason": "context"}}
  ]
}}
"""
            try:
                # Configure generation for JSON using modern config
                config = types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
                
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=extraction_prompt,
                    config=config
                )
                
                if response and response.text:
                    content = response.text.strip()
                    # Clean up any potential markdown formatting
                    clean_content = content.replace("```json", "").replace("```", "").strip()
                    
                    try:
                        extracted_data = json.loads(clean_content)
                        entities = extracted_data.get("entities", [])
                        relations = extracted_data.get("relations", [])
                        
                        logger.info(f"[Gemini] Extracted: {len(entities)} entities, {len(relations)} relations")
                        mark_key_usage("gemini", api_key, success=True)
                        return entities, relations
                        
                    except json.JSONDecodeError:
                        logger.error(f"[Gemini] JSON parse error")
                        mark_key_usage("gemini", api_key, success=False)
                        return [], []
                
                mark_key_usage("gemini", api_key, success=False)
            
            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    mark_key_exhausted("gemini", api_key)
                else:
                    mark_key_usage("gemini", api_key, success=False)
                    
        return [], []

# Singleton instance
gemini_service = GeminiService()

def get_gemini_service() -> GeminiService:
    return gemini_service
