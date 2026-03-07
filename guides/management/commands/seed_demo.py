from django.core.management.base import BaseCommand
from guides.models import Location, SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed demo data for StoryWalk MVP'

    def handle(self, *args, **options):
        locations = [
            {
                'title': 'Красная площадь',
                'city': 'Москва',
                'short_description': 'Исторический центр столицы и символ России.',
                'full_description': 'Красная площадь — главная площадь Москвы, где расположены Кремль, ГУМ и собор Василия Блаженного.',
                'segment': 'mixed',
                'access_level': 'free',
            },
            {
                'title': 'Корпус ВШЭ на Мясницкой',
                'city': 'Москва',
                'short_description': 'Исторический кампус ВШЭ в центре Москвы, на Мясницкой улице.',
                'full_description': 'Корпус ВШЭ на Мясницкой — один из ключевых учебных корпусов университета. Удобная локация в центре города и активная студенческая среда делают его важной точкой на академической карте Москвы.',
                'is_featured': True,
                'segment': 'solo',
                'access_level': 'paid',
            },
            {
                'title': 'ВДНХ',
                'city': 'Москва',
                'short_description': 'Выставочный комплекс с архитектурой и музеями.',
                'full_description': 'ВДНХ — крупный культурно-выставочный комплекс с павильонами, музеями и прогулочными зонами.',
                'segment': 'family',
                'access_level': 'free',
            },
        ]
        for row in locations:
            Location.objects.update_or_create(title=row['title'], defaults=row)

        plans = [
            ('Базовый', 0, 'Бесплатный доступ к базовым аудиогидам и ознакомительным маршрутам.'),
            ('Путешественник+', 399, 'Расширенная библиотека аудиогидов и новые маршруты.'),
            ('StoryWalk Premium', 799, 'Полный доступ к расширенным гидам и ранним релизам.'),
        ]
        for name, price, desc in plans:
            SubscriptionPlan.objects.update_or_create(
                name=name,
                defaults={'price_rub': price, 'description': desc, 'is_demo': True},
            )

        self.stdout.write(self.style.SUCCESS('Demo data seeded.'))
