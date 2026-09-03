from django.core.management.base import BaseCommand, CommandError

from django.utils import timezone

from guides.models import Location, LocationSource, RouteStop, WalkRoute


class Command(BaseCommand):
    help = 'Create the initial editorial StoryWalk route from existing locations'

    def handle(self, *args, **options):
        stop_data = [
            {
                'title': 'Исторический музей',
                'latitude': '55.755323',
                'longitude': '37.617882',
                'story_angle': 'Здание выглядит древним, но на самом деле показывает, как XIX век представлял русскую историю.',
                'sources': [
                    {
                        'title': 'История Государственного исторического музея',
                        'publisher': 'Государственный исторический музей',
                        'url': 'https://shm.ru/kollektsii-i-muzeynyy-kompleks/museum_history/istoricheskiy-muzey/history/',
                        'is_primary': True,
                    },
                    {
                        'title': 'Путеводитель по Государственному историческому музею',
                        'publisher': 'Культура.РФ',
                        'url': 'https://www.culture.ru/s/shm/',
                        'is_primary': False,
                    },
                ],
                'walk_minutes': 0,
                'navigation_hint': 'Начните у главного входа со стороны Красной площади.',
                'observation_prompt': 'Посмотрите на башни, шатры и детали фасада — здание само рассказывает, каким в XIX веке представляли образ русской истории.',
            },
            {
                'title': 'Красная площадь',
                'latitude': '55.753591',
                'longitude': '37.621501',
                'story_angle': 'Красная площадь — не пустой фон для церемоний, а пространство, где архитектура разных эпох спорит и складывается в единый образ.',
                'sources': [
                    {
                        'title': 'Kremlin and Red Square, Moscow',
                        'publisher': 'UNESCO World Heritage Centre',
                        'url': 'https://whc.unesco.org/en/list/545/',
                        'is_primary': True,
                    },
                    {
                        'title': 'История Музеев Московского Кремля',
                        'publisher': 'Музеи Московского Кремля',
                        'url': 'https://www.kreml.ru/about-museums/history/istoriya-muzeev-moskovskogo-kremlya/',
                        'is_primary': True,
                    },
                ],
                'walk_minutes': 4,
                'navigation_hint': 'Пройдите от музея к центру площади и остановитесь там, где открывается вид на Кремль и собор Василия Блаженного.',
                'observation_prompt': 'Не спешите фотографировать: сначала проследите взглядом, как разные эпохи собраны вокруг одного открытого пространства.',
            },
            {
                'title': 'Корпус ВШЭ на Мясницкой',
                'latitude': '55.761494',
                'longitude': '37.633343',
                'story_angle': 'Одна плитка у входа связывает университет с торговой и инженерной Москвой рубежа XIX–XX веков.',
                'sources': [
                    {
                        'title': 'Вышка. Фундамент — Мясницкая, 20',
                        'publisher': 'НИУ ВШЭ',
                        'url': 'https://www.hse.ru/fundament',
                        'is_primary': True,
                    },
                    {
                        'title': 'Геометрия Мясницкой',
                        'publisher': 'The Vyshka',
                        'url': 'https://thevyshka.ru/2015/03/02/myasnitskaya/',
                        'is_primary': False,
                    },
                ],
                'walk_minutes': 22,
                'navigation_hint': 'Выйдите на Никольскую улицу, пройдите к Лубянской площади и продолжайте по Мясницкой до дома 20.',
                'observation_prompt': 'Во входной зоне найдите историческую плитку «Мюръ и Мерилизъ» — маленькую деталь, связывающую университет с торговой Москвой.',
            },
        ]

        locations = {location.title: location for location in Location.objects.filter(
            title__in=[item['title'] for item in stop_data]
        )}
        missing = [item['title'] for item in stop_data if item['title'] not in locations]
        if missing:
            raise CommandError(
                'Missing locations: ' + ', '.join(missing) + '. Run import_drive_places first.'
            )

        for item in stop_data:
            location = locations[item['title']]
            location.latitude = item['latitude']
            location.longitude = item['longitude']
            location.story_angle = item['story_angle']
            location.save(update_fields=['latitude', 'longitude', 'story_angle'])
            for source in item['sources']:
                LocationSource.objects.update_or_create(
                    location=location,
                    url=source['url'],
                    defaults={
                        'title': source['title'],
                        'publisher': source['publisher'],
                        'is_primary': source['is_primary'],
                        'checked_at': timezone.localdate(),
                    },
                )

        route, _ = WalkRoute.objects.update_or_create(
            slug='vorota-kitay-goroda',
            defaults={
                'title': 'Ворота Китай-города',
                'city': 'Москва',
                'district': 'Китай-город',
                'summary': 'От парадной Красной площади через Никольскую и Лубянку — к торговой и университетской истории Мясницкой.',
                'duration_minutes': 60,
                'distance_km': 2.1,
                'interest': 'architecture',
                'routing_status': 'estimated',
                'is_published': False,
            },
        )

        route.stops.all().delete()
        for position, item in enumerate(stop_data, start=1):
            RouteStop.objects.create(
                route=route,
                location=locations[item['title']],
                position=position,
                walk_minutes=item['walk_minutes'],
                walk_distance_m=0,
                navigation_hint=item['navigation_hint'],
                observation_prompt=item['observation_prompt'],
            )

        self.stdout.write(self.style.SUCCESS(f'Route ready: {route.title} ({route.stops.count()} stops)'))
