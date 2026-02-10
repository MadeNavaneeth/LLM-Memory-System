"""
Configuration settings for the LLM Memory Management System
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database settings
SQLITE_DB_PATH = BASE_DIR / "data" / "memory.db"
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "llm_memory")

# NLP settings
SPACY_MODEL = "en_core_web_sm"

# Memory settings
MAX_CONVERSATION_HISTORY = 100
MEMORY_CONFIDENCE_THRESHOLD = 0.5
MAX_MEMORY_ITEMS_PER_QUERY = 10

# API settings
API_PREFIX = "/api"

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ENABLE_OPENAI_DEFAULT = True

# Gemini settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ENABLE_GEMINI_DEFAULT = True

if GEMINI_API_KEY:
    print(f"[OK] Config: Gemini API key found")
else:
    print("[WARN] Config: No Gemini API key found")
    print("   Please set GEMINI_API_KEY in your .env file or environment variables")

if OPENAI_API_KEY and OPENAI_API_KEY.strip():
    print(f"[OK] Config: OpenAI API key found (key length: {len(OPENAI_API_KEY)})")
else:
    print("[WARN] Config: No OpenAI API key found")
    print("   Please set OPENAI_API_KEY in your .env file or environment variables")
