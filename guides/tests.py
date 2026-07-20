from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AudioGuide, Location, LocationImage


class HomePageSmokeTests(TestCase):
    def test_home_page_is_public(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guides/home.html')


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
        )
        cls.other_location = Location.objects.create(
            title='Набережная',
            city='Санкт-Петербург',
            short_description='Прогулка у воды.',
            full_description='История набережной.',
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
