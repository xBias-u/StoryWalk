# StoryWalk

MVP веб-сервиса с аудиогидами по достопримечательностям.

## Что реализовано
- Django-проект с авторизацией
- Список локаций и детальная страница
- Встроенный HTML5-аудиоплеер для mp3
- Демо-раздел подписки
- Админка для управления контентом

## Локальный запуск
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

После запуска:
- Главная: http://127.0.0.1:8000/
- Админка: http://127.0.0.1:8000/admin/
