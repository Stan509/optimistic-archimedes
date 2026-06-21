import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
import traceback

user, _ = User.objects.get_or_create(username='testadmin', is_superuser=True, is_staff=True)
client = Client()
client.force_login(user)

try:
    response = client.post('/dashboard/fleet/categories/add/', {
        'name': 'Test Category',
        'description': 'Test Description',
        'passengers_capacity': '4',
        'luggage_capacity': '2',
        'order': '1'
    })
    print("POST /add/ status:", response.status_code)
except Exception as e:
    print("Crash during POST /add/!")
    traceback.print_exc()

