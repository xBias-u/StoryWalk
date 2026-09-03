from django.core.management.base import BaseCommand, CommandError

from guides.models import Location, PlaceCandidate
from guides.services.overpass import OverpassClient, OverpassError


class Command(BaseCommand):
    help = 'Find nearby cultural POIs and optionally save them as editorial candidates.'

    def add_arguments(self, parser):
        parser.add_argument('--from-location', help='Use coordinates of an existing location')
        parser.add_argument('--lat', type=float, help='Starting latitude')
        parser.add_argument('--lon', type=float, help='Starting longitude')
        parser.add_argument('--city', default='', help='City stored with candidates')
        parser.add_argument('--radius', type=int, default=1200, help='Search radius in metres (100–5000)')
        parser.add_argument('--limit', type=int, default=20, help='Maximum candidates (1–50)')
        parser.add_argument('--save', action='store_true', help='Save results to the editorial inbox')

    def handle(self, *args, **options):
        latitude, longitude, city = self._resolve_origin(options)
        try:
            places = OverpassClient().discover(
                latitude,
                longitude,
                radius_m=options['radius'],
                limit=options['limit'],
            )
        except OverpassError as exc:
            raise CommandError(str(exc)) from exc

        existing_titles = {
            title.casefold().replace('ё', 'е')
            for title in Location.objects.values_list('title', flat=True)
        }
        places = [
            place
            for place in places
            if place.name.casefold().replace('ё', 'е') not in existing_titles
        ]

        if not places:
            self.stdout.write(self.style.WARNING('No candidates found'))
            return

        for index, place in enumerate(places, start=1):
            self.stdout.write(
                f'{index:02d}. score={place.story_score:02d} · {place.distance_m:4d} m · '
                f'{place.category:12s} · {place.name}'
            )

        if not options['save']:
            self.stdout.write(self.style.WARNING('Preview only. Add --save to store these candidates.'))
            return

        created = 0
        updated = 0
        for place in places:
            _, is_created = PlaceCandidate.objects.update_or_create(
                source_provider='openstreetmap',
                source_id=place.source_id,
                defaults={
                    'name': place.name,
                    'city': city,
                    'latitude': place.latitude,
                    'longitude': place.longitude,
                    'category': place.category,
                    'distance_m': place.distance_m,
                    'story_score': place.story_score,
                    'source_url': place.source_url,
                    'source_tags': place.tags,
                },
            )
            created += int(is_created)
            updated += int(not is_created)

        self.stdout.write(self.style.SUCCESS(f'Candidates saved: created={created}, updated={updated}'))

    @staticmethod
    def _resolve_origin(options):
        if options.get('from_location'):
            try:
                location = Location.objects.get(title=options['from_location'])
            except Location.DoesNotExist as exc:
                raise CommandError(f"Location not found: {options['from_location']}") from exc
            if not location.has_coordinates:
                raise CommandError(f'Location has no coordinates: {location.title}')
            return float(location.latitude), float(location.longitude), options['city'] or location.city

        if options.get('lat') is None or options.get('lon') is None:
            raise CommandError('Provide --from-location or both --lat and --lon')
        return options['lat'], options['lon'], options['city']
