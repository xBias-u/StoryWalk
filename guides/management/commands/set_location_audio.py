from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from guides.models import Location, AudioGuide


class Command(BaseCommand):
    help = 'Attach short/long audio files to a location by title.'

    def add_arguments(self, parser):
        parser.add_argument('--title', required=True, help='Location title, e.g. "Кремль"')
        parser.add_argument('--short', dest='short_path', help='Path to short mp3')
        parser.add_argument('--long', dest='long_path', help='Path to long mp3')
        parser.add_argument('--voice', default='AI voice', help='Voice name')

    def handle(self, *args, **options):
        title = options['title']
        short_path = options.get('short_path')
        long_path = options.get('long_path')
        voice = options.get('voice')

        if not short_path and not long_path:
            raise CommandError('Provide at least one of --short or --long')

        try:
            location = Location.objects.get(title=title)
        except Location.DoesNotExist:
            raise CommandError(f'Location not found: {title}')

        guide, _ = AudioGuide.objects.get_or_create(
            location=location,
            defaults={
                'language': 'ru',
                'voice_name': voice,
                'duration_seconds': 0,
                'acquisition_channel': 'site',
                'audio_file': 'audio_guides/placeholder.mp3',
            },
        )

        if short_path:
            p = Path(short_path)
            if not p.exists():
                raise CommandError(f'File not found: {p}')
            with p.open('rb') as f:
                guide.audio_short_file.save(p.name, File(f), save=False)
            # fallback compatibility
            with p.open('rb') as f:
                guide.audio_file.save(p.name, File(f), save=False)

        if long_path:
            p = Path(long_path)
            if not p.exists():
                raise CommandError(f'File not found: {p}')
            with p.open('rb') as f:
                guide.audio_long_file.save(p.name, File(f), save=False)

        guide.voice_name = voice
        guide.save()
        self.stdout.write(self.style.SUCCESS(f'Audio updated for: {location.title}'))
