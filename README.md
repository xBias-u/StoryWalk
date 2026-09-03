# StoryWalk

Веб-сервис персональных аудиопрогулок, который помогает меньше смотреть в экран и больше замечать город вокруг.

## Что реализовано
- Django-проект с авторизацией и регистрацией
- Список локаций, детальная страница и избранное
- Встроенный кастомный HTML5-аудиоплеер
- Страница вариантов доступа
- Метрики MVP по прослушиваниям (`/metrics`)
- Админка для управления контентом и событиями

## Локальный запуск
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

`seed_demo` идемпотентна: её можно запускать повторно. Команда без сетевых
вызовов создаёт пять готовых остановок, привязывает bundled MP3 и публикует один
проверенный маршрут по Красной площади. Остальной импортированный контент остаётся
скрытым до редакционной проверки.

Администратора можно создать отдельно:

```bash
python manage.py createsuperuser
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
python manage.py set_location_audio --title "Красная площадь" --short /path/to/kreml_short.mp3 --long /path/to/kreml_long.mp3 --voice "Florian"
```

### Генерация озвучки через ElevenLabs

1. Скопируй `.env.example` в `.env` и добавь новый API-ключ и выбранный `voice_id`.
2. Загрузи переменные в текущую shell-сессию: `set -a; source .env; set +a`.
3. Подготовь отдельный UTF-8 файл с финальным текстом для слуха — это должен быть сценарий, а не текст статьи.
4. Сгенерируй сначала одну короткую версию:

```bash
python manage.py generate_location_audio \
  --title "Красная площадь" \
  --length short \
  --text-file guides/data/red-square-short.txt
```

Команда сохраняет MP3 в `media/audio_guides/` и привязывает его к `AudioGuide`. Существующее аудио не перезаписывается без явного флага `--force`. Ключ ElevenLabs нельзя передавать аргументом команды или коммитить в Git.

## Редакционный конвейер точки

Каждая локация проходит стадии `черновик → факты проверены → сценарий готов → озвучено → опубликовано`.

Перед публикацией в админке должны быть заполнены:

- координаты;
- одна ясная идея истории;
- минимум два источника, включая по возможности официальный;
- короткий или длинный сценарий;
- соответствующий аудиофайл.

Колонка «Готовность» в списке локаций показывает, чего именно не хватает. Тексты сценариев хранятся в `AudioGuide`, поэтому их можно проверить и исправить до повторной генерации аудио.

### Поиск мест рядом

Предварительный просмотр культурных POI вокруг существующей точки:

```bash
python manage.py discover_route_candidates \
  --from-location "Исторический музей" \
  --radius 700 \
  --limit 15
```

Чтобы сохранить результат во внутренний редакционный inbox, добавь `--save`. Команда не создаёт и не публикует пользовательские карточки.

В админке открой «Кандидаты мест». Там можно:

- добавить место в шорт-лист;
- отклонить нерелевантное;
- создать скрытый черновик локации для дальнейшего исследования.

OpenStreetMap используется только для обнаружения названия, координат и базовой категории. Его карточка не заменяет исторические источники: перед публикацией нужны минимум две отдельные проверяемые ссылки.

### Сборка редакционного маршрута Красной площади

После сохранения кандидатов команда создаёт три исследованных, но скрытых черновика и неопубликованный маршрут из пяти остановок:

```bash
python manage.py build_red_square_route
```

Сотрудник, вошедший в админку, может открыть URL чернового маршрута и увидеть редакторский предпросмотр. Для анонимных пользователей тот же URL возвращает `404`. Расстояния и время переходов пока имеют статус «оценено» и должны быть заменены данными пешеходного Directions API перед публикацией.

Подготовить короткие сценарии новых остановок без генерации аудио:

```bash
python manage.py prepare_red_square_scripts
```

Для полностью локального MVP на macOS можно временно озвучить сохранённый сценарий системным русским голосом:

```bash
python manage.py generate_location_audio \
  --title "Воскресенские ворота" \
  --length short \
  --provider apple \
  --voice-name "Milena — local MVP"
```

Этот провайдер предназначен только для локальной демонстрации. Финальные брендовые файлы должны быть перегенерированы утверждённым голосом через ElevenLabs.

Проверить все переходы по пешеходному графу Valhalla и сохранить расстояния, время и GeoJSON-линию:

```bash
python manage.py verify_route_walking krasnaya-ploshchad-sobrannaya-zanovo
```

Для локального прототипа используется публичный сервер Valhalla. В production укажи управляемый или собственный endpoint через `VALHALLA_API_URL`; публичный сервер не должен быть инфраструктурной зависимостью продукта.

## Bulk-загрузка картинок локаций
1. Создай папку, например:
```bash
mkdir -p media/location_images
```
2. Положи туда файлы с именами-алиасами:
- `isaakievskiy_sobor.jpg`
- `istoricheskiy_muzey.jpg`
- `kreml.jpg`
- `kungur.jpg`
- `ermitazh.jpg`

3. Запусти импорт:
```bash
python manage.py import_location_images --dir media/location_images
```

## Bulk-галерея (несколько фото на локацию)
Если для одной локации много фото, используй префиксы в именах файлов:
- `kreml1.png`, `kreml2.png`, ...
- `kungur1.png`, `kungur2.png`, ...
- `isaakievskiy_sobor1.png`, ...

Импорт:
```bash
python manage.py import_location_gallery --dir media/location_images --clear
```
`--clear` удаляет старую галерею для затронутых локаций перед импортом.

## Поставить обложку из самого тяжёлого файла
```bash
python manage.py set_cover_largest --title "Исаакиевский собор" --dir media/location_images --prefix isaakievskiy_sobor --prefix isaak
```

## Прод-готовность (Render/Railway)
Проект уже подготовлен для деплоя:
- `gunicorn`
- `whitenoise` (статика)
- настройки через env (`.env.example`)
- `Procfile`
- health-check `/healthz/`
- детерминированный `seed_demo`

### Переменные окружения
- `DEBUG=False`
- `SECRET_KEY=<secure-random-string>`
- `ALLOWED_HOSTS=<your-domain>`
- `CSRF_TRUSTED_ORIGINS=https://<your-domain>`
- `DATABASE_URL=<postgres-url>`
- `SERVE_MEDIA_FILES=True` — раздавать bundled demo-media через WhiteNoise
- `ELEVENLABS_API_KEY=<secret-api-key>`
- `ELEVENLABS_VOICE_ID=<selected-voice-id>`

### Команды деплоя
Build command:
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Release/pre-deploy command:
```bash
python manage.py migrate --noinput && python manage.py seed_demo
```

Start command:
```bash
gunicorn config.wsgi:application --log-file -
```

Production должен использовать PostgreSQL. При `DEBUG=False` проект не запустится без
`SECRET_KEY`, `ALLOWED_HOSTS` и `DATABASE_URL`.

`SERVE_MEDIA_FILES=True` — осознанный режим для малонагруженного demo: он поддерживает
byte-range для MP3. Для постоянных пользовательских загрузок нужно вынести `MEDIA_ROOT` в S3-совместимое
объектное хранилище.

### Release-check

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```
