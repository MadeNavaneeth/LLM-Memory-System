"""
Settings API Routes
Handles LLM model selection and multi-API key configuration
Supports: Gemini, OpenAI, OpenRouter
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from datetime import datetime

router = APIRouter(prefix="/settings", tags=["settings"])

# ---------------------------------------------------------------------------
# Available Models Registry
# ---------------------------------------------------------------------------
AVAILABLE_MODELS: Dict[str, List[Dict[str, Any]]] = {
    "gemini": [
        {"id": "gemini-2.0-flash",   "name": "Gemini 2.0 Flash",   "free": False},
        {"id": "gemini-1.5-pro",     "name": "Gemini 1.5 Pro",     "free": False},
        {"id": "gemini-2.5-flash",   "name": "Gemini 2.5 Flash",   "free": False},
        {"id": "gemini-2.5-pro",     "name": "Gemini 2.5 Pro",     "free": False},
        {"id": "gemini-3-pro-preview", "name": "Gemini 3 Pro",     "free": False},
    ],
    "openai": [
        {"id": "gpt-4o-mini",        "name": "GPT-4o Mini",        "free": False},
        {"id": "gpt-4o",             "name": "GPT-4o",             "free": False},
        {"id": "gpt-3.5-turbo",      "name": "GPT-3.5 Turbo",     "free": False},
    ],
    "openrouter": [
        {"id": "arcee-ai/trinity-large-preview:free",       "name": "Arcee: Trinity Large Preview",  "free": True},
        {"id": "arcee-ai/trinity-mini:free",                "name": "Arcee: Trinity Mini",           "free": True},
        {"id": "openrouter/aurora-alpha",                   "name": "Aurora Alpha",                  "free": True},
        {"id": "deepseek/deepseek-r1-0528:free",            "name": "DeepSeek R1 0528",              "free": True},
        {"id": "openrouter/free",                           "name": "Free Models Router",            "free": True},
        {"id": "google/gemma-3-4b-it:free",                 "name": "Google Gemma 3 4B",             "free": True},
        {"id": "google/gemma-3-12b-it:free",                "name": "Google Gemma 3 12B",            "free": True},
        {"id": "google/gemma-3-27b-it:free",                "name": "Google Gemma 3 27B",            "free": True},
        {"id": "google/gemma-3n-e2b-it:free",               "name": "Google Gemma 3n 2B",            "free": True},
        {"id": "google/gemma-3n-e4b-it:free",               "name": "Google Gemma 3n 4B",            "free": True},
        {"id": "liquid/lfm-2.5-1.2b-instruct:free",         "name": "LiquidAI LFM2.5 Instruct",     "free": True},
        {"id": "liquid/lfm-2.5-1.2b-thinking:free",         "name": "LiquidAI LFM2.5 Thinking",     "free": True},
        {"id": "meta-llama/llama-3.2-3b-instruct:free",     "name": "Meta Llama 3.2 3B",            "free": True},
        {"id": "meta-llama/llama-3.3-70b-instruct:free",    "name": "Meta Llama 3.3 70B",           "free": True},
        {"id": "mistralai/mistral-small-3.1-24b-instruct:free","name": "Mistral Small 3.1 24B",     "free": True},
        {"id": "nvidia/nemotron-3-nano-30b-a3b:free",       "name": "NVIDIA Nemotron 3 Nano 30B",   "free": True},
        {"id": "nvidia/nemotron-nano-12b-v2-vl:free",       "name": "NVIDIA Nemotron Nano 12B VL",  "free": True},
        {"id": "nvidia/nemotron-nano-9b-v2:free",           "name": "NVIDIA Nemotron Nano 9B V2",   "free": True},
        {"id": "nousresearch/hermes-3-llama-3.1-405b:free", "name": "Nous Hermes 3 405B",           "free": True},
        {"id": "openai/gpt-oss-120b:free",                  "name": "OpenAI gpt-oss-120b",          "free": True},
        {"id": "openai/gpt-oss-20b:free",                   "name": "OpenAI gpt-oss-20b",           "free": True},
        {"id": "openrouter/pony-alpha",                     "name": "Pony Alpha",                   "free": True},
        {"id": "qwen/qwen3-4b:free",                        "name": "Qwen3 4B",                     "free": True},
        {"id": "qwen/qwen3-coder:free",                     "name": "Qwen3 Coder 480B",             "free": True},
        {"id": "qwen/qwen3-next-80b-a3b-instruct:free",     "name": "Qwen3 Next 80B",              "free": True},
        {"id": "stepfun/step-3.5-flash:free",               "name": "StepFun Step 3.5 Flash",       "free": True},
        {"id": "tngtech/deepseek-r1t-chimera:free",         "name": "TNG DeepSeek R1T Chimera",     "free": True},
        {"id": "tngtech/deepseek-r1t2-chimera:free",        "name": "TNG DeepSeek R1T2 Chimera",    "free": True},
        {"id": "tngtech/tng-r1t-chimera:free",              "name": "TNG R1T Chimera",              "free": True},
        {"id": "upstage/solar-pro-3:free",                  "name": "Upstage Solar Pro 3",          "free": True},
        {"id": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free", "name": "Venice Uncensored", "free": True},
        {"id": "z-ai/glm-4.5-air:free",                    "name": "Z.AI GLM 4.5 Air",             "free": True},
    ],
}

ALL_VALID_PROVIDERS = ["gemini", "openai", "openrouter"]

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
class ApiKeyMetadata(BaseModel):
    id: str
    label: str
    masked_key: str
    usage_count: int = 0
    error_count: int = 0
    status: str = "active"  # active, exhausted, error
    last_used: Optional[str] = None

class ApiKeyRequest(BaseModel):
    provider: str  # "gemini", "openai", or "openrouter"
    api_key: str
    label: Optional[str] = None

class ModelSelectRequest(BaseModel):
    model: str  # exact model id, e.g. "gemini-2.0-flash"

class SettingsResponse(BaseModel):
    model: str              # provider name for backward compat
    selected_model: str     # exact model id
    api_keys: Dict[str, List[ApiKeyMetadata]]

import logging
import json
from pathlib import Path

SETTINGS_FILE = Path("settings.json")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory settings store
# ---------------------------------------------------------------------------
_settings: Dict[str, Any] = {
    "model": os.getenv("LLM_MODEL", "gemini"),
    "selected_model": "gemini-2.0-flash",      # exact model id
    "gemini_keys": [],
    "openai_keys": [],
    "openrouter_keys": [],
}

# ---------------------------------------------------------------------------
# Helpers: determine provider from a model id
# ---------------------------------------------------------------------------
def provider_for_model(model_id: str) -> str:
    """Return the provider name for a given model id."""
    for provider, models in AVAILABLE_MODELS.items():
        if any(m["id"] == model_id for m in models):
            return provider
    return "gemini"  # default fallback

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_to_disk():
    """Save current settings to JSON file"""
    try:
        data = {
            "model": _settings["model"],
            "selected_model": _settings["selected_model"],
        }
        for provider in ALL_VALID_PROVIDERS:
            data[f"{provider}_keys"] = [
                {"key": k["key"], "meta": k["meta"].dict()}
                for k in _settings[f"{provider}_keys"]
            ]
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"[SETTINGS] Saved to {SETTINGS_FILE}")
    except Exception as e:
        logger.error(f"[SETTINGS] Failed to save settings: {e}")

def load_from_disk():
    """Load settings from JSON file"""
    global _settings
    if not SETTINGS_FILE.exists():
        return

    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)

        if "model" in data:
            _settings["model"] = data["model"]
        if "selected_model" in data:
            _settings["selected_model"] = data["selected_model"]

        for provider in ALL_VALID_PROVIDERS:
            key_list = []
            for item in data.get(f"{provider}_keys", []):
                meta_data = item["meta"]
                key_list.append({
                    "key": item["key"],
                    "meta": ApiKeyMetadata(**meta_data)
                })
            _settings[f"{provider}_keys"] = key_list

        logger.info(f"[SETTINGS] Loaded from {SETTINGS_FILE}")
    except Exception as e:
        logger.error(f"[SETTINGS] Failed to load settings: {e}")

# Initialize
load_from_disk()

# Seed env-var keys if not already present
env_gemini = os.getenv("GEMINI_API_KEY")
if env_gemini and not any(k["key"] == env_gemini for k in _settings["gemini_keys"]):
    _settings["gemini_keys"].append({
        "key": env_gemini,
        "meta": ApiKeyMetadata(
            id=env_gemini[:8],
            label="Env Key",
            masked_key=f"{env_gemini[:4]}...{env_gemini[-4:]}",
            status="active"
        )
    })

env_openai = os.getenv("OPENAI_API_KEY")
if env_openai and not any(k["key"] == env_openai for k in _settings["openai_keys"]):
    _settings["openai_keys"].append({
        "key": env_openai,
        "meta": ApiKeyMetadata(
            id=env_openai[:8],
            label="Env Key",
            masked_key=f"sk-...{env_openai[-4:]}",
            status="active"
        )
    })

env_openrouter = os.getenv("OPENROUTER_API_KEY")
if env_openrouter and not any(k["key"] == env_openrouter for k in _settings["openrouter_keys"]):
    _settings["openrouter_keys"].append({
        "key": env_openrouter,
        "meta": ApiKeyMetadata(
            id=env_openrouter[:8],
            label="Env Key",
            masked_key=f"{env_openrouter[:4]}...{env_openrouter[-4:]}",
            status="active"
        )
    })

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """Get current settings with key metadata"""
    return SettingsResponse(
        model=_settings["model"],
        selected_model=_settings["selected_model"],
        api_keys={
            p: [k["meta"] for k in _settings[f"{p}_keys"]]
            for p in ALL_VALID_PROVIDERS
        }
    )

@router.get("/models")
async def get_models():
    """Return available models grouped by provider, with key availability flags"""
    result = {}
    for provider, models in AVAILABLE_MODELS.items():
        has_keys = len(_settings.get(f"{provider}_keys", [])) > 0
        result[provider] = {
            "models": models,
            "has_keys": has_keys,
        }
    return {
        "providers": result,
        "selected_model": _settings["selected_model"],
    }

@router.post("/model")
async def update_model(update: ModelSelectRequest):
    """Update the selected model (exact model id)"""
    # Validate the model id exists
    provider = provider_for_model(update.model)
    _settings["selected_model"] = update.model
    _settings["model"] = provider
    logger.info(f"[SETTINGS] Model changed to: {update.model} (provider: {provider})")
    save_to_disk()
    return {"status": "success", "model": update.model, "provider": provider}

@router.post("/keys")
async def add_key(request: ApiKeyRequest):
    """Add a new API key"""
    if request.provider not in ALL_VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider. Must be one of: {ALL_VALID_PROVIDERS}")

    key_list = _settings[f"{request.provider}_keys"]

    # Check duplicate
    if any(k["key"] == request.api_key for k in key_list):
        raise HTTPException(status_code=400, detail="Key already exists")

    # Create metadata
    key_id = request.api_key[:8]
    masked = f"{request.api_key[:4]}...{request.api_key[-4:]}"
    label = request.label or f"Key {len(key_list) + 1}"

    new_entry = {
        "key": request.api_key,
        "meta": ApiKeyMetadata(
            id=key_id,
            label=label,
            masked_key=masked,
            status="active"
        )
    }

    key_list.append(new_entry)
    logger.info(f"[SETTINGS] Added {request.provider} key: {label}")

    # Set env var for first key of each provider
    if len(key_list) == 1:
        env_map = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
        env_var = env_map.get(request.provider)
        if env_var:
            os.environ[env_var] = request.api_key

    save_to_disk()
    return new_entry["meta"]

@router.delete("/keys/{provider}/{key_id}")
async def remove_key(provider: str, key_id: str):
    """Remove an API key"""
    if provider not in ALL_VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider")

    key_list = _settings[f"{provider}_keys"]
    initial_len = len(key_list)

    _settings[f"{provider}_keys"] = [k for k in key_list if k["meta"].id != key_id]

    if len(_settings[f"{provider}_keys"]) < initial_len:
        logger.info(f"[SETTINGS] Removed {provider} key: {key_id}")
        save_to_disk()
        return {"status": "success", "message": "API key removed"}

    raise HTTPException(status_code=404, detail="Key not found")

# ---------------------------------------------------------------------------
# Internal Helper Functions (used by services)
# ---------------------------------------------------------------------------
def get_current_model() -> str:
    return _settings["model"]

def get_selected_model() -> str:
    return _settings["selected_model"]

def get_next_api_key(provider: str) -> str:
    """Get the next active API key for rotation (Round Robin-ish)"""
    key_list = _settings.get(f"{provider}_keys", [])
    if not key_list:
        return ""

    # Find active keys
    active = [k for k in key_list if k["meta"].status != "exhausted"]

    if not active:
        logger.warning(f"[SETTINGS] All {provider} keys exhausted. Resetting status to try again.")
        for k in key_list:
            k["meta"].status = "active"
        active = key_list

    return active[0]["key"]

def mark_key_usage(provider: str, key: str, success: bool):
    """Update usage stats for a key"""
    key_list = _settings.get(f"{provider}_keys", [])
    for entry in key_list:
        if entry["key"] == key:
            meta = entry["meta"]
            meta.last_used = datetime.now().isoformat()
            if success:
                meta.usage_count += 1
                meta.status = "active"
                meta.error_count = 0
            else:
                meta.error_count += 1
            break

def mark_key_exhausted(provider: str, key: str):
    """Mark a key as exhausted (429)"""
    key_list = _settings.get(f"{provider}_keys", [])
    for entry in key_list:
        if entry["key"] == key:
            entry["meta"].status = "exhausted"
            logger.warning(f"[SETTINGS] Key {entry['meta'].label} marked as EXHAUSTED")
            break
