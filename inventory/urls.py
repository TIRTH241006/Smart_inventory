from django.urls import path, include
from .views import dashboard
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, SupplierViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'transactions', TransactionViewSet)

urlpatterns = [
    path('', dashboard),  # frontend
    path('api/', include(router.urls)),  # backend APIs
]