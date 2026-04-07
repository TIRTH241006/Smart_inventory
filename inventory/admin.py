from django.contrib import admin
from .models import AuditLog, Company, EmployeeProfile, Notification, OTPCode, Product, Supplier, Transaction, WarehouseLocation


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
	list_display = ("name", "owner", "notification_email", "low_stock_email_notifications", "created_at")
	search_fields = ("name", "slug", "owner__username", "owner__email")


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
	list_display = ("user", "company", "role", "can_manage_inventory", "can_manage_employees", "must_change_password")
	list_filter = ("role", "can_manage_inventory", "can_manage_employees", "must_change_password")
	search_fields = ("user__username", "user__email", "full_name", "company__name")


@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
	list_display = ("name", "company", "code", "location_type", "is_default")
	list_filter = ("location_type", "is_default")
	search_fields = ("name", "code", "company__name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ("name", "company", "sku", "category", "quantity", "reorder_level", "price", "location", "is_active")
	list_filter = ("company", "category", "is_active")
	search_fields = ("name", "sku", "company__name")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
	list_display = ("name", "company", "contact_person", "email", "phone")
	search_fields = ("name", "company__name", "contact_person", "email")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
	list_display = ("company", "product", "transaction_type", "quantity", "location", "performed_by", "date")
	list_filter = ("company", "transaction_type", "date")
	search_fields = ("product__name", "note", "performed_by__username")


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
	list_display = ("email", "purpose", "code", "expires_at", "is_used")
	list_filter = ("purpose", "is_used")
	search_fields = ("email", "user__username")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
	list_display = ("company", "action", "entity_type", "user", "created_at")
	list_filter = ("company", "action", "entity_type")
	search_fields = ("company__name", "user__username", "description")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	list_display = ("company", "title", "level", "user", "is_read", "created_at")
	list_filter = ("company", "level", "is_read")
	search_fields = ("company__name", "title", "message")