import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from guides.models import AudioGuide, Location
from guides.services.elevenlabs import ElevenLabsClient, ElevenLabsError


class _AudioResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.content


@override_settings(
    ELEVENLABS_API_KEY="test-key",
    ELEVENLABS_VOICE_ID="voice-id",
    ELEVENLABS_MODEL_ID="eleven_multilingual_v2",
)
class ElevenLabsClientTests(SimpleTestCase):
    @patch("guides.services.elevenlabs.urlopen")
    def test_synthesize_requests_russian_mp3(self, mocked_urlopen):
        mocked_urlopen.return_value = _AudioResponse(b"mp3-bytes")

        audio = ElevenLabsClient().synthesize("Посмотрите на фасад.")

        self.assertEqual(audio, b"mp3-bytes")
        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["language_code"], "ru")
        self.assertEqual(payload["model_id"], "eleven_multilingual_v2")
        self.assertEqual(payload["voice_settings"]["speed"], 0.96)
        self.assertIn("output_format=mp3_44100_128", request.full_url)

    @override_settings(ELEVENLABS_API_KEY="")
    def test_synthesize_requires_api_key(self):
        with self.assertRaisesMessage(ElevenLabsError, "ELEVENLABS_API_KEY"):
            ElevenLabsClient().synthesize("Текст")


@override_settings(
    ELEVENLABS_API_KEY="test-key",
    ELEVENLABS_VOICE_ID="voice-id",
    ELEVENLABS_VOICE_NAME="StoryWalk narrator",
)
class GenerateLocationAudioTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            title="Палаты XVII века",
            city="Москва",
            short_description="Историческое место.",
            full_description="Полная история места.",
        )

    @patch(
        "guides.management.commands.generate_location_audio.ElevenLabsClient.synthesize",
        return_value=b"generated-mp3",
    )
    def test_command_generates_and_attaches_short_audio(self, mocked_synthesize):
        with TemporaryDirectory() as temp_dir, override_settings(MEDIA_ROOT=temp_dir):
            narration_path = Path(temp_dir) / "narration.txt"
            narration_path.write_text("Посмотрите на старые палаты.", encoding="utf-8")

            call_command(
                "generate_location_audio",
                title=self.location.title,
                length="short",
                text_file=str(narration_path),
            )

            guide = AudioGuide.objects.get(location=self.location)
            self.assertTrue(guide.audio_short_file.name.endswith(".mp3"))
            self.assertTrue(guide.audio_file.name.endswith(".mp3"))
            self.assertEqual(guide.short_script, "Посмотрите на старые палаты.")
            self.assertEqual(guide.voice_name, "StoryWalk narrator")
            self.location.refresh_from_db()
            self.assertEqual(self.location.content_status, "voiced")
            with guide.audio_short_file.open("rb") as audio_file:
                self.assertEqual(audio_file.read(), b"generated-mp3")
            mocked_synthesize.assert_called_once_with(
                "Посмотрите на старые палаты.",
                language_code="ru",
            )

    @patch(
        "guides.management.commands.generate_location_audio.ElevenLabsClient.synthesize",
        return_value=b"generated-mp3",
    )
    def test_command_uses_saved_script_when_file_is_omitted(self, mocked_synthesize):
        AudioGuide.objects.create(
            location=self.location,
            short_script="Сохранённый текст истории.",
        )

        with TemporaryDirectory() as temp_dir, override_settings(MEDIA_ROOT=temp_dir):
            call_command(
                "generate_location_audio",
                title=self.location.title,
                length="short",
            )

        mocked_synthesize.assert_called_once_with(
            "Сохранённый текст истории.",
            language_code="ru",
        )

    @patch(
        "guides.management.commands.generate_location_audio.AppleSpeechClient.synthesize",
        return_value=b"local-mp3",
    )
    def test_command_supports_local_mvp_voice(self, mocked_synthesize):
        AudioGuide.objects.create(
            location=self.location,
            short_script="Локальная история.",
        )

        with TemporaryDirectory() as temp_dir, override_settings(MEDIA_ROOT=temp_dir):
            call_command(
                "generate_location_audio",
                title=self.location.title,
                length="short",
                provider="apple",
                voice_name="Milena — local MVP",
            )

            guide = AudioGuide.objects.get(location=self.location)
            self.assertEqual(guide.voice_name, "Milena — local MVP")
            self.assertEqual(guide.audio_file.name, guide.audio_short_file.name)

        mocked_synthesize.assert_called_once_with(
            "Локальная история.",
            language_code="ru",
        )
