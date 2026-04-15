import csv
import pdfplumber

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, IntegerField, Sum, Value
from django.db.models.functions import Coalesce
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.google.views import oauth2_login as google_oauth2_login
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .forms import (
    CompanySettingsForm,
    EmailAuthenticationForm,
    EmployeeInviteForm,
    ForcePasswordChangeForm,
    OTPRequestForm,
    OTPVerificationForm,
    OwnerRegistrationForm,
    PasswordResetOTPForm,
)
from .models import AuditLog, EmployeeProfile, Notification, Product, Supplier, Transaction, WarehouseLocation
from .permissions import CanManageEmployees, CanManageInventory, IsCompanyOwner
from .serializers import (
    AuditLogSerializer,
    EmployeeProfileSerializer,
    NotificationSerializer,
    ProductSerializer,
    SupplierSerializer,
    TransactionSerializer,
    WarehouseLocationSerializer,
)
from .utils import (
    create_audit_log,
    create_owner_company,
    ensure_company_context,
    generate_temporary_password,
    get_default_location,
    issue_otp,
    notify_low_stock,
    otp_feedback_message,
    send_employee_invitation,
    unique_username_from_email,
    verify_otp,
)


User = get_user_model()


def is_google_oauth_configured():
    provider_settings = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get("google", {})
    app_configs = provider_settings.get("APPS")
    if app_configs is None:
        app_config = provider_settings.get("APP")
        app_configs = [app_config] if app_config else []

    for app_config in app_configs:
        if app_config and app_config.get("client_id") and app_config.get("secret"):
            return True

    try:
        current_site = Site.objects.get_current()
        return SocialApp.objects.filter(provider="google", sites=current_site).exists()
    except (OperationalError, ProgrammingError, Site.DoesNotExist):
        return False


def get_user_profile(user):
    return ensure_company_context(user)


def get_company(user):
    return get_user_profile(user).company


def base_template_context(request):
    context = {"google_oauth_ready": is_google_oauth_configured()}
    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
        company = profile.company
        context.update(
            {
                "profile": profile,
                "company": company,
                "is_company_owner": profile.is_admin,
                "can_manage_inventory": profile.is_admin or profile.can_manage_inventory,
                "can_manage_employees": profile.is_admin or profile.can_manage_employees,
                "recent_notifications": company.notifications.filter(is_read=False)[:5],
            }
        )
    return context


def render_page(request, template_name, context=None):
    merged = base_template_context(request)
    merged.update(context or {})
    return render(request, template_name, merged)


def owner_required(request):
    profile = get_user_profile(request.user)
    if profile.is_admin:
        return None
    messages.error(request, "Only company admins can access that section.")
    return redirect("dashboard")


