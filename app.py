"""
Chokwadi AI - Main Application
WhatsApp bot via Meta WhatsApp Cloud API.
Deployed on Railway.
"""
import os
import re
import json
import httpx
from flask import Flask, request, jsonify

from config import (
    WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_VERIFY_TOKEN, GRAPH_API_VERSION,
    FLASK_PORT, FLASK_DEBUG, AI_PROVIDER, ADMIN_PHONE,
    get_active_provider, get_available_providers
)
from core.analyzer import analyze_text, analyze_image_with_vision
from core.transcriber import transcribe_voice_note
from core.link_scanner import scan_url, format_scan_results

app = Flask(__name__)

# ─── Runtime provider override ────────────────────────────────────────────
_runtime_provider_override = None


def _current_provider() -> str:
    if _runtime_provider_override:
        return _runtime_provider_override
    return get_active_provider()


# ─── WhatsApp Cloud API Helper ────────────────────────────────────────────

MESSAGES_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def send_whatsapp_message(to: str, text: str):
    """Send a text message via Meta WhatsApp Cloud API."""
    # WhatsApp has a ~4096 char limit per message
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)] if len(text) > 4000 else [text]

    for chunk in chunks:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": chunk},
        }
        try:
            resp = httpx.post(MESSAGES_URL, headers=HEADERS, json=payload, timeout=30)
            print(f"[SEND] To {to}: {resp.status_code} {resp.text[:200]}")
            if resp.status_code != 200:
                print(f"[SEND ERROR] {resp.text}")
        except Exception as e:
            print(f"[SEND ERROR] {e}")


def mark_as_read(message_id: str):
    """Mark a message as read (shows blue ticks)."""
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    try:
        httpx.post(MESSAGES_URL, headers=HEADERS, json=payload, timeout=10)
    except Exception:
        pass


# ─── Messages ─────────────────────────────────────────────────────────────

WELCOME_MESSAGE = """🇿🇼 *Mauya ku Chokwadi AI!* 🇿🇼
_Welcome to Chokwadi AI!_

Ndiri AI inokubatsira kuziva kana zvaunoona pa internet zviri zvechokwadi kana kwete.
(I'm an AI that helps you check if what you see online is true or false.)

📱 *Tumira chero chimwe chezvinhu izvi:*
(Send me any of the following:)

📝 Text message / WhatsApp forward
🖼️ Screenshot or image (mupikicha)
🎤 Voice note
🔗 Link/URL

Ndichaongorora ndikuudze kana zviri zvechokwadi! ✅

_Basa rangu (What I check):_
• Nhau dzenhema (Fake news)
• Scams ne fraud (EcoCash, investment scams)
• Fake government notices
• Health misinformation
• Phishing links

Tumira message yako izvozvi! 👇

🇿🇼 _Chokwadi AI - Chokwadi Chisingaputse ukama_
"""

GREETING_WORDS = {
    "hi", "hello", "help", "start", "menu",
    "mauya", "salibonani", "ndeipi", "hey", "heyy", "howzit",
    "maswera sei", "makadii", "kunjani", "yo","hoyo"
}


# ─── Admin Commands ───────────────────────────────────────────────────────

def _handle_admin_command(command: str) -> str | None:
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

def detect_message_type(message: dict) -> str:
    """Detect WhatsApp message type from the webhook payload."""
    msg_type = message.get("type", "text")
    if msg_type == "audio":
        return "voice"
    elif msg_type == "image":
        return "image"
    elif msg_type == "document":
        return "document"
    elif msg_type == "text":
        body = message.get("text", {}).get("body", "")
        if re.search(r'https?://[^\s<>"{}|\\^`\[\]]+', body):
            return "link"
        return "text"
    return "text"


def extract_urls(text: str) -> list:
    return re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)


