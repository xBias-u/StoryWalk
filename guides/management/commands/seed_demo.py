from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from guides.models import AudioGuide, Location, LocationImage, PlaceCandidate, WalkRoute


PUBLIC_LOCATION_TITLES = (
    'Воскресенские ворота',
    'Исторический музей',
    'Красная площадь',
    'Мавзолей В. И. Ленина',
    'Собор Василия Блаженного',
)

DEMO_CANDIDATES = (
    {
        'name': 'Воскресенские ворота',
        'latitude': '55.755660',
        'longitude': '37.618048',
        'category': 'historic',
        'distance_m': 39,
        'story_score': 11,
        'source_id': 'relation/1932724',
    },
    {
        'name': 'Мавзолей В. И. Ленина',
        'latitude': '55.753721',
        'longitude': '37.619902',
        'category': 'historic',
        'distance_m': 218,
        'story_score': 11,
        'source_id': 'relation/3272726',
    },
    {
        'name': 'Собор Василия Блаженного',
        'latitude': '55.752469',
        'longitude': '37.623097',
        'category': 'religious',
        'distance_m': 455,
        'story_score': 12,
        'source_id': 'relation/3030568',
    },
)

PUBLIC_AUDIO = {
    'Воскресенские ворота': ('audio_guides/red_square_gate_short.mp3', 47),
    'Исторический музей': ('audio_guides/historical_museum_route_short.mp3', 55),
    'Красная площадь': ('audio_guides/red_square_short.mp3', 53),
    'Мавзолей В. И. Ленина': ('audio_guides/lenin_mausoleum_short.mp3', 50),
    'Собор Василия Блаженного': ('audio_guides/saint_basils_short.mp3', 50),
}

# These assets are useful in the editorial inbox but are intentionally not
# published by the deterministic demo seed.
EDITORIAL_ASSETS = {
    'Исаакиевский собор': {
        'cover': 'location_images/isaakievskiy_sobor_cover.jpg',
        'gallery': [f'location_images/isaakievskiy_sobor{i}.jpg' for i in range(1, 6)],
        'short': 'audio_guides/isaakievskiy_short.mp3',
        'long': 'audio_guides/isaakievskiy_long.mp3',
        'script': 'source_text_isaakievsky.txt',
    },
    'Корпус ВШЭ на Мясницкой': {
        'cover': 'location_images/hse_myasnitskaya_cover.jpg',
        'gallery': [f'location_images/hse_myasnitskaya{i}.jpg' for i in range(1, 5)],
        'short': 'audio_guides/hse_myasnitskaya_short.mp3',
        'script': 'source_text_hse_myasnitskaya.txt',
    },
    'Кунгур': {
        'cover': 'location_images/kungur_cover.png',
        'gallery': [f'location_images/kungur{i}.png' for i in range(1, 4)],
        'short': 'audio_guides/kungur_short.mp3',
        'long': 'audio_guides/kungur_long.mp3',
        'script': 'source_text_kungur.txt',
    },
    'Эрмитаж': {
        'cover': 'location_images/ermitazh_cover_v2.png',
        'gallery': ['location_images/ermitazh1.png', 'location_images/ermitazh_cover.jpg'],
        'short': 'audio_guides/ermitazh_short.mp3',
        'long': 'audio_guides/ermitazh_long.mp3',
        'script': 'source_text_hermitage.txt',
    },
}

VERIFIED_LEGS = (
    (1, 0, 0),
    (2, 47, 1),
    (3, 371, 5),
    (4, 218, 3),
    (5, 309, 4),
)

