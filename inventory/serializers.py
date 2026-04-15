from rest_framework import serializers
from .models import AuditLog, Company, EmployeeProfile, Notification, Product, Supplier, Transaction, WarehouseLocation


class CompanySerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "slug",
            "owner",
            "owner_username",
            "notification_email",
            "low_stock_email_notifications",
            "dark_mode_enabled",
        ]


class WarehouseLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseLocation
        fields = ["id", "name", "code", "location_type", "description", "is_default"]


class EmployeeProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "phone",
            "job_title",
            "role",
            "can_manage_inventory",
            "can_manage_employees",
            "can_view_reports",
            "must_change_password",
            "email_verified",
            "is_active_employee",
        ]


class ProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "location",
            "location_name",
            "supplier",
            "supplier_name",
            "quantity",
            "price",
            "reorder_level",
            "sku",
            "is_active",
            "is_low_stock",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        qty = attrs.get("quantity", getattr(self.instance, "quantity", 0))
        reorder = attrs.get("reorder_level", getattr(self.instance, "reorder_level", 0))
        if reorder < 0 or qty < 0:
            raise serializers.ValidationError("Quantity and reorder level must be non-negative.")
        return attrs


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "email", "phone", "address", "created_at", "updated_at"]


class TransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    performed_by_username = serializers.CharField(source="performed_by.username", read_only=True)
    created_at = serializers.DateTimeField(source="date", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "product",
            "product_name",
            "location",
            "location_name",
            "quantity",
            "transaction_type",
            "note",
            "invoice_pdf",
            "performed_by",
            "performed_by_username",
            "created_at",
        ]
        read_only_fields = ["performed_by"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Transaction quantity must be greater than zero.")
        return value


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "level", "target_url", "is_read", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "action", "entity_type", "entity_id", "description", "actor", "metadata", "created_at"]
