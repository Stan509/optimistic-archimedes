#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "Waiting for database..."
python -c "
import socket
import time
import sys
import os
import urllib.parse

db_url = os.environ.get('DATABASE_URL')
if not db_url or not (db_url.startswith('postgres://') or db_url.startswith('postgresql://')):
    print('No PostgreSQL database URL found or using SQLite. Skipping wait.')
    sys.exit(0)

url = urllib.parse.urlparse(db_url)
host = url.hostname
port = url.port or 5432

print(f'Waiting for database connection on {host}:{port}...')
retries = 0
max_retries = 30
while retries < max_retries:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, port))
        s.close()
        print('Database is ready!')
        break
    except socket.error as e:
        retries += 1
        if retries >= max_retries:
            print(f'Could not connect to database after {max_retries} attempts. Proceeding anyway...')
            break
        time.sleep(1)
"

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Seeding initial database data..."
python manage.py seed_data

# Copy local media to Spaces if configured
if [ -n "$DO_SPACES_KEY" ] && [ -d "/app/media" ]; then
    echo "Syncing local media files to DigitalOcean Spaces..."
    python manage.py sync_media_to_spaces || echo "Media sync skipped (non-fatal)"
fi

echo "Starting Gunicorn server..."
exec gunicorn hotel_project.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