VERIFIED_GEOMETRY = {
    'type': 'FeatureCollection',
    'features': [
        {
            'type': 'Feature',
            'properties': {'position': 1},
            'geometry': {'type': 'LineString', 'coordinates': [
                [37.618081, 55.755677], [37.618138, 55.755643], [37.618212, 55.755598],
                [37.618363, 55.755452], [37.618408, 55.755425], [37.618291, 55.755356],
                [37.618269, 55.755343],
            ]},
        },
        {
            'type': 'Feature',
            'properties': {'position': 2},
            'geometry': {'type': 'LineString', 'coordinates': [
                [37.618269, 55.755343], [37.618291, 55.755356], [37.618408, 55.755425],
                [37.618770, 55.755228], [37.618922, 55.755157], [37.619028, 55.755108],
                [37.618927, 55.755044], [37.618620, 55.754868], [37.618364, 55.754713],
                [37.618481, 55.754726], [37.618523, 55.754728], [37.618875, 55.754758],
                [37.618978, 55.754764], [37.619048, 55.754755], [37.619158, 55.754720],
                [37.620302, 55.754160], [37.621491, 55.753585],
            ]},
        },
        {
            'type': 'Feature',
            'properties': {'position': 3},
            'geometry': {'type': 'LineString', 'coordinates': [
                [37.621491, 55.753585], [37.621860, 55.753406], [37.621752, 55.753336],
                [37.621581, 55.753225], [37.620183, 55.753902], [37.620098, 55.753848],
                [37.620086, 55.753840], [37.620054, 55.753820], [37.620036, 55.753809],
                [37.620017, 55.753797], [37.620010, 55.753793], [37.619985, 55.753777],
                [37.620049, 55.753744], [37.620089, 55.753724], [37.620099, 55.753719],
                [37.620086, 55.753710], [37.620054, 55.753690], [37.620045, 55.753684],
                [37.620025, 55.753694], [37.620061, 55.753717], [37.619970, 55.753763],
            ]},
        },
        {
            'type': 'Feature',
            'properties': {'position': 4},
            'geometry': {'type': 'LineString', 'coordinates': [
                [37.619970, 55.753763], [37.620061, 55.753717], [37.620025, 55.753694],
                [37.620045, 55.753684], [37.620054, 55.753690], [37.620086, 55.753710],
                [37.620099, 55.753719], [37.620089, 55.753724], [37.620049, 55.753744],
                [37.619985, 55.753777], [37.620010, 55.753793], [37.620017, 55.753797],
                [37.620036, 55.753809], [37.620054, 55.753820], [37.620086, 55.753840],
                [37.620098, 55.753848], [37.620183, 55.753902], [37.621581, 55.753225],
                [37.621777, 55.753131], [37.621959, 55.753043], [37.622017, 55.752940],
                [37.622139, 55.753023], [37.622403, 55.752891], [37.622419, 55.752877],
                [37.622431, 55.752867], [37.622446, 55.752853], [37.622492, 55.752784],
                [37.622581, 55.752723], [37.622646, 55.752652], [37.622663, 55.752633],
                [37.622667, 55.752629], [37.622683, 55.752611], [37.622697, 55.752596],
                [37.622725, 55.752566], [37.622732, 55.752558], [37.622737, 55.752553],
                [37.622752, 55.752536], [37.622777, 55.752543], [37.622819, 55.752555],
                [37.622824, 55.752557], [37.622896, 55.752578], [37.622908, 55.752564],
                [37.622968, 55.752538], [37.622988, 55.752517], [37.623015, 55.752488],
                [37.623035, 55.752493], [37.623041, 55.752495], [37.623059, 55.752501],
            ]},
        },
    ],
}


