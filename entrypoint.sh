#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "Waiting for PostgreSQL database..."
python -c "
import socket
import time
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect(('db', 5432))
        s.close()
        break
    except socket.error:
        time.sleep(0.1)
"
echo "PostgreSQL is ready!"

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn server..."
exec gunicorn hotel_project.wsgi:application --bind 0.0.0.0:8000 --workers 3
