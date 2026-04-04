from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from guides.models import Location, AudioGuide, FavoriteLocation, AudioListenEvent, LocationImage


class Command(BaseCommand):
    help = 'Rename location with merge if target title already exists (preserves media/audio/events).'

    def add_arguments(self, parser):
        parser.add_argument('--from-title', required=True)
        parser.add_argument('--to-title', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        src_title = options['from_title']
        dst_title = options['to_title']

        if src_title == dst_title:
            raise CommandError('from-title and to-title must be different')

        try:
            src = Location.objects.get(title=src_title)
        except Location.DoesNotExist:
            raise CommandError(f'Source not found: {src_title}')

        dst = Location.objects.filter(title=dst_title).first()

        if dst is None:
            src.title = dst_title
            src.save(update_fields=['title'])
            self.stdout.write(self.style.SUCCESS(f'Renamed: {src_title} -> {dst_title}'))
            return

        # merge related objects into destination
        AudioListenEvent.objects.filter(location=src).update(location=dst)
        FavoriteLocation.objects.filter(location=src).update(location=dst)
        LocationImage.objects.filter(location=src).update(location=dst)

        src_audio = AudioGuide.objects.filter(location=src).first()
        dst_audio = AudioGuide.objects.filter(location=dst).first()

        if src_audio and not dst_audio:
            src_audio.location = dst
            src_audio.save(update_fields=['location'])
        elif src_audio and dst_audio:
            # prefer destination record, fill missing fields from source
            changed = False
            for field in ['audio_file', 'audio_short_file', 'audio_long_file', 'voice_name', 'language', 'duration_seconds']:
                if not getattr(dst_audio, field) and getattr(src_audio, field):
                    setattr(dst_audio, field, getattr(src_audio, field))
                    changed = True
            if changed:
                dst_audio.save()
            src_audio.delete()

        src.delete()
        self.stdout.write(self.style.SUCCESS(f'Merged and renamed: {src_title} -> {dst_title}'))
