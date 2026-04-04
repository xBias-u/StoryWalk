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

## Импорт страниц из структуры Drive
Добавлены стартовые страницы локаций из папок Drive (v1):
```bash
python manage.py import_drive_places
```
Источник данных: `guides/data/drive_places_v1.json`

## Как добавить свои mp3-озвучки
Рекомендуемый путь (самый простой):
1. Открой админку `/admin/`
2. Создай/открой `AudioGuide`
3. Выбери нужную `Location`
4. Загрузи mp3 в поля:
   - `audio_short_file` — короткая версия
   - `audio_long_file` — длинная версия
   - `audio_file` — fallback (обратная совместимость)
5. Заполни `duration_seconds`, `voice_name` (опционально)

После сохранения аудио автоматически появится на странице локации (`/guides/<id>/`).

CLI-вариант (без админки):
```bash
python manage.py set_location_audio --title "Кремль" --short /path/to/kreml_short.mp3 --long /path/to/kreml_long.mp3 --voice "Florian"
```

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
