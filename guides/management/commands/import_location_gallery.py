import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from guides.models import Location, LocationImage

ALIASES = {
    'kreml': 'Кремль',
    'isaakievskiy_sobor': 'Исаакиевский собор',
    'istoricheskiy_muzey': 'Исторический музей',
    'kungur': 'Кунгур',
    'ermitazh': 'Эритаж',
}


class Command(BaseCommand):
    help = 'Import gallery images by filename prefix (e.g., kreml1.png, kreml2.png).'

    def add_arguments(self, parser):
        parser.add_argument('--dir', required=True)
        parser.add_argument('--clear', action='store_true', help='Clear existing gallery images for touched locations')

    def handle(self, *args, **opts):
        d = Path(opts['dir'])
        if not d.exists() or not d.is_dir():
            raise CommandError(f'Directory not found: {d}')

        files = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}]
        if not files:
            raise CommandError('No images found')

        touched = set()
        added = 0

        for f in sorted(files):
            m = re.match(r'^([a-z_]+)(\d+)?$', f.stem.lower())
            if not m:
                self.stdout.write(f'SKIP name: {f.name}')
                continue
            prefix = m.group(1)
            title = ALIASES.get(prefix)
            if not title:
                self.stdout.write(f'SKIP unknown prefix: {f.name}')
                continue

            try:
                loc = Location.objects.get(title=title)
            except Location.DoesNotExist:
                self.stdout.write(f'SKIP location missing: {title}')
                continue

            if opts['clear'] and loc.id not in touched:
                loc.gallery_images.all().delete()

            order_match = re.search(r'(\d+)$', f.stem)
            sort_order = int(order_match.group(1)) if order_match else 0

            obj = LocationImage(location=loc, sort_order=sort_order)
            with f.open('rb') as img:
                obj.image.save(f.name, File(img), save=False)
            obj.caption = f'{loc.title} — фото {sort_order}' if sort_order else ''
            obj.save()
            touched.add(loc.id)
            added += 1
            self.stdout.write(f'ADD {loc.title}: {f.name}')

        self.stdout.write(self.style.SUCCESS(f'Done. added={added}, locations={len(touched)}'))
