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
            },
            {
                'title': 'ВДНХ',
                'city': 'Москва',
                'short_description': 'Выставочный комплекс с архитектурой и музеями.',
                'full_description': 'ВДНХ — крупный культурно-выставочный комплекс с павильонами, музеями и прогулочными зонами.',
            },
        ]
        for row in locations:
            Location.objects.get_or_create(title=row['title'], defaults=row)

        plans = [
            ('Free Demo', 0, 'Доступ к базовым аудиогидам.'),
            ('StoryWalk Plus', 399, 'Расширенная библиотека и персональные подборки.'),
            ('StoryWalk Pro', 799, 'Все возможности и ранний доступ к новым маршрутам.'),
        ]
        for name, price, desc in plans:
            SubscriptionPlan.objects.get_or_create(
                name=name,
                defaults={'price_rub': price, 'description': desc, 'is_demo': True},
            )

        self.stdout.write(self.style.SUCCESS('Demo data seeded.'))
