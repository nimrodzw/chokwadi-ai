"""
Chokwadi AI - Main Application
WhatsApp bot for misinformation detection in Zimbabwe.
Deployed on Railway with Twilio WhatsApp integration.
"""
import os
import re
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse

from config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    FLASK_PORT, FLASK_DEBUG, AI_PROVIDER,
    get_active_provider, get_available_providers
)
from core.analyzer import analyze_text, analyze_image_with_vision
from core.transcriber import transcribe_voice_note
from core.link_scanner import scan_url, format_scan_results

app = Flask(__name__)

# ─── Runtime state (allows live switching via admin commands) ──────────────
_runtime_provider_override = None


def _current_provider() -> str:
    """Get the current effective provider, considering runtime overrides."""
    if _runtime_provider_override:
        return _runtime_provider_override
    return get_active_provider()


# ─── Messages ─────────────────────────────────────────────────────────────

WELCOME_MESSAGE = """🇿🇼 *Mauya ku Chokwadi AI!* 🇿🇼
_Welcome to Chokwadi AI!_

Ndiri AI inokubatsira kuziva kana zvaunoona pa internet zviri zvechokwadi kana kwete.
(I'm an AI that helps you check if what you see online is true or false.)

📱 *Tumira chero chimwe chezvinhu izvi:*
(Send me any of the following:)

📝 Text message / WhatsApp forward
🖼️ Screenshot or image
🎤 Voice note
🔗 Link/URL

Ndichaongorora ndikuudze kana zviri zvechokwadi! ✅
(I'll analyse it and tell you if it's credible!)

_Basa rangu (What I check):_
• Nhau dzenhema (Fake news)
• Scams ne fraud (EcoCash, investment scams)
• Fake government notices
• Health misinformation
• Phishing links

Tumira message yako izvozvi! 👇
(Send your message now!)

🇿🇼 _Chokwadi AI - Zvokwadi Zvinobatsira (The truth helps)_
"""

GREETING_WORDS = {
    "hi", "hello", "help", "start", "menu",
    "mauya", "salibonani", "ndeipi", "hey", "howzit",
    "maswera sei", "makadii", "kunjani",
}


# ─── Admin Commands (for you to switch providers live) ─────────────────────

ADMIN_PHONE = os.getenv("ADMIN_PHONE", "")  # e.g. "whatsapp:+263771841532"


def _handle_admin_command(command: str) -> str | None:
    """
    Process admin commands. Returns response string or None if not a command.

    Commands:
        !status    - Show current provider and available providers
        !claude    - Switch to Anthropic Claude
        !gpt       - Switch to OpenAI GPT
        !auto      - Switch to auto mode (Claude first, GPT fallback)
    """
    global _runtime_provider_override

    cmd = command.strip().lower()

    if cmd == "!status":
        available = get_available_providers()
        current = _current_provider()
        override = _runtime_provider_override or "none"
        return (
            f"⚙️ *Chokwadi AI Status*\n\n"
            f"Config provider: {AI_PROVIDER}\n"
            f"Runtime override: {override}\n"
            f"Active provider: *{current}*\n"
            f"Available: {', '.join(available)}"
        )

    elif cmd == "!claude":
        _runtime_provider_override = "anthropic"
        return "✅ Switched to *Anthropic Claude*"

    elif cmd == "!gpt":
        _runtime_provider_override = "openai"
        return "✅ Switched to *OpenAI GPT*"

    elif cmd == "!auto":
        _runtime_provider_override = None
        return "✅ Switched to *auto mode* (Claude → GPT fallback)"

    return None


# ─── Content Detection ─────────────────────────────────────────────────────

def detect_content_type(body: str, num_media: int, media_type: str = "") -> str:
    """Classify the incoming message type."""
    if num_media > 0:
        if "audio" in media_type or "ogg" in media_type or "voice" in media_type:
            return "voice"
        elif "image" in media_type or "jpeg" in media_type or "png" in media_type or "webp" in media_type:
            return "image"
        elif "pdf" in media_type or "document" in media_type:
            return "document"
        return "image"  # default media → image

    if re.search(r'https?://[^\s<>"{}|\\^`\[\]]+', body):
        return "link"

    return "text"


def extract_urls(text: str) -> list:
    return re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)


