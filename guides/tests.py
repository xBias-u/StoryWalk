import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    AudioGuide,
    AudioListenEvent,
    Location,
    LocationImage,
    LocationSource,
    RouteStop,
    WalkRoute,
)


class HomePageSmokeTests(TestCase):
    def test_health_check_reports_database_readiness(self):
        response = self.client.get(reverse('health_check'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_home_page_is_public(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guides/home.html')


class LocationEditorialWorkflowTests(TestCase):
    def test_readiness_explains_what_is_missing(self):
        location = Location.objects.create(
            title='Дом с историей',
            city='Москва',
            short_description='Коротко.',
            full_description='Подробно.',
        )

        self.assertEqual(
            location.content_readiness_issues(),
            [
                'нет координат',
                'нет главной идеи',
                'меньше двух источников',
                'нет сценария',
                'нет аудио',
            ],
        )

    def test_location_is_ready_with_coordinates_angle_and_two_sources(self):
        location = Location.objects.create(
            title='Дом с историей',
            city='Москва',
            short_description='Коротко.',
            full_description='Подробно.',
            latitude='55.755800',
            longitude='37.617300',
            story_angle='Фасад показывает, как город менял представление о себе.',
        )
        LocationSource.objects.create(
            location=location,
            title='Официальная история',
            url='https://example.com/official',
            is_primary=True,
        )
        LocationSource.objects.create(
            location=location,
            title='Архивная справка',
            url='https://example.com/archive',
        )
        AudioGuide.objects.create(
            location=location,
            short_script='Остановитесь и посмотрите на фасад.',
            audio_file='audio_guides/story.mp3',
            audio_short_file='audio_guides/story-short.mp3',
        )

        self.assertEqual(location.content_readiness_issues(), [])


class GuidePagesSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='walker',
            password='test-password',
        )
        cls.location = Location.objects.create(
            title='Палаты XVII века',
            city='Москва',
            short_description='Тихая историческая точка в центре города.',
            full_description='История места для аудиопрогулки.',
            is_featured=True,
            content_status='published',
            is_published=True,
        )
        cls.other_location = Location.objects.create(
            title='Набережная',
            city='Санкт-Петербург',
            short_description='Прогулка у воды.',
            full_description='История набережной.',
            content_status='published',
            is_published=True,
        )
        cls.audio_guide = AudioGuide.objects.create(
            location=cls.location,
            audio_file='audio_guides/main.mp3',
            audio_short_file='audio_guides/short.mp3',
            audio_long_file='audio_guides/long.mp3',
            voice_name='StoryWalk',
        )
        cls.first_image = LocationImage.objects.create(
            location=cls.location,
            image='locations/gallery/first.jpg',
            sort_order=20,
        )
        cls.second_image = LocationImage.objects.create(
            location=cls.location,
            image='locations/gallery/second.jpg',
            sort_order=10,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_catalog_is_public(self):
        self.client.logout()
        url = reverse('location_list')

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guides/location_list.html')

    def test_location_detail_is_public(self):
        self.client.logout()
        url = reverse('location_detail', args=[self.location.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guides/location_detail.html')

    def test_catalog_renders_and_filters_locations(self):
        response = self.client.get(
            reverse('location_list'),
            {'q': 'Палаты', 'city': 'Москва'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guides/location_list.html')
        self.assertContains(response, self.location.title)
        self.assertNotContains(response, self.other_location.title)

    def test_location_detail_renders_audio_versions_and_gallery(self):
        response = self.client.get(
            reverse('location_detail', args=[self.location.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guides/location_detail.html')
        self.assertContains(response, self.audio_guide.audio_short_file.url)
        self.assertContains(response, self.audio_guide.audio_long_file.url)
        self.assertContains(response, self.first_image.image.url)
        self.assertContains(response, self.second_image.image.url)
        self.assertContains(response, 'data-player', count=2)

    def test_gallery_images_follow_sort_order(self):
        images = list(self.location.gallery_images.all())

        self.assertEqual(images, [self.second_image, self.first_image])

    def test_anonymous_listener_can_send_audio_progress(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.get(reverse('location_detail', args=[self.location.pk]))
        csrf_token = csrf_client.cookies['csrftoken'].value

        response = csrf_client.post(
            reverse('audio_event_api'),
            data=json.dumps({
                'location_id': self.location.pk,
                'event_type': 'start',
                'session_id': 'test-session-001',
                'audio_variant': 'short',
                'current_seconds': 0,
                'duration_seconds': 120,
                'completion_percent': 0,
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        event = AudioListenEvent.objects.get(location=self.location)
        self.assertIsNone(event.user)
        self.assertEqual(event.session_id, 'test-session-001')
        self.assertEqual(event.audio_variant, 'short')

    def test_audio_event_rejects_malformed_payloads_without_server_error(self):
        url = reverse('audio_event_api')

        array_response = self.client.post(url, data='[]', content_type='application/json')
        number_response = self.client.post(
            url,
            data=json.dumps({
                'location_id': self.location.pk,
                'event_type': 'progress',
                'session_id': 'invalid-number-session',
                'audio_variant': 'short',
                'current_seconds': 'not-a-number',
            }),
            content_type='application/json',
        )

        self.assertEqual(array_response.status_code, 400)
        self.assertEqual(number_response.status_code, 400)
        self.assertEqual(AudioListenEvent.objects.count(), 0)

    def test_audio_event_deduplicates_immediate_retries(self):
        payload = {
            'location_id': self.location.pk,
            'event_type': 'progress',
            'session_id': 'dedupe-session-001',
            'audio_variant': 'short',
            'current_seconds': 20,
            'duration_seconds': 100,
            'completion_percent': 20,
        }
        url = reverse('audio_event_api')

        first = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        second = self.client.post(url, data=json.dumps(payload), content_type='application/json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()['duplicate'])
        self.assertEqual(AudioListenEvent.objects.filter(session_id='dedupe-session-001').count(), 1)

    def test_metrics_are_staff_only(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('metrics')).status_code, 403)

        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.assertEqual(self.client.get(reverse('metrics')).status_code, 200)

    def test_favorite_does_not_redirect_to_an_external_referer(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('toggle_favorite', args=[self.location.pk]),
            HTTP_REFERER='https://attacker.example/leave',
        )

        self.assertRedirects(response, reverse('location_detail', args=[self.location.pk]))


class RouteFlowSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.locations = [
            Location.objects.create(
                title=f'Точка {number}',
                city='Москва',
                short_description=f'Короткая история точки {number}.',
                full_description=f'Полная история точки {number}.',
                content_status='published',
                is_published=True,
            )
            for number in range(1, 4)
        ]
        cls.route = WalkRoute.objects.create(
            title='Городской маршрут',
            slug='city-route',
            city='Москва',
            district='Китай-город',
            summary='Три связанные истории в центре города.',
            duration_minutes=60,
            distance_km=2.1,
            interest='architecture',
            routing_status='verified',
            is_published=True,
        )
        for position, location in enumerate(cls.locations, start=1):
            RouteStop.objects.create(
                route=cls.route,
                location=location,
                position=position,
                walk_minutes=0 if position == 1 else 8,
                navigation_hint=f'Идите к точке {position}.',
                observation_prompt=f'Посмотрите на точку {position}.',
            )

    def test_preferences_redirect_to_matching_route(self):
        response = self.client.get(reverse('route_match'), {
            'city': 'Москва',
            'duration': '60',
            'interest': 'architecture',
        })

        expected_url = f"{reverse('route_preview', args=[self.route.slug])}?duration=60&interest=architecture"
        self.assertRedirects(response, expected_url)

    def test_route_preview_renders_ordered_stops(self):
        response = self.client.get(reverse('route_preview', args=[self.route.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guides/route_preview.html')
        self.assertContains(response, self.route.title)
        for location in self.locations:
            self.assertContains(response, location.title)

    def test_walk_mode_moves_between_stops(self):
        url = reverse('route_walk', args=[self.route.slug])

        first_response = self.client.get(url)
        second_response = self.client.get(url, {'stop': 2})

        self.assertEqual(first_response.status_code, 200)
        self.assertTemplateUsed(first_response, 'guides/route_walk.html')
        self.assertContains(first_response, self.locations[0].title)
        self.assertContains(first_response, self.locations[1].title)
        self.assertContains(second_response, self.locations[1].title)
        self.assertContains(second_response, '2/3')

    def test_public_route_with_an_unpublished_stop_is_hidden(self):
        first_location = self.locations[0]
        first_location.is_published = False
        first_location.save(update_fields=['is_published'])

        response = self.client.get(reverse('route_preview', args=[self.route.slug]))

        self.assertEqual(response.status_code, 404)
