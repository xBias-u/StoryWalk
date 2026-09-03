import math
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from guides.models import WalkRoute
from guides.services.valhalla import ValhallaClient, ValhallaError


class Command(BaseCommand):
    help = 'Calculate and store a real pedestrian path for an editorial route.'

    def add_arguments(self, parser):
        parser.add_argument('slug', help='WalkRoute slug')
        parser.add_argument('--api-url', help='Override the configured Valhalla endpoint')

    def handle(self, *args, **options):
        try:
            route = WalkRoute.objects.prefetch_related('stops__location').get(slug=options['slug'])
        except WalkRoute.DoesNotExist as exc:
            raise CommandError(f'Route not found: {options["slug"]}') from exc

        stops = list(route.stops.all())
        if len(stops) < 2:
            raise CommandError('The route needs at least two stops')
        missing = [stop.location.title for stop in stops if not stop.location.has_coordinates]
        if missing:
            raise CommandError('Coordinates are missing: ' + ', '.join(missing))

        locations = [
            {
                'latitude': stop.location.latitude,
                'longitude': stop.location.longitude,
            }
            for stop in stops
        ]
        try:
            pedestrian_route = ValhallaClient(api_url=options.get('api_url')).route(locations)
        except ValhallaError as exc:
            raise CommandError(str(exc)) from exc

        with transaction.atomic():
            first_stop = stops[0]
            first_stop.walk_distance_m = 0
            first_stop.walk_minutes = 0
            first_stop.save(update_fields=['walk_distance_m', 'walk_minutes'])

            for stop, leg in zip(stops[1:], pedestrian_route.legs):
                stop.walk_distance_m = leg.distance_m
                stop.walk_minutes = max(1, math.ceil(leg.duration_seconds / 60))
                stop.save(update_fields=['walk_distance_m', 'walk_minutes'])

            route.distance_km = (
                Decimal(pedestrian_route.distance_m) / Decimal(1000)
            ).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            route.routing_status = 'verified'
            route.routing_provider = 'valhalla'
            route.routing_updated_at = timezone.now()
            route.route_geometry = pedestrian_route.geojson
            route.save(update_fields=[
                'distance_km',
                'routing_status',
                'routing_provider',
                'routing_updated_at',
                'route_geometry',
            ])

        self.stdout.write(self.style.SUCCESS(
            f'Pedestrian route verified: {route.distance_km} km, '
            f'{math.ceil(pedestrian_route.duration_seconds / 60)} min between stops'
        ))
