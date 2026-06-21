import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

# Create a superuser or get one
user, created = User.objects.get_or_create(username='testadmin', is_superuser=True, is_staff=True)
if created:
    user.set_password('password')
    user.save()

client = Client()
client.force_login(user)

# Test GET /dashboard/fleet/categories/add/
response = client.get('/dashboard/fleet/categories/add/')
print("GET /add/ status:", response.status_code)
if response.status_code == 500:
    print("Error in GET /add/")

# Test GET /dashboard/fleet/categories/sprinter-van/edit/
response = client.get('/dashboard/fleet/categories/sprinter-van/edit/')
print("GET /edit/ status:", response.status_code)
if response.status_code == 500:
    print("Error in GET /edit/")
