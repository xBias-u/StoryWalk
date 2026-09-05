import math

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from guides.models import Location, LocationSource, PlaceCandidate, RouteStop, WalkRoute


class Command(BaseCommand):
    help = 'Build an unpublished editorial route around Red Square from reviewed candidates.'

    def handle(self, *args, **options):
        curated = {
            'Воскресенские ворота': {
                'short_description': 'Парадный вход на Красную площадь, исчезнувший ради советских парадов и восстановленный в 1990-е.',
                'full_description': (
                    'Воскресенские ворота превращают вход на Красную площадь в отдельный городской ритуал. '
                    'Первые каменные ворота появились здесь в XVI веке, а знакомое завершение с двумя башнями — в конце XVII столетия.\n\n'
                    'В 1931 году сооружение разобрали, освобождая пространство для движения военной техники. '
                    'Современные ворота восстановили в 1994–1995 годах. Поэтому перед нами одновременно исторический образ и поздняя реконструкция.\n\n'
                    'Для прогулки важен сам момент перехода: всего один шаг отделяет шум Манежной площади от пространства, которое веками служило сценой государственной церемонии.'
                ),
                'story_angle': 'Ворота показывают, как город сначала удаляет неудобную память, а затем собирает её заново.',
                'sources': [
                    ('Гид по Красной площади', 'Культура.РФ', 'https://www.culture.ru/materials/256846/gid-po-krasnoi-ploshadi-marshrut-ot-gosudarstvennogo-istoricheskogo-muzeya'),
                    ('100 лучших мест Москвы', 'Правительство Москвы', 'https://www.mos.ru/upload/documents/oiv/100_luchshikh_mest_moskvy.pdf'),
                ],
            },
            'Мавзолей В. И. Ленина': {
                'short_description': 'Ступенчатый гранитный монумент, превративший временный траурный ритуал в постоянную архитектуру площади.',
                'full_description': (
                    'После смерти Владимира Ленина в 1924 году на Красной площади последовательно появились временные деревянные сооружения. '
                    'Современный каменный Мавзолей по проекту Алексея Щусева был завершён к 1930 году.\n\n'
                    'Его строгая ступенчатая форма резко отличается от башен и храмов вокруг, но масштаб намеренно подчинён площади и Кремлёвской стене. '
                    'Красный, чёрный и серый камень превращают небольшое здание в визуальный центр протяжённой трибуны.\n\n'
                    'Эта остановка — не оценка политической эпохи, а наблюдение за тем, как архитектура делает память публичной, управляемой и долговечной.'
                ),
                'story_angle': 'Мавзолей показывает, как временный ритуал может стать постоянной архитектурой власти.',
                'sources': [
                    ('История и современность Московского Кремля', 'Федеральная служба охраны России', 'https://fso.gov.ru/struct/skmk/history-moskremlin/'),
                    ('Kremlin and Red Square, Moscow', 'UNESCO World Heritage Centre', 'https://whc.unesco.org/en/list/545/'),
                ],
            },
            'Собор Василия Блаженного': {
                'short_description': 'Собор-памятник XVI века, чей знакомый многоцветный образ складывался и менялся на протяжении столетий.',
                'full_description': (
                    'Покровский собор возвели в середине XVI века в память о взятии Казани. '
                    'Но привычный нам красочный силуэт не возник в один момент: декоративное оформление куполов и фасадов менялось в последующие столетия.\n\n'
                    'С расстояния собор кажется почти сказочной скульптурой. Подойдите ближе и проследите, как отдельные объёмы, переходы и купола собираются вокруг центральной композиции. '
                    'Единство здесь рождается не из симметрии одинаковых частей, а из тщательно удерживаемого разнообразия.\n\n'
                    'Финал маршрута меняет привычный взгляд: главный символ Москвы оказывается не застывшим образом, а зданием со своей долгой историей перестроек, реставраций и новых прочтений.'
                ),
                'story_angle': 'Знакомый сказочный образ собора — результат нескольких веков изменений, а не одно мгновение XVI века.',
                'sources': [
                    ('Покровский собор: коллизии XX столетия', 'Государственный исторический музей', 'https://stbasil.shm.ru/20century/'),
                    ('Kremlin and Red Square, Moscow', 'UNESCO World Heritage Centre', 'https://whc.unesco.org/en/list/545/'),
                ],
            },
        }

        locations = {}
        for name, content in curated.items():
            try:
                candidate = PlaceCandidate.objects.get(name=name)
            except PlaceCandidate.DoesNotExist as exc:
                raise CommandError(
                    f'Candidate not found: {name}. Run discover_route_candidates first.'
                ) from exc
            candidate.status = 'shortlisted'
            candidate.save(update_fields=['status', 'updated_at'])
            location = candidate.promote_to_location()
            location.short_description = content['short_description']
            location.full_description = content['full_description']
            location.story_angle = content['story_angle']
            location.content_status = 'researched'
            location.is_published = False
            location.editorial_notes = 'Нужно подготовить короткий и длинный аудиосценарии и проверить формулировки на месте.'
            location.save(update_fields=[
                'short_description',
                'full_description',
                'story_angle',
                'content_status',
                'is_published',
                'editorial_notes',
            ])
            for title, publisher, url in content['sources']:
                LocationSource.objects.update_or_create(
                    location=location,
                    url=url,
                    defaults={
                        'title': title,
                        'publisher': publisher,
                        'is_primary': publisher in {
                            'Государственный исторический музей',
                            'Федеральная служба охраны России',
                            'Правительство Москвы',
                        },
                        'checked_at': timezone.localdate(),
                    },
                )
            locations[name] = location

        for existing_name in ('Исторический музей', 'Красная площадь'):
            try:
                locations[existing_name] = Location.objects.get(title=existing_name)
            except Location.DoesNotExist as exc:
                raise CommandError(f'Existing location not found: {existing_name}') from exc

        stop_data = [
            ('Воскресенские ворота', 'Начните со стороны Манежной площади и пройдите к двум аркам ворот.', 'Остановитесь до прохода и сравните две стороны городского порога.'),
            ('Исторический музей', 'После ворот поверните направо к главному фасаду Исторического музея.', 'Найдите детали, которые выглядят древними, хотя здание построено в XIX веке.'),
            ('Красная площадь', 'Выйдите на открытое пространство площади и двигайтесь вдоль Кремлёвской стены.', 'Посмотрите, как здания разных эпох удерживают границы огромного пустого пространства.'),
            ('Мавзолей В. И. Ленина', 'Подойдите к центральной части Кремлёвской стены и остановитесь напротив Мавзолея.', 'Сравните масштаб Мавзолея с башнями и стеной: здание гораздо меньше, чем кажется на фотографиях.'),
            ('Собор Василия Блаженного', 'Продолжайте к южному краю площади до собора Василия Блаженного.', 'Сначала охватите силуэт целиком, затем выберите один купол и проследите поддерживающий его объём.'),
        ]

        route, _ = WalkRoute.objects.update_or_create(
            slug='krasnaya-ploshchad-sobrannaya-zanovo',
            defaults={
                'title': 'Красная площадь: собранная заново',
                'city': 'Москва',
                'district': 'Красная площадь',
                'summary': 'Пять остановок о том, как Москва строила, разрушала и заново собирала своё главное пространство.',
                'duration_minutes': 30,
                'distance_km': 0.9,
                'interest': 'architecture',
                'routing_status': 'estimated',
                'is_published': False,
            },
        )
        route.stops.all().delete()

        previous = None
        for position, (name, navigation_hint, observation_prompt) in enumerate(stop_data, start=1):
            location = locations[name]
            distance = self._estimated_walk_distance(previous, location) if previous else 0
            walk_minutes = max(1, math.ceil(distance / 75)) if distance else 0
            RouteStop.objects.create(
                route=route,
                location=location,
                position=position,
                walk_minutes=walk_minutes,
                walk_distance_m=distance,
                navigation_hint=navigation_hint,
                observation_prompt=observation_prompt,
            )
            previous = location

        self.stdout.write(self.style.SUCCESS(
            f'Draft route ready: {route.title} ({route.stops.count()} stops, unpublished)'
        ))

    @staticmethod
    def _estimated_walk_distance(first, second):
        radius = 6_371_000
        lat1 = math.radians(float(first.latitude))
        lat2 = math.radians(float(second.latitude))
        delta_lat = lat2 - lat1
        delta_lon = math.radians(float(second.longitude) - float(first.longitude))
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        straight_distance = radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(straight_distance * 1.25)
