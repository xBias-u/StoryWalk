import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from guides.models import AudioGuide, Location
from guides.services.apple_speech import AppleSpeechClient, AppleSpeechError
from guides.services.elevenlabs import ElevenLabsClient, ElevenLabsError


class Command(BaseCommand):
    help = "Generate a short or long location narration with ElevenLabs."

    def add_arguments(self, parser):
        parser.add_argument("--title", required=True, help="Exact location title")
        parser.add_argument(
            "--length",
            required=True,
            choices=("short", "long"),
            help="Audio version to generate",
        )
        parser.add_argument(
            "--text-file",
            help="UTF-8 file containing the final spoken narration; defaults to the saved script",
        )
        parser.add_argument(
            "--provider",
            choices=("elevenlabs", "apple"),
            default="elevenlabs",
            help="Speech provider; apple is a local macOS-only MVP fallback",
        )
        parser.add_argument(
            "--voice-id",
            help="Override ELEVENLABS_VOICE_ID for this generation",
        )
        parser.add_argument(
            "--voice-name",
            default=None,
            help="Human-readable voice label stored in AudioGuide",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace an existing version",
        )

    def handle(self, *args, **options):
        try:
            location = Location.objects.get(title=options["title"])
        except Location.DoesNotExist as exc:
            raise CommandError(f"Location not found: {options['title']}") from exc

        guide, _ = AudioGuide.objects.get_or_create(
            location=location,
            defaults={
                "language": "ru",
                "voice_name": "",
                "duration_seconds": 0,
                "acquisition_channel": "site",
                "audio_file": "",
            },
        )
        length = options["length"]
        if options.get("text_file"):
            text_path = Path(options["text_file"]).expanduser()
            if not text_path.is_file():
                raise CommandError(f"Narration file not found: {text_path}")
            try:
                narration = text_path.read_text(encoding="utf-8").strip()
            except UnicodeDecodeError as exc:
                raise CommandError("Narration file must use UTF-8 encoding") from exc
        else:
            narration = getattr(guide, f"{length}_script").strip()
        if not narration:
            raise CommandError(
                f"The saved {length} script is empty; provide --text-file"
            )

        field_name = f"audio_{length}_file"
        field = getattr(guide, field_name)
        if field and not options["force"]:
            raise CommandError(
                f"{length.capitalize()} audio already exists; use --force to replace it"
            )

        if options["provider"] == "apple":
            resolved_voice_name = options.get("voice_name") or "Milena — local MVP"
            client = AppleSpeechClient(voice=resolved_voice_name.split(' — ')[0])
            error_class = AppleSpeechError
        else:
            resolved_voice_name = options.get("voice_name") or getattr(
                settings,
                "ELEVENLABS_VOICE_NAME",
                "StoryWalk",
            )
            client = ElevenLabsClient(voice_id=options.get("voice_id"))
            error_class = ElevenLabsError
        try:
            audio = client.synthesize(narration, language_code="ru")
        except error_class as exc:
            raise CommandError(str(exc)) from exc

        digest = hashlib.sha256(narration.encode("utf-8")).hexdigest()[:10]
        location_slug = slugify(location.title, allow_unicode=True) or f"location-{location.pk}"
        filename = f"{location_slug}-{length}-{digest}.mp3"
        getattr(guide, field_name).save(filename, ContentFile(audio), save=False)
        setattr(guide, f"{length}_script", narration)

        if (
            length == "short"
            or not guide.audio_file
            or guide.audio_file.name == "audio_guides/placeholder.mp3"
        ):
            guide.audio_file.name = getattr(guide, field_name).name

        guide.voice_name = resolved_voice_name
        guide.language = "ru"
        guide.save()
        if location.content_status != "published":
            location.content_status = "voiced"
            location.save(update_fields=["content_status"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {length} audio for {location.title}: "
                f"{getattr(guide, field_name).name}"
            )
        )
