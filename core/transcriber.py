"""
Chokwadi AI - Voice Note Transcriber
Converts WhatsApp voice notes to text using OpenAI Whisper API.
Downloads audio from Meta's CDN using the WhatsApp access token.
"""
import os
import tempfile
import httpx
import openai
from config import OPENAI_API_KEY, WHATSAPP_ACCESS_TOKEN


def transcribe_voice_note(media_id: str) -> dict:
    """
    Download and transcribe a WhatsApp voice note via Meta's media API.

    Args:
        media_id: The media ID from the WhatsApp webhook payload

    Returns:
        dict with keys: 'text' (transcription), 'language' (detected language)
    """
    tmp_path = None
    try:
        # Step 1: Get the media URL from Meta
        media_url_endpoint = f"https://graph.facebook.com/v22.0/{media_id}"
        headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}

        resp = httpx.get(media_url_endpoint, headers=headers, timeout=30)
        resp.raise_for_status()
        media_info = resp.json()
        download_url = media_info.get("url")

        if not download_url:
            return {"text": None, "language": None, "error": "No media URL returned"}

        # Step 2: Download the actual audio file
        audio_resp = httpx.get(download_url, headers=headers, follow_redirects=True, timeout=60)
        audio_resp.raise_for_status()

        # Determine file extension from content type
        content_type = audio_resp.headers.get("content-type", "")
        if "ogg" in content_type or "opus" in content_type:
            suffix = ".ogg"
        elif "mp4" in content_type or "m4a" in content_type:
            suffix = ".m4a"
        elif "mpeg" in content_type or "mp3" in content_type:
            suffix = ".mp3"
        elif "amr" in content_type:
            suffix = ".amr"
        else:
            suffix = ".ogg"  # WhatsApp default

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_resp.content)
            tmp_path = tmp.name

        # Step 3: Transcribe with Whisper
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )

        return {
            "text": transcription.text,
            "language": getattr(transcription, "language", "unknown"),
        }

    except Exception as e:
        print(f"[ERROR] Transcription failed: {e}")
        return {"text": None, "language": None, "error": str(e)}

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
