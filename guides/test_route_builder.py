from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from guides.models import AudioGuide, Location, PlaceCandidate, WalkRoute


class RedSquareRouteBuilderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Location.objects.create(
            title='Исторический музей',
            city='Москва',
            short_description='Музей.',
            full_description='История музея.',
            latitude='55.755323',
            longitude='37.617882',
            content_status='published',
            is_published=True,
        )
        Location.objects.create(
            title='Красная площадь',
            city='Москва',
            short_description='Площадь.',
            full_description='История площади.',
            latitude='55.753591',
            longitude='37.621501',
            content_status='published',
            is_published=True,
        )
        candidates = [
            ('Воскресенские ворота', 'node/1', '55.755660', '37.618048'),
            ('Мавзолей В. И. Ленина', 'way/2', '55.753721', '37.619902'),
            ('Собор Василия Блаженного', 'way/3', '55.752469', '37.623097'),
        ]
        for name, source_id, latitude, longitude in candidates:
            PlaceCandidate.objects.create(
                name=name,
                city='Москва',
                latitude=latitude,
                longitude=longitude,
                category='historic',
                source_id=source_id,
                source_url=f'https://www.openstreetmap.org/{source_id}',
            )

    def test_builder_creates_hidden_researched_locations_and_draft_route(self):
        call_command('build_red_square_route')

        route = WalkRoute.objects.get(slug='krasnaya-ploshchad-sobrannaya-zanovo')
        self.assertFalse(route.is_published)
        self.assertEqual(route.routing_status, 'estimated')
        self.assertEqual(route.stops.count(), 5)
        self.assertEqual(
            list(route.stops.values_list('location__title', flat=True)),
            [
                'Воскресенские ворота',
                'Исторический музей',
                'Красная площадь',
                'Мавзолей В. И. Ленина',
                'Собор Василия Блаженного',
            ],
        )
        for title in (
            'Воскресенские ворота',
            'Мавзолей В. И. Ленина',
            'Собор Василия Блаженного',
        ):
            location = Location.objects.get(title=title)
            self.assertFalse(location.is_published)
            self.assertEqual(location.content_status, 'researched')
            self.assertGreaterEqual(location.sources.count(), 3)
        self.assertTrue(all(stop.walk_distance_m > 0 for stop in route.stops.exclude(position=1)))
        self.assertEqual(self.client.get(route.get_absolute_url()).status_code, 404)

        editor = get_user_model().objects.create_user(
            username='route-editor',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(editor)
        response = self.client.get(route.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Редакторский предпросмотр')

    def test_script_command_prepares_text_without_fake_audio(self):
        call_command('build_red_square_route')
        call_command('prepare_red_square_scripts')

        for title in (
            'Воскресенские ворота',
            'Исторический музей',
            'Красная площадь',
            'Мавзолей В. И. Ленина',
            'Собор Василия Блаженного',
        ):
            location = Location.objects.get(title=title)
            guide = AudioGuide.objects.get(location=location)
            self.assertEqual(location.content_status, 'scripted')
            self.assertGreater(len(guide.short_script), 500)
            self.assertFalse(guide.has_audio)

        editor = get_user_model().objects.create_user(
            username='script-editor',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(editor)
        route = WalkRoute.objects.get(slug='krasnaya-ploshchad-sobrannaya-zanovo')
        response = self.client.get(route.get_absolute_url())
        self.assertGreaterEqual(
            response.content.decode().count('История готовится'),
            5,
        )
