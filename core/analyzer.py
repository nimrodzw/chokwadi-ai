"""
Chokwadi AI - Core Analyzer
Sends content to AI for credibility analysis.
Supports Anthropic (Claude) and OpenAI (GPT) with automatic fallback.
"""
import base64
import anthropic
import openai
import httpx

from config import (
    ANTHROPIC_API_KEY, OPENAI_API_KEY,
    CLAUDE_MODEL, OPENAI_CHAT_MODEL,
    get_active_provider, get_fallback_provider
)
from prompts.system_prompt import (
    CHOKWADI_SYSTEM_PROMPT, LINK_ANALYSIS_PROMPT,
    VOICE_NOTE_CONTEXT, IMAGE_CONTEXT
)


# ─── Text / Transcription / Link Analysis ─────────────────────────────────

def analyze_text(content: str, content_type: str = "text") -> str:
    """
    Analyse content for misinformation using the configured AI provider.
    """
    if content_type == "voice":
        user_message = VOICE_NOTE_CONTEXT + content
    elif content_type == "image":
        user_message = IMAGE_CONTEXT + content
    elif content_type == "link":
        user_message = f"Please analyse this URL/link for safety and credibility:\n\n{content}"
    else:
        user_message = f"Please analyse the following content for credibility and misinformation:\n\n{content}"

    system = CHOKWADI_SYSTEM_PROMPT
    if content_type == "link":
        system += "\n\n" + LINK_ANALYSIS_PROMPT

    primary = get_active_provider()
    fallback = get_fallback_provider()

    result = _call_provider(primary, system, user_message)
    if result is not None:
        return result

    if fallback:
        print(f"[FALLBACK] {primary} failed, trying {fallback}...")
        result = _call_provider(fallback, system, user_message)
        if result is not None:
            return result

    return _error_response()


def _call_provider(provider: str, system: str, user_message: str) -> str | None:
    try:
        if provider == "anthropic":
            return _call_claude(system, user_message)
        else:
            return _call_openai(system, user_message)
    except Exception as e:
        print(f"[ERROR] {provider} API error: {e}")
        return None


def _call_claude(system: str, user_message: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def _call_openai(system: str, user_message: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content


# ─── Image / Vision Analysis ──────────────────────────────────────────────

def analyze_image_with_vision(image_url: str, meta_token: str = None) -> str:
    """
    Analyse an image directly using vision capabilities.

    Args:
        image_url:   URL of the image to analyse
        meta_token:  Meta WhatsApp access token for downloading media
    """
    primary = get_active_provider()
    fallback = get_fallback_provider()

    result = _call_vision_provider(primary, image_url, meta_token)
    if result is not None:
        return result

    if fallback:
        print(f"[FALLBACK] {primary} vision failed, trying {fallback}...")
        result = _call_vision_provider(fallback, image_url, meta_token)
        if result is not None:
            return result

    return _error_response()


def _call_vision_provider(provider: str, image_url: str, meta_token: str = None) -> str | None:
    try:
        if provider == "anthropic":
            return _vision_claude(image_url, meta_token)
        else:
            return _vision_openai(image_url, meta_token)
    except Exception as e:
        print(f"[ERROR] {provider} vision error: {e}")
        return None


def _download_image(image_url: str, meta_token: str = None) -> tuple[bytes, str]:
    """Download image bytes from Meta CDN or any URL."""
    headers = {}
    if meta_token:
        headers["Authorization"] = f"Bearer {meta_token}"

    resp = httpx.get(image_url, headers=headers, follow_redirects=True, timeout=30)
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "image/jpeg")
    if "png" in content_type:
        media_type = "image/png"
    elif "webp" in content_type:
        media_type = "image/webp"
    elif "gif" in content_type:
        media_type = "image/gif"
    else:
        media_type = "image/jpeg"

    return resp.content, media_type


def _vision_claude(image_url: str, meta_token: str = None) -> str:
    image_data, media_type = _download_image(image_url, meta_token)
    image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=CHOKWADI_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Please analyse this image for misinformation, scams, or manipulated content. "
                            "Extract any visible text and assess the credibility of the claims made."
                        ),
                    },
                ],
            }
        ],
    )
    return response.content[0].text


def _vision_openai(image_url: str, meta_token: str = None) -> str:
    image_data, media_type = _download_image(image_url, meta_token)
    image_b64 = base64.standard_b64encode(image_data).decode("utf-8")
    data_uri = f"data:{media_type};base64,{image_b64}"

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": CHOKWADI_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Please analyse this image for misinformation, scams, or manipulated content. "
                            "Extract any visible text and assess the credibility of the claims made."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    },
                ],
            },
        ],
    )
    return response.choices[0].message.content


# ─── Error Response ────────────────────────────────────────────────────────

def _error_response() -> str:
    return (
        "🔍 *CHOKWADI AI*\n\n"
        "⚠️ Pane dambudziko rekutarisa content iyi panguva ino. "
        "(We're experiencing a temporary issue analysing this content.)\n\n"
        "Edza zvakare mushure menguva shoma. (Please try again shortly.)\n\n"
        "🇿🇼 _Chokwadi AI - Zvokwadi Zvinobatsira_"
    )
