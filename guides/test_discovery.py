import json
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from guides.models import Location, PlaceCandidate
from guides.services.overpass import DiscoveredPlace, OverpassClient


class _JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode('utf-8')


class OverpassClientTests(SimpleTestCase):
    @patch('guides.services.overpass.urlopen')
    def test_discovery_ranks_and_deduplicates_places(self, mocked_urlopen):
        mocked_urlopen.return_value = _JsonResponse({
            'elements': [
                {
                    'type': 'way',
                    'id': 10,
                    'center': {'lat': 55.756, 'lon': 37.619},
                    'tags': {
                        'name': 'Museum',
                        'name:ru': 'Городской музей',
                        'tourism': 'museum',
                        'heritage': '2',
                        'wikipedia': 'ru:Городской музей',
                    },
                },
                {
                    'type': 'node',
                    'id': 11,
                    'lat': 55.7561,
                    'lon': 37.6191,
                    'tags': {'name': 'Городской музей', 'tourism': 'attraction'},
                },
                {
                    'type': 'node',
                    'id': 12,
                    'lat': 55.757,
                    'lon': 37.620,
                    'tags': {
                        'name': 'Памятная доска',
                        'historic': 'memorial',
                        'memorial': 'plaque',
                    },
                },
            ],
        })

        places = OverpassClient().discover(55.755, 37.618, radius_m=1200, limit=10)

        self.assertEqual([place.name for place in places], ['Городской музей', 'Памятная доска'])
        self.assertEqual(places[0].category, 'museum')
        self.assertEqual(places[0].source_id, 'way/10')
        self.assertGreater(places[0].story_score, places[1].story_score)


class CandidateWorkflowTests(TestCase):
    def setUp(self):
        self.origin = Location.objects.create(
            title='Старт маршрута',
            city='Москва',
            short_description='Старт.',
            full_description='Старт маршрута.',
            latitude='55.755000',
            longitude='37.618000',
            content_status='published',
            is_published=True,
        )

    @patch('guides.management.commands.discover_route_candidates.OverpassClient.discover')
    def test_command_saves_candidates_without_publishing_locations(self, mocked_discover):
        mocked_discover.return_value = [
            DiscoveredPlace(
                name='Старинная палата',
                latitude=55.756,
                longitude=37.619,
                category='historic',
                distance_m=140,
                story_score=12,
                source_id='way/42',
                source_url='https://www.openstreetmap.org/way/42',
                tags={'historic': 'building'},
            ),
            DiscoveredPlace(
                name=self.origin.title,
                latitude=55.755,
                longitude=37.618,
                category='historic',
                distance_m=0,
                story_score=20,
                source_id='node/1',
                source_url='https://www.openstreetmap.org/node/1',
                tags={'historic': 'building'},
            ),
        ]

        call_command(
            'discover_route_candidates',
            from_location=self.origin.title,
            limit=10,
            save=True,
        )

        candidate = PlaceCandidate.objects.get(source_id='way/42')
        self.assertEqual(candidate.status, 'new')
        self.assertIsNone(candidate.location)
        self.assertFalse(Location.objects.filter(title='Старинная палата').exists())
        self.assertFalse(PlaceCandidate.objects.filter(source_id='node/1').exists())

    def test_promotion_creates_hidden_draft_with_osm_source(self):
        candidate = PlaceCandidate.objects.create(
            name='Старинная палата',
            city='Москва',
            latitude='55.756000',
            longitude='37.619000',
            category='historic',
            distance_m=140,
            story_score=12,
            source_id='way/42',
            source_url='https://www.openstreetmap.org/way/42',
            source_tags={'historic': 'building'},
        )

        location = candidate.promote_to_location()

        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'imported')
        self.assertEqual(candidate.location, location)
        self.assertFalse(location.is_published)
        self.assertEqual(location.content_status, 'draft')
        self.assertEqual(location.sources.count(), 1)
        self.assertEqual(self.client.get(f'/guides/{location.pk}/').status_code, 404)
