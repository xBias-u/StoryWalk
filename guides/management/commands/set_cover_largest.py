from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from guides.models import Location


class Command(BaseCommand):
    help = 'Set location cover image from the largest file in directory matching prefixes.'

    def add_arguments(self, parser):
        parser.add_argument('--title', required=True, help='Location title')
        parser.add_argument('--dir', required=True, help='Directory with images')
        parser.add_argument('--prefix', action='append', default=[], help='Filename prefix (can repeat)')

    def handle(self, *args, **opts):
        title = opts['title']
        folder = Path(opts['dir'])
        prefixes = [p.lower() for p in opts['prefix']] or ['isaak', 'isaakiev', 'isaakievskiy_sobor']

        if not folder.exists() or not folder.is_dir():
            raise CommandError(f'Directory not found: {folder}')

        try:
            loc = Location.objects.get(title=title)
        except Location.DoesNotExist:
            raise CommandError(f'Location not found: {title}')

        candidates = []
        for f in folder.iterdir():
            if not f.is_file():
                continue
            if f.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
                continue
            low = f.name.lower()
            if any(low.startswith(p) for p in prefixes):
                candidates.append(f)

        if not candidates:
            raise CommandError('No matching image files found')

        best = max(candidates, key=lambda p: p.stat().st_size)
        with best.open('rb') as fh:
            loc.image.save(best.name, File(fh), save=False)
        loc.save(update_fields=['image'])

        self.stdout.write(self.style.SUCCESS(f'Set cover for {title}: {best.name} ({best.stat().st_size} bytes)'))
