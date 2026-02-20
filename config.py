"""
Chokwadi AI - Configuration
Supports Meta WhatsApp Cloud API + dual AI provider switching.
"""
import os

# --- AI API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- AI Provider Selection ---
# "anthropic" = Claude only
# "openai"    = GPT only
# "auto"      = Anthropic first, fallback to OpenAI on failure
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto")

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
OPENAI_WHISPER_MODEL = "whisper-1"

# --- Meta WhatsApp Cloud API ---
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "chokwadi-verify-2026")
GRAPH_API_VERSION = "v22.0"

# --- App Settings ---
FLASK_PORT = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5000")))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# --- Admin ---
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "")  # e.g. "263771841532" (no + prefix)

# --- Rate Limiting ---
MAX_REQUESTS_PER_USER_PER_HOUR = 20


def get_available_providers() -> list:
    providers = []
    if ANTHROPIC_API_KEY:
        providers.append("anthropic")
    if OPENAI_API_KEY:
        providers.append("openai")
    return providers


def get_active_provider() -> str:
    available = get_available_providers()
    if AI_PROVIDER == "auto":
        if "anthropic" in available:
            return "anthropic"
        elif "openai" in available:
            return "openai"
        else:
            raise RuntimeError("No AI API keys configured!")
    if AI_PROVIDER in available:
        return AI_PROVIDER
    if available:
        print(f"[WARN] '{AI_PROVIDER}' not configured, falling back to '{available[0]}'")
        return available[0]
    raise RuntimeError("No AI API keys configured!")


def get_fallback_provider() -> str | None:
    if AI_PROVIDER != "auto":
        return None
    available = get_available_providers()
    primary = get_active_provider()
    for p in available:
        if p != primary:
            return p
    return None
