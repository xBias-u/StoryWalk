from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from guides.models import AudioGuide, Location, LocationImage, WalkRoute


class DemoSeedTests(TestCase):
    def test_seed_demo_is_idempotent_and_public_content_is_ready(self):
        call_command('seed_demo', verbosity=0)
        first_counts = self._counts()
        call_command('seed_demo', verbosity=0)

        self.assertEqual(self._counts(), first_counts)
        self.assertEqual(Location.objects.filter(is_published=True).count(), 5)
        self.assertFalse(Location.objects.filter(title='Эритаж').exists())
        self.assertTrue(Location.objects.filter(title='Эрмитаж').exists())

        for location in Location.objects.filter(is_published=True):
            self.assertEqual(location.content_status, 'published')
            self.assertEqual(location.content_readiness_issues(), [])
            guide = location.audio_guide
            self.assertTrue(guide.audio_short_file)
            self.assertGreater(Path(guide.audio_short_file.path).stat().st_size, 1_000)

        route = WalkRoute.objects.get(is_published=True)
        self.assertEqual(route.slug, 'krasnaya-ploshchad-sobrannaya-zanovo')
        self.assertEqual(route.routing_status, 'verified')
        self.assertEqual(route.stops.count(), 5)
        self.assertTrue(route.route_geometry['features'])
        self.assertFalse(route.stops.filter(location__is_published=False).exists())

    @staticmethod
    def _counts():
        return {
            'locations': Location.objects.count(),
            'guides': AudioGuide.objects.count(),
            'images': LocationImage.objects.count(),
            'routes': WalkRoute.objects.count(),
        }