@require_http_methods(["GET", "POST"])
def google_login_view(request):
    if not is_google_oauth_configured():
        messages.error(
            request,
            "Google login is not configured yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your environment, or create a Google SocialApp in Django admin.",
        )
        return redirect("login")
    return google_oauth2_login(request)


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
        if profile.must_change_password:
            return redirect("force-password-change")
        return redirect("dashboard")

    form = EmailAuthenticationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["email"].strip()
        password = form.cleaned_data["password"]
        email_matches = list(User.objects.filter(email__iexact=identifier).order_by("id"))
        username_match = User.objects.filter(username__iexact=identifier).first()

        matched_user = None
        if email_matches:
            matched_user = next(
                (
                    user
                    for user in email_matches
                    if user.has_usable_password() and not SocialAccount.objects.filter(user=user, provider="google").exists()
                ),
                email_matches[0],
            )
        elif username_match:
            matched_user = username_match

        if matched_user and SocialAccount.objects.filter(user=matched_user, provider="google").exists():
            messages.error(request, "This account uses Google sign-in. Continue with Google to access it.")
            return render_page(request, "login.html", {"form": form})
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            messages.error(request, "Invalid email/username or password.")
        elif not user.is_active:
            request.session["pending_signup_email"] = user.email
            messages.warning(request, "Your account is not verified yet. Enter the OTP sent to your email.")
            return redirect("verify-otp")
        else:
            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
            profile = get_user_profile(user)
            create_audit_log(profile.company, user, "login", "auth", user.id, "User signed in with password")
            if profile.must_change_password:
                return redirect("force-password-change")
            return redirect("dashboard")

    return render_page(request, "login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = OwnerRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = unique_username_from_email(form.cleaned_data["email"])
        full_name = form.cleaned_data["full_name"].strip()
        user = User.objects.create(
            username=username,
            email=form.cleaned_data["email"],
            is_active=False,
            first_name=full_name.split(" ")[0],
            last_name=" ".join(full_name.split(" ")[1:]),
        )
        user.set_password(form.cleaned_data["password1"])
        user.save()

        company = create_owner_company(user, form.cleaned_data["company_name"], full_name=full_name)
        otp = issue_otp(user, user.email, "signup")
        request.session["pending_signup_email"] = user.email
        request.session["pending_signup_company_id"] = company.id
        messages.success(request, f"Verification OTP generated. {otp_feedback_message(otp)} Enter it to activate your company admin workspace.")
        return redirect("verify-otp")

    return render_page(request, "register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_otp_view(request):
    pending_email = request.session.get("pending_signup_email")
    if not pending_email:
        messages.info(request, "Start admin signup or OTP login first.")
        return redirect("register")

    form = OTPVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        otp = verify_otp(pending_email, "signup", form.cleaned_data["code"])
        if not otp:
            messages.error(request, "The OTP is invalid or expired.")
        else:
            user = otp.user or User.objects.filter(email__iexact=pending_email).first()
            if user is None:
                messages.error(request, "No account was found for this OTP.")
                return redirect("register")
            user.is_active = True
            user.save(update_fields=["is_active"])
            profile = get_user_profile(user)
            profile.email_verified = True
            profile.save(update_fields=["email_verified", "updated_at"])
            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
            create_audit_log(profile.company, user, "signup_verified", "user", user.id, "Admin verified manual signup")
            request.session.pop("pending_signup_email", None)
            request.session.pop("pending_signup_company_id", None)
            messages.success(request, "Your company admin workspace is now active.")
            return redirect("dashboard")

    return render_page(request, "otp_verification.html", {"form": form, "pending_email": pending_email, "otp_mode": "signup"})


@require_http_methods(["GET", "POST"])
def otp_login_view(request):
    request_form = OTPRequestForm()
    verify_form = OTPVerificationForm()
    pending_email = request.session.get("pending_login_email")

    if request.method == "POST":
        step = request.POST.get("step", "request")
        if step == "request":
            request_form = OTPRequestForm(request.POST)
            if request_form.is_valid():
                email = request_form.cleaned_data["email"].strip().lower()
                user = User.objects.filter(email__iexact=email, is_active=True).first()
                if not user:
                    messages.error(request, "No active account found for that email.")
                else:
                    otp = issue_otp(user, email, "login")
                    request.session["pending_login_email"] = email
                    pending_email = email
                    messages.success(request, otp_feedback_message(otp))
        else:
            verify_form = OTPVerificationForm(request.POST)
            pending_email = request.session.get("pending_login_email")
            if verify_form.is_valid() and pending_email:
                otp = verify_otp(pending_email, "login", verify_form.cleaned_data["code"])
                if not otp or not otp.user:
                    messages.error(request, "The OTP is invalid or expired.")
                else:
                    login(request, otp.user, backend=settings.AUTHENTICATION_BACKENDS[0])
                    profile = get_user_profile(otp.user)
                    create_audit_log(profile.company, otp.user, "otp_login", "auth", otp.user.id, "User signed in with OTP")
                    request.session.pop("pending_login_email", None)
                    if profile.must_change_password:
                        return redirect("force-password-change")
                    return redirect("dashboard")

    return render_page(
        request,
        "otp_login.html",
        {"request_form": request_form, "verify_form": verify_form, "pending_email": pending_email},
    )


@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    request_form = OTPRequestForm()
    reset_form = PasswordResetOTPForm()
    pending_email = request.session.get("pending_password_reset_email")

    if request.method == "POST":
        step = request.POST.get("step", "request")
        if step == "request":
            request_form = OTPRequestForm(request.POST)
            if request_form.is_valid():
                email = request_form.cleaned_data["email"].strip().lower()
                user = User.objects.filter(email__iexact=email, is_active=True).first()
                if not user:
                    messages.error(request, "No active account found for that email.")
                else:
                    otp = issue_otp(user, email, "password_reset")
                    request.session["pending_password_reset_email"] = email
                    pending_email = email
                    messages.success(request, otp_feedback_message(otp))
        else:
            reset_form = PasswordResetOTPForm(request.POST)
            pending_email = request.session.get("pending_password_reset_email")
            if reset_form.is_valid() and pending_email:
                otp = verify_otp(pending_email, "password_reset", reset_form.cleaned_data["code"])
                if not otp or not otp.user:
                    messages.error(request, "The OTP is invalid or expired.")
                else:
                    otp.user.set_password(reset_form.cleaned_data["password1"])
                    otp.user.save(update_fields=["password"])
                    profile = get_user_profile(otp.user)
                    profile.must_change_password = False
                    profile.save(update_fields=["must_change_password", "updated_at"])
                    create_audit_log(profile.company, otp.user, "password_reset", "auth", otp.user.id, "Password reset with OTP")
                    request.session.pop("pending_password_reset_email", None)
                    messages.success(request, "Password updated. You can now sign in.")
                    return redirect("login")

    return render_page(
        request,
        "forgot_password.html",
        {"request_form": request_form, "reset_form": reset_form, "pending_email": pending_email},
    )


@login_required
def force_password_change_view(request):
    profile = get_user_profile(request.user)
    form = ForcePasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password", "updated_at"])
        create_audit_log(profile.company, request.user, "password_changed", "auth", request.user.id, "Forced password change completed")
        messages.success(request, "Password updated successfully.")
        return redirect("dashboard")
    return render_page(request, "force_password_change.html", {"form": form})


@login_required
def logout_view(request):
    profile = get_user_profile(request.user)
    create_audit_log(profile.company, request.user, "logout", "auth", request.user.id, "User logged out")
    logout(request)
    messages.info(
        request,
        "You have been logged out. Google sign-in will ask you to choose an account again before continuing.",
    )
    return redirect("home")


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render_page(request, "home.html")


@login_required
def dashboard(request):
    return render_page(request, "dashboard.html")


@login_required
def inventory_page(request):
    return render_page(request, "inventory.html")


@login_required
def supplier_page(request):
    return render_page(request, "suppliers.html")


@login_required
def transaction_page(request):
    return render_page(request, "transactions.html")


@login_required
def employee_page(request):
    guard = owner_required(request)
    if guard:
        return guard

    profile = get_user_profile(request.user)
    company = profile.company
    search = request.GET.get("search", "").strip()
    employees = company.employees.select_related("user").all()
    if search:
        employees = employees.filter(full_name__icontains=search) | employees.filter(user__email__icontains=search)

    invite_form = EmployeeInviteForm(request.POST or None)
    if request.method == "POST" and invite_form.is_valid():
        email = invite_form.cleaned_data["email"].strip().lower()
        username = unique_username_from_email(email)
        temporary_password = generate_temporary_password()
        user = User.objects.create_user(username=username, email=email, password=temporary_password, is_active=True)
        EmployeeProfile.objects.create(
            user=user,
            company=company,
            role=EmployeeProfile.ROLE_EMPLOYEE,
            full_name=invite_form.cleaned_data["full_name"],
            job_title=invite_form.cleaned_data["job_title"],
            can_manage_inventory=invite_form.cleaned_data["can_manage_inventory"],
            can_manage_employees=False,
            can_view_reports=invite_form.cleaned_data["can_view_reports"],
            must_change_password=True,
            email_verified=True,
        )
        send_employee_invitation(company, email, username, temporary_password, invite_form.cleaned_data["full_name"])
        create_audit_log(company, request.user, "employee_invited", "employee", user.id, f"Invited employee {email}")
        messages.success(request, f"Employee invited successfully. Temporary password sent to {email}.")
        return redirect("employees-page")

    return render_page(
        request,
        "employees.html",
        {
            "employees": employees.order_by("full_name", "user__username"),
            "invite_form": invite_form,
            "search": search,
        },
    )


@login_required
def settings_page(request):
    guard = owner_required(request)
    if guard:
        return guard
    company = get_company(request.user)
    form = CompanySettingsForm(request.POST or None, instance=company)
    if request.method == "POST" and form.is_valid():
        updated_company = form.save()
        create_audit_log(updated_company, request.user, "company_settings_updated", "company", updated_company.id)
        messages.success(request, "Company settings updated.")
        return redirect("settings-page")
    return render_page(request, "settings.html", {"form": form})


class CompanyScopedViewSet(viewsets.ModelViewSet):
    company_field_name = "company"

    def current_profile(self):
        return get_user_profile(self.request.user)

    def current_company(self):
        return self.current_profile().company

    def filter_by_company(self, queryset):
        return queryset.filter(**{self.company_field_name: self.current_company()})


class ProductViewSet(CompanyScopedViewSet):
    queryset = Product.objects.select_related("supplier", "location").all()
    serializer_class = ProductSerializer
    search_fields = ["name", "category", "sku", "location__name"]
    ordering_fields = ["name", "category", "quantity", "price", "created_at"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [CanManageInventory()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = self.filter_by_company(Product.objects.select_related("supplier", "location").all())
        category = self.request.query_params.get("category")
        low_stock_only = self.request.query_params.get("low_stock")
        if category:
            queryset = queryset.filter(category__iexact=category)
        if low_stock_only in {"true", "1"}:
            queryset = queryset.filter(quantity__lte=F("reorder_level"))
        return queryset

    def perform_create(self, serializer):
        company = self.current_company()
        location = serializer.validated_data.get("location") or get_default_location(company)
        product = serializer.save(company=company, location=location)
        create_audit_log(company, self.request.user, "product_created", "product", product.id, f"Created {product.name}")
        if product.is_low_stock:
            notify_low_stock(product)

    def perform_update(self, serializer):
        product = serializer.save()
        create_audit_log(product.company, self.request.user, "product_updated", "product", product.id, f"Updated {product.name}")
        if product.is_low_stock:
            notify_low_stock(product)

    def perform_destroy(self, instance):
        profile = self.current_profile()
        if not profile.is_admin:
            raise permissions.PermissionDenied("Only company admins can delete products.")
        create_audit_log(instance.company, self.request.user, "product_deleted", "product", instance.id, f"Deleted {instance.name}")
        instance.delete()


class SupplierViewSet(CompanyScopedViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ["name", "contact_person", "email", "phone"]
    ordering_fields = ["name", "created_at"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsCompanyOwner()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return self.filter_by_company(Supplier.objects.all())

    def perform_create(self, serializer):
        supplier = serializer.save(company=self.current_company())
        create_audit_log(supplier.company, self.request.user, "supplier_created", "supplier", supplier.id, f"Created {supplier.name}")

    def perform_update(self, serializer):
        supplier = serializer.save()
        create_audit_log(supplier.company, self.request.user, "supplier_updated", "supplier", supplier.id, f"Updated {supplier.name}")

    def perform_destroy(self, instance):
        create_audit_log(instance.company, self.request.user, "supplier_deleted", "supplier", instance.id, f"Deleted {instance.name}")
        instance.delete()


class TransactionViewSet(CompanyScopedViewSet):
    queryset = Transaction.objects.select_related("product", "location", "performed_by").all()
    serializer_class = TransactionSerializer
    search_fields = ["product__name", "note", "performed_by__username", "location__name"]
    ordering_fields = ["date", "quantity"]

    def get_permissions(self):
        if self.action in {"create"}:
            return [CanManageInventory()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = self.filter_by_company(Transaction.objects.select_related("product", "location", "performed_by").all())
        tx_type = self.request.query_params.get("type")
        if tx_type in {Transaction.STOCK_IN, Transaction.STOCK_OUT}:
            queryset = queryset.filter(transaction_type=tx_type)
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        company = self.current_company()
        product = serializer.validated_data["product"]
        if product.company_id != company.id:
            raise permissions.PermissionDenied("Product does not belong to your company.")

        location = serializer.validated_data.get("location") or product.location or get_default_location(company)
        transaction_obj = serializer.save(company=company, performed_by=self.request.user, location=location)
        
        # Handle PDF invoice extraction for STOCK_IN
        if transaction_obj.transaction_type == Transaction.STOCK_IN and transaction_obj.invoice_pdf:
            try:
                with pdfplumber.open(transaction_obj.invoice_pdf.path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                    if text.strip():
                        # Extract supplier info or append to note
                        extracted_info = f"Invoice content: {text[:500]}..."  # Limit to 500 chars
                        if transaction_obj.note:
                            transaction_obj.note += f" | {extracted_info}"
                        else:
                            transaction_obj.note = extracted_info
                        transaction_obj.save(update_fields=['note'])
            except Exception as e:
                # Log error but don't fail the transaction
                print(f"Error extracting PDF: {e}")

        product = Product.objects.select_for_update().get(pk=transaction_obj.product_id)

        if transaction_obj.transaction_type == Transaction.STOCK_IN:
            product.quantity += transaction_obj.quantity
        else:
            if product.quantity < transaction_obj.quantity:
                raise ValueError("Insufficient stock for this Stock OUT transaction.")
            product.quantity -= transaction_obj.quantity

        if transaction_obj.location and product.location_id != transaction_obj.location_id:
            product.location = transaction_obj.location
        product.save()
        create_audit_log(
            company,
            self.request.user,
            "stock_transaction",
            "transaction",
            transaction_obj.id,
            f"{transaction_obj.transaction_type} {transaction_obj.quantity} units for {product.name}",
        )
        if product.is_low_stock:
            notify_low_stock(product)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class EmployeeProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmployeeProfileSerializer
    permission_classes = [CanManageEmployees]
    search_fields = ["full_name", "user__email", "user__username", "job_title"]
    ordering_fields = ["full_name", "created_at"]

    def get_queryset(self):
        company = get_company(self.request.user)
        return EmployeeProfile.objects.select_related("user", "company").filter(company=company)


class WarehouseLocationViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseLocationSerializer
    search_fields = ["name", "code"]
    ordering_fields = ["name", "location_type"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsCompanyOwner()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        company = get_company(self.request.user)
        return WarehouseLocation.objects.filter(company=company)

    def perform_create(self, serializer):
        location = serializer.save(company=get_company(self.request.user))
        create_audit_log(location.company, self.request.user, "location_created", "location", location.id, f"Created {location.name}")


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        company = get_company(self.request.user)
        queryset = Notification.objects.filter(company=company)
        if not get_user_profile(self.request.user).is_admin:
            queryset = queryset.filter(user__in=[None, self.request.user])
        return queryset


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    profile = get_user_profile(request.user)
    company = profile.company
    products = Product.objects.filter(company=company)
    transactions = Transaction.objects.filter(company=company)
    employees = EmployeeProfile.objects.filter(company=company, is_active_employee=True)
    low_stock_qs = products.filter(quantity__lte=F("reorder_level"))
    recent_transactions = transactions.select_related("product", "performed_by")[:8]
    aggregates = products.aggregate(
        total_units=Coalesce(Sum("quantity"), Value(0), output_field=IntegerField()),
        inventory_value=Coalesce(
            Sum(ExpressionWrapper(F("quantity") * F("price"), output_field=DecimalField(max_digits=16, decimal_places=2))),
            Value(0, output_field=DecimalField(max_digits=16, decimal_places=2)),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        ),
    )

    return Response(
        {
            "total_products": products.count(),
            "low_stock_items": low_stock_qs.count(),
            "total_transactions": transactions.count(),
            "total_employees": employees.count(),
            "active_suppliers": Supplier.objects.filter(company=company).count(),
            "total_units": aggregates["total_units"],
            "inventory_value": float(aggregates["inventory_value"]),
            "low_stock_products": ProductSerializer(low_stock_qs[:6], many=True).data,
            "recent_transactions": TransactionSerializer(recent_transactions, many=True).data,
            "recent_activity": AuditLogSerializer(company.audit_logs.select_related("user")[:8], many=True).data,
            "notifications": NotificationSerializer(company.notifications.filter(is_read=False)[:5], many=True).data,
            "category_distribution": list(products.values("category").order_by("category").annotate(total=Count("id"))),
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def low_stock(request):
    company = get_company(request.user)
    low_products = Product.objects.filter(company=company, quantity__lte=F("reorder_level"))
    serializer = ProductSerializer(low_products, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, pk):
    company = get_company(request.user)
    notification = get_object_or_404(Notification, pk=pk, company=company)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return Response({"status": "ok"})


@login_required
def export_products_csv(request):
    company = get_company(request.user)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="products.csv"'
    writer = csv.writer(response)
    writer.writerow(["Name", "SKU", "Category", "Quantity", "Price", "Reorder Level", "Location", "Supplier"])
    for product in Product.objects.select_related("supplier", "location").filter(company=company):
        writer.writerow(
            [
                product.name,
                product.sku,
                product.category,
                product.quantity,
                product.price,
                product.reorder_level,
                product.location.name if product.location else "",
                product.supplier.name if product.supplier else "",
            ]
        )
    return response


@login_required
def export_transactions_csv(request):
    company = get_company(request.user)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(["Product", "Type", "Quantity", "Location", "Note", "By", "Created At"])
    for tx in Transaction.objects.select_related("product", "performed_by", "location").filter(company=company):
        writer.writerow(
            [
                tx.product.name,
                tx.transaction_type,
                tx.quantity,
                tx.location.name if tx.location else "",
                tx.note,
                tx.performed_by.username if tx.performed_by else "",
                tx.date,
            ]
        )
    return response