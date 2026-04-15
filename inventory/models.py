from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=180, unique=True)
    slug = models.SlugField(max_length=220, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="owned_companies",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    notification_email = models.EmailField(blank=True)
    low_stock_email_notifications = models.BooleanField(default=True)
    dark_mode_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class EmployeeProfile(models.Model):
    ROLE_OWNER = "owner"
    ROLE_EMPLOYEE = "employee"
    ROLE_CHOICES = (
        (ROLE_OWNER, "Admin"),
        (ROLE_EMPLOYEE, "Employee"),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="employee_profile", on_delete=models.CASCADE)
    company = models.ForeignKey(Company, related_name="employees", on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)
    full_name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    can_manage_inventory = models.BooleanField(default=True)
    can_manage_employees = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    is_active_employee = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["full_name", "user__username"]
        indexes = [models.Index(fields=["company", "role"])]

    def __str__(self):
        return self.full_name or self.user.get_username()

    @property
    def is_owner(self):
        return self.role == self.ROLE_OWNER

    @property
    def is_admin(self):
        return self.is_owner or (self.can_manage_inventory and self.can_manage_employees and self.can_view_reports)


class WarehouseLocation(models.Model):
    TYPE_WAREHOUSE = "warehouse"
    TYPE_STORE = "store"
    TYPE_ROOM = "room"
    TYPE_CHOICES = (
        (TYPE_WAREHOUSE, "Warehouse"),
        (TYPE_STORE, "Store"),
        (TYPE_ROOM, "Room"),
    )

    company = models.ForeignKey(Company, related_name="locations", on_delete=models.CASCADE)
    name = models.CharField(max_length=140)
    code = models.CharField(max_length=50)
    location_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_WAREHOUSE)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]
        unique_together = [("company", "code")]
        indexes = [models.Index(fields=["company", "name"])]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Supplier(models.Model):
    company = models.ForeignKey(Company, related_name="suppliers", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["company", "name"])]
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="unique_supplier_name_per_company")]

    def __str__(self):
        return self.name


class Product(models.Model):
    company = models.ForeignKey(Company, related_name="products", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, db_index=True)
    location = models.ForeignKey(
        WarehouseLocation,
        related_name="products",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    supplier = models.ForeignKey(
        Supplier,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    reorder_level = models.IntegerField(default=5)
    sku = models.CharField(max_length=64, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "sku"], name="unique_product_sku_per_company")]
        indexes = [
            models.Index(fields=["company", "name"]),
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["quantity", "reorder_level"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level


class Transaction(models.Model):
    STOCK_IN = "IN"
    STOCK_OUT = "OUT"
    TRANSACTION_TYPE = (
        (STOCK_IN, "Stock In"),
        (STOCK_OUT, "Stock Out"),
    )

    company = models.ForeignKey(Company, related_name="transactions", null=True, blank=True, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="transactions", on_delete=models.CASCADE)
    location = models.ForeignKey(
        WarehouseLocation,
        related_name="transactions",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    quantity = models.IntegerField()
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPE)
    note = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="inventory_transactions",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["transaction_type", "date"]),
            models.Index(fields=["product", "date"]),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.transaction_type} ({self.quantity})"


class OTPCode(models.Model):
    PURPOSE_SIGNUP = "signup"
    PURPOSE_LOGIN = "login"
    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_CHOICES = (
        (PURPOSE_SIGNUP, "Signup Verification"),
        (PURPOSE_LOGIN, "Passwordless Login"),
        (PURPOSE_PASSWORD_RESET, "Password Reset"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="otp_codes", null=True, blank=True, on_delete=models.CASCADE)
    email = models.EmailField()
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "purpose", "is_used"])]

    def __str__(self):
        return f"{self.email} - {self.purpose}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class AuditLog(models.Model):
    company = models.ForeignKey(Company, related_name="audit_logs", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="audit_logs", null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "created_at"])]

    def __str__(self):
        return f"{self.action} - {self.company.name}"


class Notification(models.Model):
    LEVEL_INFO = "info"
    LEVEL_WARNING = "warning"
    LEVEL_CRITICAL = "critical"
    LEVEL_CHOICES = (
        (LEVEL_INFO, "Info"),
        (LEVEL_WARNING, "Warning"),
        (LEVEL_CRITICAL, "Critical"),
    )

    company = models.ForeignKey(Company, related_name="notifications", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notifications", null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    message = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    target_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "is_read", "created_at"])]

    def __str__(self):
        return self.title