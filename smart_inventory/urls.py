from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from inventory.views import google_login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/google/login/', google_login_view, name='accounts-google-login'),
    path('', include('inventory.urls')),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)