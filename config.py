"""
Chokwadi AI - Configuration
All sensitive keys loaded from environment variables.
Supports switching between Anthropic (Claude) and OpenAI (GPT) providers.
"""
import os

# --- API Keys (set these as environment variables) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

# --- AI Provider Selection ---
# "anthropic" = Claude only
# "openai"    = GPT only  
# "auto"      = Anthropic first, fallback to OpenAI on failure
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto")

# Models
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
OPENAI_WHISPER_MODEL = "whisper-1"  # Always OpenAI for speech-to-text

# --- Twilio WhatsApp ---
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# --- App Settings ---
# Railway injects PORT env var; fallback to FLASK_PORT or 5000
FLASK_PORT = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5000")))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# --- Rate Limiting ---
MAX_REQUESTS_PER_USER_PER_HOUR = 20


def get_available_providers() -> list:
    """Return list of providers that have API keys configured."""
    providers = []
    if ANTHROPIC_API_KEY:
        providers.append("anthropic")
    if OPENAI_API_KEY:
        providers.append("openai")
    return providers


def get_active_provider() -> str:
    """
    Determine which provider to use based on config and available keys.
    Returns 'anthropic' or 'openai'.
    """
    available = get_available_providers()

    if AI_PROVIDER == "auto":
        if "anthropic" in available:
            return "anthropic"
        elif "openai" in available:
            return "openai"
        else:
            raise RuntimeError("No AI API keys configured! Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")

    if AI_PROVIDER in available:
        return AI_PROVIDER

    # Requested provider not available, try the other
    if available:
        print(f"[WARN] Requested provider '{AI_PROVIDER}' not configured, falling back to '{available[0]}'")
        return available[0]

    raise RuntimeError("No AI API keys configured! Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")


def get_fallback_provider() -> str | None:
    """Return the fallback provider if auto mode is on and both keys exist."""
    if AI_PROVIDER != "auto":
        return None
    available = get_available_providers()
    primary = get_active_provider()
    for p in available:
        if p != primary:
            return p
    return None