# ─── Webhook ───────────────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    """Twilio WhatsApp webhook — receives messages, returns analysis."""
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")
    num_media = int(request.values.get("NumMedia", 0))
    media_type = request.values.get("MediaContentType0", "") if num_media > 0 else ""
    media_url = request.values.get("MediaUrl0", "") if num_media > 0 else ""

    print(f"\n{'='*60}")
    print(f"[IN] From: {sender}")
    print(f"[IN] Body: {incoming_msg[:120]}")
    print(f"[IN] Media: {num_media} ({media_type})")
    print(f"[IN] Provider: {_current_provider()}")
    print(f"{'='*60}")

    resp = MessagingResponse()

    # --- Admin commands (only from your number) ---
    if sender == ADMIN_PHONE and incoming_msg.startswith("!"):
        admin_resp = _handle_admin_command(incoming_msg)
        if admin_resp:
            resp.message(admin_resp)
            return str(resp)

    # --- Greetings / help ---
    if incoming_msg.lower() in GREETING_WORDS:
        resp.message(WELCOME_MESSAGE)
        return str(resp)

    # --- Process content ---
    content_type = detect_content_type(incoming_msg, num_media, media_type)

    try:
        if content_type == "voice":
            response_text = _handle_voice(media_url, sender)

        elif content_type == "image":
            response_text = _handle_image(media_url, sender)

        elif content_type == "link":
            response_text = _handle_link(incoming_msg, sender)

        else:
            response_text = _handle_text(incoming_msg, sender)

        # WhatsApp has a ~1600 char limit per message
        _send_response(resp, response_text)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        resp.message(
            "⚠️ Pane dambudziko rekutarisa content iyi. "
            "(There was an error processing your request. Please try again.)\n\n"
            "🇿🇼 _Chokwadi AI_"
        )

    return str(resp)


# ─── Content Handlers ──────────────────────────────────────────────────────

def _handle_text(message: str, sender: str) -> str:
    if len(message) < 5:
        return (
            "📝 Ndapota tumira message yakareba kuti ndikwanise kuiongorora.\n"
            "(Please send a longer message for me to analyse.)\n\n"
            "Tumira 'help' kuti uwane rubatsiro. (Send 'help' for assistance.)"
        )
    print(f"[PROCESS] Text analysis for {sender}")
    return analyze_text(message, content_type="text")


def _handle_voice(media_url: str, sender: str) -> str:
    print(f"[PROCESS] Voice note for {sender}")
    twilio_auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    result = transcribe_voice_note(media_url, twilio_auth)

    if result.get("text"):
        print(f"[TRANSCRIBED] Lang: {result['language']} | Text: {result['text'][:150]}...")
        analysis = analyze_text(result["text"], content_type="voice")
        return (
            f"🎤 *Voice Note Transcription:*\n"
            f"_{result['text'][:500]}_\n\n"
            f"{analysis}"
        )
    return (
        "⚠️ Handina kukwanisa kunzwa voice note yacho. "
        "(I couldn't process this voice note. "
        "Please try sending it again or send the information as text.)"
    )


def _handle_image(media_url: str, sender: str) -> str:
    print(f"[PROCESS] Image analysis for {sender}")
    if not media_url:
        return (
            "⚠️ Handina kukwanisa kuona mufananidzo wacho. "
            "(I couldn't access the image. Please try again.)"
        )
    twilio_auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return analyze_image_with_vision(media_url, twilio_auth)


def _handle_link(message: str, sender: str) -> str:
    urls = extract_urls(message)
    if not urls:
        return analyze_text(message, content_type="text")

    print(f"[PROCESS] Link scan: {urls[0]}")
    scan_results = scan_url(urls[0])
    scan_report = format_scan_results(scan_results)

    combined = (
        f"URL submitted for analysis: {urls[0]}\n\n"
        f"{scan_report}\n\n"
        f"Additional context from user: {message}"
    )
    return analyze_text(combined, content_type="link")


def _send_response(resp: MessagingResponse, text: str):
    """Send response, splitting into multiple messages if needed."""
    if len(text) <= 1500:
        resp.message(text)
    else:
        chunks = [text[i:i + 1500] for i in range(0, len(text), 1500)]
        for chunk in chunks:
            resp.message(chunk)


# ─── Health & Info Endpoints ───────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Chokwadi AI",
        "tagline": "Zvokwadi Zvinobatsira - The Truth Helps",
        "description": "Multimodal misinformation detection for Zimbabwean youth",
        "status": "running",
        "provider": _current_provider(),
        "available_providers": get_available_providers(),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "provider": _current_provider()})


# ─── Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("🇿🇼  CHOKWADI AI - Zvokwadi Zvinobatsira")
    print("    Multimodal Misinformation Detection for Zimbabwe")
    print("=" * 60)
    print(f"  Provider : {_current_provider()}")
    print(f"  Available: {', '.join(get_available_providers())}")
    print(f"  Port     : {FLASK_PORT}")
    print(f"  Debug    : {FLASK_DEBUG}")
    print(f"  Admin    : {ADMIN_PHONE or 'not set'}")
    print("=" * 60)

    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)