# ─── Webhook ───────────────────────────────────────────────────────────────

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta webhook verification (GET request)."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        print(f"[WEBHOOK] Verification successful")
        return challenge, 200
    else:
        print(f"[WEBHOOK] Verification failed - token mismatch")
        return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    """Meta WhatsApp webhook — receives messages, processes, and responds."""
    body = request.get_json()

    if not body:
        return jsonify({"status": "no body"}), 400

    # Meta sends various webhook events; we only care about messages
    try:
        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    _process_message(message)

    except Exception as e:
        print(f"[ERROR] Webhook processing: {e}")
        import traceback
        traceback.print_exc()

    # Always return 200 to Meta (otherwise they retry and you get duplicates)
    return jsonify({"status": "ok"}), 200


def _process_message(message: dict):
    """Process a single incoming WhatsApp message."""
    sender = message.get("from", "")  # Phone number like "263771841532"
    message_id = message.get("id", "")
    msg_type = message.get("type", "text")

    # Get text body (if text message)
    text_body = ""
    if msg_type == "text":
        text_body = message.get("text", {}).get("body", "").strip()

    print(f"\n{'='*60}")
    print(f"[IN] From: {sender}")
    print(f"[IN] Type: {msg_type}")
    print(f"[IN] Body: {text_body[:120]}")
    print(f"[IN] Provider: {_current_provider()}")
    print(f"{'='*60}")

    # Mark as read (blue ticks)
    mark_as_read(message_id)

    # --- Admin commands ---
    if sender == ADMIN_PHONE and text_body.startswith("!"):
        admin_resp = _handle_admin_command(text_body)
        if admin_resp:
            send_whatsapp_message(sender, admin_resp)
            return

    # --- Greetings ---
    if msg_type == "text" and text_body.lower() in GREETING_WORDS:
        send_whatsapp_message(sender, WELCOME_MESSAGE)
        return

    # --- Process by content type ---
    content_type = detect_message_type(message)

    try:
        if content_type == "voice":
            media_id = message.get("audio", {}).get("id", "")
            response_text = _handle_voice(media_id, sender)

        elif content_type == "image":
            media_id = message.get("image", {}).get("id", "")
            response_text = _handle_image(media_id, sender)

        elif content_type == "link":
            response_text = _handle_link(text_body, sender)

        else:
            response_text = _handle_text(text_body, sender)

        send_whatsapp_message(sender, response_text)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        send_whatsapp_message(
            sender,
            "⚠️ Pane dambudziko rekutarisa content iyi. "
            "(There was an error processing your request. Please try again.)\n\n"
            "🇿🇼 _Chokwadi AI_"
        )


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


def _handle_voice(media_id: str, sender: str) -> str:
    print(f"[PROCESS] Voice note for {sender}")

    if not media_id:
        return (
            "⚠️ Handina kukwanisa kunzwa voice note yacho. "
            "(I couldn't process this voice note. Please try again.)"
        )

    result = transcribe_voice_note(media_id)

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


def _handle_image(media_id: str, sender: str) -> str:
    print(f"[PROCESS] Image analysis for {sender}")

    if not media_id:
        return (
            "⚠️ Handina kukwanisa kuona mufananidzo wacho. "
            "(I couldn't access the image. Please try again.)"
        )

    # Get the media URL from Meta, then pass to vision analyzer
    try:
        media_url_endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}"
        headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
        resp = httpx.get(media_url_endpoint, headers=headers, timeout=30)
        resp.raise_for_status()
        media_url = resp.json().get("url")

        if media_url:
            # Pass the download URL and auth header for the vision module
            return analyze_image_with_vision(media_url, meta_token=WHATSAPP_ACCESS_TOKEN)
    except Exception as e:
        print(f"[ERROR] Image download: {e}")

    return (
        "⚠️ Handina kukwanisa kuona mufananidzo wacho. "
        "(I couldn't access the image. Please try again.)"
    )


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
    print("    Powered by Meta WhatsApp Cloud API")
    print("=" * 60)
    print(f"  Provider : {_current_provider()}")
    print(f"  Available: {', '.join(get_available_providers())}")
    print(f"  Phone ID : {WHATSAPP_PHONE_NUMBER_ID}")
    print(f"  Port     : {FLASK_PORT}")
    print("=" * 60)

    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)
