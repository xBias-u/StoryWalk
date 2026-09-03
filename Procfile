release: python manage.py migrate --noinput && python manage.py seed_demo
web: gunicorn config.wsgi:application --access-logfile - --error-logfile -
