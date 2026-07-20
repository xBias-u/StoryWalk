from django.core.management.base import BaseCommand

from guides.models import Location, SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed initial StoryWalk content'

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
        ]
        for row in locations:
            Location.objects.update_or_create(title=row['title'], defaults=row)

        SubscriptionPlan.objects.filter(is_active=True).delete()

        plans = [
            ('Базовый', 0, 'Бесплатный доступ к открытым историям и ознакомительным прогулкам.'),
            ('Путешественник+', 399, 'Расширенная коллекция прогулок и новые маршруты.'),
            ('StoryWalk Premium', 799, 'Полный доступ к прогулкам и ранним релизам.'),
        ]
        for name, price, description in plans:
            SubscriptionPlan.objects.create(
                name=name,
                price_rub=price,
                description=description,
                is_active=True,
            )

        self.stdout.write(self.style.SUCCESS('Initial content seeded.'))