class Command(BaseCommand):
    help = 'Create a deterministic, fully playable StoryWalk demo without network calls.'

    @transaction.atomic
    def handle(self, *args, **options):
        self._normalize_legacy_titles()
        Location.objects.filter(is_published=True).update(is_published=False)
        call_command('seed_content', stdout=self.stdout)
        call_command('import_drive_places', stdout=self.stdout)
        call_command('seed_routes', stdout=self.stdout)
        self._seed_candidates()
        call_command('build_red_square_route', stdout=self.stdout)
        call_command('prepare_red_square_scripts', stdout=self.stdout)

        self._attach_editorial_assets()
        self._attach_public_audio()
        self._publish_locations()
        self._publish_verified_route()

        self.stdout.write(self.style.SUCCESS(
            'Demo ready: 1 verified route, 5 published stops, bundled audio attached.'
        ))

    @staticmethod
    def _normalize_legacy_titles():
        legacy = Location.objects.filter(title='Эритаж').first()
        if not legacy:
            return
        if Location.objects.filter(title='Эрмитаж').exists():
            legacy.is_published = False
            legacy.save(update_fields=['is_published'])
            return
        legacy.title = 'Эрмитаж'
        legacy.save(update_fields=['title'])

    @staticmethod
    def _seed_candidates():
        for item in DEMO_CANDIDATES:
            source_id = item['source_id']
            PlaceCandidate.objects.update_or_create(
                source_provider='openstreetmap',
                source_id=source_id,
                defaults={
                    'name': item['name'],
                    'city': 'Москва',
                    'latitude': item['latitude'],
                    'longitude': item['longitude'],
                    'category': item['category'],
                    'distance_m': item['distance_m'],
                    'story_score': item['story_score'],
                    'source_url': f'https://www.openstreetmap.org/{source_id}',
                    'source_tags': {},
                },
            )

    def _attach_public_audio(self):
        for title, (name, duration) in PUBLIC_AUDIO.items():
            self._require_media_asset(name)
            location = Location.objects.get(title=title)
            guide, _ = AudioGuide.objects.get_or_create(location=location)
            guide.audio_short_file.name = name
            guide.audio_file.name = name
            guide.duration_seconds = duration
            guide.language = 'ru'
            guide.voice_name = 'Milena — demo voice'
            guide.save()

    def _attach_editorial_assets(self):
        data_dir = Path(__file__).resolve().parents[2] / 'data'
        for title, assets in EDITORIAL_ASSETS.items():
            try:
                location = Location.objects.get(title=title)
            except Location.DoesNotExist:
                continue

            self._require_media_asset(assets['cover'])
            location.image.name = assets['cover']
            location.is_published = False
            location.content_status = 'voiced'
            location.save(update_fields=['image', 'is_published', 'content_status'])

            for order, image_name in enumerate(assets['gallery'], start=1):
                self._require_media_asset(image_name)
                LocationImage.objects.update_or_create(
                    location=location,
                    image=image_name,
                    defaults={'sort_order': order},
                )

            script = (data_dir / assets['script']).read_text(encoding='utf-8').strip()
            guide, _ = AudioGuide.objects.get_or_create(location=location)
            if assets.get('short'):
                self._require_media_asset(assets['short'])
                guide.audio_short_file.name = assets['short']
                guide.audio_file.name = assets['short']
                guide.short_script = script
            if assets.get('long'):
                self._require_media_asset(assets['long'])
                guide.audio_long_file.name = assets['long']
                guide.long_script = script
            guide.language = 'ru'
            guide.voice_name = 'StoryWalk demo'
            guide.save()

    @staticmethod
    def _publish_locations():
        for title in PUBLIC_LOCATION_TITLES:
            location = Location.objects.get(title=title)
            issues = location.content_readiness_issues()
            if issues:
                raise CommandError(f'{title} is not publication-ready: {", ".join(issues)}')
            location.content_status = 'published'
            location.is_published = True
            location.is_featured = True
            location.editorial_notes = 'Deterministic demo release candidate.'
            location.save(update_fields=[
                'content_status', 'is_published', 'is_featured', 'editorial_notes',
            ])

    @staticmethod
    def _publish_verified_route():
        route = WalkRoute.objects.get(slug='krasnaya-ploshchad-sobrannaya-zanovo')
        stops = {stop.position: stop for stop in route.stops.select_related('location')}
        for position, distance_m, walk_minutes in VERIFIED_LEGS:
            stop = stops[position]
            stop.walk_distance_m = distance_m
            stop.walk_minutes = walk_minutes
            stop.save(update_fields=['walk_distance_m', 'walk_minutes'])

        route.distance_km = '0.9'
        route.routing_status = 'verified'
        route.routing_provider = 'valhalla-snapshot'
        route.routing_updated_at = timezone.now()
        route.route_geometry = VERIFIED_GEOMETRY
        route.is_published = True
        route.save(update_fields=[
            'distance_km', 'routing_status', 'routing_provider', 'routing_updated_at',
            'route_geometry', 'is_published',
        ])

        WalkRoute.objects.exclude(pk=route.pk).update(is_published=False)

    @staticmethod
    def _require_media_asset(name):
        path = Path(settings.MEDIA_ROOT) / name
        if not path.is_file() or path.stat().st_size < 1_000:
            raise CommandError(f'Demo media asset is missing or empty: {path}')
