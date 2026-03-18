from django.contrib import admin
from django.urls import path, include
from inventory.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('inventory.urls')),   # APIs
    path('', dashboard),                       # ✅ homepage
    path('accounts/', include('allauth.urls')),  # Google login
]