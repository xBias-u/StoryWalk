from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, SimpleTestCase, override_settings

from guides.models import Location, RouteStop, WalkRoute
from guides.services.valhalla import PedestrianRoute, RouteLeg, ValhallaClient, ValhallaError
from guides.views import build_route_visualization


class ValhallaClientTests(SimpleTestCase):
    def test_decodes_polyline6_as_geojson_coordinates(self):
        coordinates = ValhallaClient.decode_polyline6('_izlhA~rlgdF_{geC~ywl@_kwzCn`{nI')

        self.assertEqual(coordinates[0], [-120.2, 38.5])
        self.assertEqual(coordinates[-1], [-126.453, 43.252])

    def test_rejects_response_with_wrong_leg_count(self):
        with self.assertRaisesRegex(ValhallaError, '0 legs instead of 2'):
            ValhallaClient._parse_route({'trip': {'legs': []}}, expected_legs=2)


@override_settings(VALHALLA_API_URL='https://routing.example/route')
class VerifyRouteWalkingTests(TestCase):
    def setUp(self):
        self.route = WalkRoute.objects.create(
            title='Тестовая прогулка',
            slug='test-walk',
            city='Москва',
            summary='Маршрут для теста.',
            distance_km='0.1',
            routing_status='estimated',
        )
        for position, coordinates in enumerate([
            ('55.750000', '37.610000'),
            ('55.751000', '37.611000'),
            ('55.752000', '37.612000'),
        ], start=1):
            location = Location.objects.create(
                title=f'Точка {position}',
                short_description='Точка.',
                full_description='Описание.',
                latitude=coordinates[0],
                longitude=coordinates[1],
            )
            RouteStop.objects.create(
                route=self.route,
                location=location,
                position=position,
            )

    @patch('guides.management.commands.verify_route_walking.ValhallaClient.route')
    def test_command_stores_verified_legs_and_geometry(self, route_mock):
        route_mock.return_value = PedestrianRoute(
            distance_m=650,
            duration_seconds=510,
            legs=[
                RouteLeg(250, 180, [[37.61, 55.75], [37.611, 55.751]]),
                RouteLeg(400, 330, [[37.611, 55.751], [37.612, 55.752]]),
            ],
        )

        output = StringIO()
        call_command('verify_route_walking', self.route.slug, stdout=output)

        self.route.refresh_from_db()
        self.assertEqual(self.route.routing_status, 'verified')
        self.assertEqual(self.route.routing_provider, 'valhalla')
        self.assertEqual(str(self.route.distance_km), '0.7')
        self.assertEqual(self.route.route_geometry['type'], 'FeatureCollection')
        self.assertIsNotNone(self.route.routing_updated_at)
        self.assertEqual(
            list(self.route.stops.values_list('walk_distance_m', 'walk_minutes')),
            [(0, 0), (250, 3), (400, 6)],
        )
        self.assertIn('Pedestrian route verified', output.getvalue())

        visualization = build_route_visualization(
            self.route,
            list(self.route.stops.select_related('location')),
        )
        self.assertEqual(len(visualization['paths']), 2)
        self.assertEqual(len(visualization['markers']), 3)
