# StoryWalk

MVP веб-сервиса с аудиогидами по достопримечательностям.

## Что реализовано
- Django-проект с авторизацией и регистрацией
- Список локаций, детальная страница и избранное
- Встроенный кастомный HTML5-аудиоплеер
- Демо-раздел тарифов (фримиум-логика)
- Метрики MVP по прослушиваниям (`/metrics`)
- Админка для управления контентом и событиями

## Локальный запуск
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

После запуска:
- Главная: http://127.0.0.1:8000/
- Админка: http://127.0.0.1:8000/admin/

## Прод-готовность (Render/Railway)
Проект уже подготовлен для деплоя:
- `gunicorn`
- `whitenoise` (статика)
- настройки через env (`.env.example`)
- `Procfile`

### Переменные окружения
- `DEBUG=False`
- `SECRET_KEY=<secure-random-string>`
- `ALLOWED_HOSTS=<your-domain>`
- `CSRF_TRUSTED_ORIGINS=https://<your-domain>`
- `DATABASE_URL=<postgres-url>`

### Команды деплоя
Build command:
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

Start command:
```bash
gunicorn config.wsgi:application --log-file -
```

> Для полноценного прод-режима рекомендуется PostgreSQL.
