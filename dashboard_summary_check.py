import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_inventory.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from inventory.views import dashboard_summary

User = get_user_model()
user = User.objects.filter(username='gsfc_admin').first()
print('user exists:', bool(user))
if not user:
    raise SystemExit(1)

factory = APIRequestFactory()
request = factory.get('/api/dashboard/summary/')
request.user = user
response = dashboard_summary(request)
print('status:', response.status_code)
print('data keys:', list(response.data.keys()))
print('category_distribution:', response.data.get('category_distribution'))
print('stock_status_distribution:', response.data.get('stock_status_distribution'))
print('transaction_distribution:', response.data.get('transaction_distribution'))
print('supplier_distribution:', response.data.get('supplier_distribution'))
