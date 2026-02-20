"""
Chokwadi AI - Voice Note Transcriber
Converts WhatsApp voice notes to text using OpenAI Whisper API
"""
import os
import tempfile
import httpx
import openai
from config import OPENAI_API_KEY


def transcribe_voice_note(media_url: str, twilio_auth: tuple) -> dict:
    """
    Download and transcribe a WhatsApp voice note.
    
    Args:
        media_url: Twilio media URL for the voice note
        twilio_auth: Tuple of (account_sid, auth_token) for Twilio authentication
    
    Returns:
        dict with keys: 'text' (transcription), 'language' (detected language)
    """
    try:
        # Download the audio file from Twilio (requires auth)
        response = httpx.get(media_url, auth=twilio_auth, follow_redirects=True)
        response.raise_for_status()
        
        # Save to temp file (Whisper needs a file)
        suffix = ".ogg"  # WhatsApp voice notes are typically OGG/Opus
        content_type = response.headers.get("content-type", "")
        if "mp4" in content_type or "m4a" in content_type:
            suffix = ".m4a"
        elif "mpeg" in content_type or "mp3" in content_type:
            suffix = ".mp3"
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        # Transcribe with Whisper
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return {
            "text": transcription.text,
            "language": getattr(transcription, 'language', 'unknown')
        }
    
    except Exception as e:
        print(f"[ERROR] Transcription failed: {e}")
        # Clean up temp file if it exists
        try:
            os.unlink(tmp_path)
        except:
            pass
        return {
            "text": None,
            "language": None,
            "error": str(e)
        }
