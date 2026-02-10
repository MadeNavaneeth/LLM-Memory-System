"""
OpenRouter LLM Service
Uses the OpenAI-compatible API at https://openrouter.ai/api/v1
Supports hundreds of models including free-tier options.
"""
import logging
from typing import List, Dict, Optional, Tuple, Any
import json
from openai import OpenAI
from app.api.routes.settings import get_next_api_key, mark_key_usage, mark_key_exhausted

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

class OpenRouterService:
    """Service for interacting with LLMs via OpenRouter (OpenAI-compatible)"""

    def __init__(self, model_name: str = "deepseek/deepseek-r1"):
        self.model_name = model_name

    def _get_client(self, api_key: str):
        """Configure and return a client instance with the given key"""
        try:
            return OpenAI(
                api_key=api_key,
                base_url=OPENROUTER_BASE_URL,
            )
        except Exception as e:
            logger.error(f"⚠ Error configuring OpenRouter client: {e}")
            return None

    def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        retrieved_memories: List[str] = None
    ) -> str:
        """
        Generate a response using OpenRouter API with key rotation/fallback
        """
        max_retries = 3
        last_error = None
        is_rate_limited = False

        for attempt in range(max_retries):
            api_key = get_next_api_key("openrouter")
            if not api_key:
                logger.warning("[OpenRouter] No active API keys available")
                break

            client = self._get_client(api_key)
            if not client:
                continue

            try:
                # Build messages
                messages = [
                    {"role": "system", "content": "You are a helpful AI assistant with persistent memory. Use the provided memory context to answer questions accurately and personally."}
                ]

                # Add memories
                if retrieved_memories and len(retrieved_memories) > 0:
                    memory_text = "IMPORTANT: You remember the following about this user:\n"
                    for i, memory in enumerate(retrieved_memories[:10], 1):
                        memory_text += f"{i}. {memory}\n"
                    messages.append({"role": "system", "content": memory_text})

                # Add conversation history
                if conversation_history:
                    for msg in conversation_history[-10:]:
                        role = "assistant" if msg.get("role") == "assistant" else "user"
                        messages.append({"role": role, "content": msg.get("content", "")})

                # Add current message
                messages.append({"role": "user", "content": user_message})

                logger.info(f"[OpenRouter] Calling model: {self.model_name}")
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.7,
                    extra_headers={
                        "HTTP-Referer": "http://localhost:8000",
                        "X-Title": "MemoryLLM",
                    }
                )

                result = response.choices[0].message.content
                mark_key_usage("openrouter", api_key, success=True)
                logger.info(f"[OpenRouter] Response received ({len(result)} chars)")
                return result

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                mark_key_usage("openrouter", api_key, success=False)

                if "429" in str(e) or "quota" in error_str or "rate" in error_str:
                    is_rate_limited = True
                    mark_key_exhausted("openrouter", api_key)
                    logger.warning(f"[OpenRouter] Rate limited (attempt {attempt+1}): {e}")
                    # Wait before retrying on rate limits
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(5)
                else:
                    logger.error(f"[OpenRouter] Error (attempt {attempt+1}): {e}")

        # Return user-friendly error messages
        model_short = self.model_name.split("/")[-1].split(":")[0] if "/" in self.model_name else self.model_name
        if is_rate_limited:
            return (
                f"⏳ **Rate limit reached** for **{model_short}** on OpenRouter. "
                f"Free models are limited to a few requests per minute. "
                f"Please wait ~30 seconds and try again, or switch to a different model from the dropdown."
            )
        return f"⚠️ Sorry, I couldn't reach **{model_short}** on OpenRouter right now. Please try a different model or check your API key."
