"""
OpenAI LLM Service
Handles communication with OpenAI API (GPT-4o, GPT-3.5-turbo)
"""
import logging
from typing import List, Dict, Optional, Tuple, Any
import json
from openai import OpenAI
from app.api.routes.settings import get_next_api_key, mark_key_usage, mark_key_exhausted

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI API"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        
    def _get_client(self, api_key: str):
        """Configure and return a client instance with the given key"""
        try:
            return OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"⚠ Error configuring OpenAI client with key {api_key[:8]}...: {e}")
            return None
    
    def generate_response(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]] = None,
        retrieved_memories: List[str] = None
    ) -> str:
        """
        Generate a response using OpenAI API with key rotation/fallback
        """
        max_retries = 3
        last_error = None
        
        # Try up to 3 different keys if available
        for attempt in range(max_retries):
            api_key = get_next_api_key("openai")
            if not api_key:
                logger.warning("[OpenAI] No active API keys available")
                break
                
            client = self._get_client(api_key)
            if not client:
                continue
        
            try:
                # Build messages
                messages = [
                    {"role": "system", "content": "You are a helpful AI assistant with persistent memory. Use the provided memory context to answer questions accurately and personally."}
                ]
                
                # Add memories using system message injection finding
                if retrieved_memories and len(retrieved_memories) > 0:
                    memory_text = "IMPORTANT: You remember the following about this user:\n"
                    for i, memory in enumerate(retrieved_memories[:10], 1):
                        memory_text += f"{i}. {memory}\n"
                    memory_text += "\nUse this information to answer questions."
                    messages.append({"role": "system", "content": memory_text})
                
                # Add conversation history
                if conversation_history:
                    for msg in conversation_history[-5:]:
                        role = "user" if msg.get("role") == "user" else "assistant"
                        messages.append({"role": role, "content": msg.get("content")})
                
                # Add current message
                messages.append({"role": "user", "content": user_message})
                
                logger.info(f"[OpenAI] Generating response (Attempt {attempt+1})")
                
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.7
                )
                
                content = response.choices[0].message.content
                if content:
                    logger.debug(f"[OpenAI] SUCCESS: {content[:50]}...")
                    mark_key_usage("openai", api_key, success=True)
                    return content
                else:
                    logger.warning(f"[OpenAI] Empty response received")
                    mark_key_usage("openai", api_key, success=False)
                    
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                logger.error(f"[OpenAI] Exception with key {api_key[:8]}...: {error_msg}")
                
                if "429" in error_msg or "quota" in error_msg.lower():
                    logger.warning(f"[OpenAI] Key exhausted (429/Quota). Switching...")
                    mark_key_exhausted("openai", api_key)
                else:
                    logger.warning(f"[OpenAI] Usage error. Marking failure.")
                    mark_key_usage("openai", api_key, success=False)
                
        logger.error(f"[OpenAI] All attempts failed. Last error: {last_error}")
        return "I'm having trouble retrieving a response from OpenAI right now. Please check your API keys."

    def is_available(self) -> bool:
        """Check if OpenAI API is available (has at least one key)"""
        return bool(get_next_api_key("openai"))

# Singleton instance
openai_service = OpenAIService()

def get_openai_service() -> OpenAIService:
    return openai_service
