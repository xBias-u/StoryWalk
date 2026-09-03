import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class ElevenLabsError(RuntimeError):
    """A safe, user-facing error raised when speech generation fails."""


class ElevenLabsClient:
    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    MAX_MULTILINGUAL_V2_CHARACTERS = 10_000

    def __init__(self, api_key=None, voice_id=None, model_id=None, timeout=90):
        self.api_key = api_key or getattr(settings, "ELEVENLABS_API_KEY", "")
        self.voice_id = voice_id or getattr(settings, "ELEVENLABS_VOICE_ID", "")
        self.model_id = model_id or getattr(
            settings,
            "ELEVENLABS_MODEL_ID",
            "eleven_multilingual_v2",
        )
        self.timeout = timeout

    def synthesize(self, text, language_code="ru"):
        text = text.strip()
        if not self.api_key:
            raise ElevenLabsError("ELEVENLABS_API_KEY is not configured")
        if not self.voice_id:
            raise ElevenLabsError("ELEVENLABS_VOICE_ID is not configured")
        if not text:
            raise ElevenLabsError("The narration text is empty")
        if len(text) > self.MAX_MULTILINGUAL_V2_CHARACTERS:
            raise ElevenLabsError(
                "The narration is longer than 10,000 characters; split it into chapters"
            )

        query = urlencode({"output_format": "mp3_44100_128"})
        url = f"{self.API_URL.format(voice_id=self.voice_id)}?{query}"
        payload = {
            "text": text,
            "model_id": self.model_id,
            "language_code": language_code,
            "voice_settings": {
                "stability": 0.55,
                "similarity_boost": 0.75,
                "style": 0.05,
                "use_speaker_boost": True,
                "speed": 0.96,
            },
        }
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                audio = response.read()
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")[:500]
            raise ElevenLabsError(
                f"ElevenLabs returned HTTP {exc.code}: {details}"
            ) from exc
        except URLError as exc:
            raise ElevenLabsError(f"Could not reach ElevenLabs: {exc.reason}") from exc

        if not audio:
            raise ElevenLabsError("ElevenLabs returned an empty audio file")
        return audio
