from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EmployeeProfileViewSet,
    NotificationViewSet,
    ProductViewSet,
    SupplierViewSet,
    TransactionViewSet,
    WarehouseLocationViewSet,
    dashboard,
    dashboard_summary,
    employee_page,
    export_products_csv,
    export_transactions_csv,
    force_password_change_view,
    forgot_password_view,
    google_login_view,
    home,
    inventory_page,
    login_view,
    logout_view,
    low_stock,
    mark_notification_read,
    otp_login_view,
    register_view,
    settings_page,
    supplier_page,
    transaction_page,
    verify_otp_view,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'employees', EmployeeProfileViewSet, basename='employees')
router.register(r'locations', WarehouseLocationViewSet, basename='locations')
router.register(r'notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('verify-otp/', verify_otp_view, name='verify-otp'),
    path('otp-login/', otp_login_view, name='otp-login'),
    path('forgot-password/', forgot_password_view, name='forgot-password'),
    path('force-password-change/', force_password_change_view, name='force-password-change'),
    path('logout/', logout_view, name='logout'),
    path('auth/google/', google_login_view, name='google-login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('inventory/', inventory_page, name='inventory-page'),
    path('suppliers/', supplier_page, name='suppliers-page'),
    path('transactions/', transaction_page, name='transactions-page'),
    path('employees/', employee_page, name='employees-page'),
    path('settings/', settings_page, name='settings-page'),
    path('export/products/', export_products_csv, name='export-products'),
    path('export/transactions/', export_transactions_csv, name='export-transactions'),
    path('api/', include(router.urls)),
    path('api/dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('api/low-stock/', low_stock, name='low-stock'),
    path('api/notifications/<int:pk>/read/', mark_notification_read, name='notification-read'),
]