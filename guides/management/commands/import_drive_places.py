import json
from pathlib import Path

from django.core.management.base import BaseCommand

from guides.models import Location


class Command(BaseCommand):
    help = 'Import/update locations from JSON generated from Drive folder names.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='guides/data/drive_places_v1.json',
            help='Path to JSON file with places.',
        )

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {path}'))
            return

        data = json.loads(path.read_text(encoding='utf-8'))
        created = 0
        updated = 0

        for row in data:
            defaults = {
                'city': row.get('city', ''),
                'short_description': row.get('short_description', '')[:255],
                'full_description': row.get('full_description', ''),
                'access_level': row.get('access_level', 'free'),
                'segment': row.get('segment', 'solo'),
                'is_featured': bool(row.get('is_featured', True)),
            }

            matches = Location.objects.filter(title=row['title']).order_by('id')
            if matches.exists():
                obj = matches.first()
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save(update_fields=list(defaults.keys()))
                # soft-dedupe for accidental duplicate titles
                if matches.count() > 1:
                    for dup in matches[1:]:
                        dup.delete()
                is_created = False
            else:
                obj = Location.objects.create(title=row['title'], **defaults)
                is_created = True

            created += int(is_created)
            updated += int(not is_created)
            self.stdout.write(f"{'CREATED' if is_created else 'UPDATED'}: {obj.title}")

        self.stdout.write(self.style.SUCCESS(f'Done. created={created}, updated={updated}'))
