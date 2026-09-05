from django.core.exceptions import ValidationError
from django.http import HttpResponseNotFound
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from config.middleware import DemoMediaWhiteNoiseMiddleware
from guides.models import Location, WalkRoute


class ReleaseInvariantTests(TestCase):
    def test_location_cannot_be_marked_public_with_a_draft_status(self):
        location = Location(
            title='Черновик',
            short_description='Коротко.',
            full_description='Подробно.',
            content_status='draft',
            is_published=True,
        )

        with self.assertRaises(ValidationError):
            location.full_clean()

    def test_route_cannot_be_marked_public_before_routing_is_verified(self):
        route = WalkRoute(
            title='Черновой маршрут',
            slug='draft-route',
            city='Москва',
            summary='Проверка.',
            routing_status='estimated',
            is_published=True,
        )

        with self.assertRaises(ValidationError):
            route.full_clean()


class DemoMediaTests(SimpleTestCase):
    @override_settings(SERVE_MEDIA_FILES=True, WHITENOISE_AUTOREFRESH=True)
    def test_bundled_audio_supports_byte_range_requests(self):
        middleware = DemoMediaWhiteNoiseMiddleware(lambda request: HttpResponseNotFound())
        request = RequestFactory().get(
            '/media/audio_guides/red_square_short.mp3',
            HTTP_RANGE='bytes=0-99',
        )

        response = middleware(request)
        try:
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response['Content-Type'], 'audio/mpeg')
            self.assertTrue(response['Content-Range'].startswith('bytes 0-99/'))
            self.assertEqual(response['Content-Length'], '100')
        finally:
            response.close()
