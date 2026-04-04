import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from guides.models import Location


DEFAULT_MAP = {
    'isaakievskiy_sobor': 'Исаакиевский собор',
    'istoricheskiy_muzey': 'Исторический музей',
    'kreml': 'Кремль',
    'kungur': 'Кунгур',
    'ermitazh': 'Эритаж',
}


def normalize(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^a-z0-9_а-яё-]', '', name)
    return name


class Command(BaseCommand):
    help = 'Bulk import location images from directory by predefined aliases.'

    def add_arguments(self, parser):
        parser.add_argument('--dir', required=True, help='Directory with images')

    def handle(self, *args, **options):
        images_dir = Path(options['dir'])
        if not images_dir.exists() or not images_dir.is_dir():
            raise CommandError(f'Directory not found: {images_dir}')

        exts = {'.jpg', '.jpeg', '.png', '.webp'}
        files = [p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in exts]
        if not files:
            raise CommandError(f'No images found in: {images_dir}')

        updated = 0
        skipped = 0

        for f in files:
            key = normalize(f.stem)
            title = DEFAULT_MAP.get(key)
            if not title:
                self.stdout.write(f'SKIP (unknown alias): {f.name}')
                skipped += 1
                continue

            try:
                loc = Location.objects.get(title=title)
            except Location.DoesNotExist:
                self.stdout.write(f'SKIP (location not found): {title} <- {f.name}')
                skipped += 1
                continue

            with f.open('rb') as img:
                loc.image.save(f.name, File(img), save=False)
            loc.save(update_fields=['image'])
            self.stdout.write(f'UPDATED image: {loc.title} <- {f.name}')
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'Done. updated={updated}, skipped={skipped}'))
