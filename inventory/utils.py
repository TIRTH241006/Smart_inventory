import random
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from .models import AuditLog, Company, EmployeeProfile, Notification, OTPCode, WarehouseLocation


OTP_PREVIEW_BACKENDS = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}


def generate_otp_code():
    return "".join(random.choices(string.digits, k=6))


def generate_temporary_password(length=12):
    alphabet = string.ascii_letters + string.digits + "@#%!"
    return "".join(random.choices(alphabet, k=length))


def unique_username_from_email(email):
    user_model = get_user_model()
    base = slugify((email or "user").split("@")[0]).replace("-", "") or "user"
    candidate = base
    counter = 1
    while user_model.objects.filter(username=candidate).exists():
        candidate = f"{base}{counter}"
        counter += 1
    return candidate[:150]


def unique_company_slug(name):
    base = slugify(name) or "company"
    candidate = base
    counter = 1
    while Company.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate[:220]


@transaction.atomic
def create_owner_company(user, company_name, full_name=""):
    company = Company.objects.create(
        name=company_name,
        slug=unique_company_slug(company_name),
        owner=user,
        notification_email=user.email,
    )
    EmployeeProfile.objects.update_or_create(
        user=user,
        defaults={
            "company": company,
            "role": EmployeeProfile.ROLE_OWNER,
            "full_name": full_name or user.get_full_name() or user.username,
            "can_manage_inventory": True,
            "can_manage_employees": True,
            "can_view_reports": True,
            "email_verified": user.is_active,
            "must_change_password": False,
        },
    )
    WarehouseLocation.objects.get_or_create(
        company=company,
        code="HQ",
        defaults={"name": "Main Warehouse", "location_type": WarehouseLocation.TYPE_WAREHOUSE, "is_default": True},
    )
    return company


def ensure_company_context(user):
    profile = getattr(user, "employee_profile", None)
    if profile:
        return profile

    company_name = f"{user.username} Workspace"
    company = Company.objects.create(
        name=company_name,
        slug=unique_company_slug(company_name),
        owner=user,
        notification_email=user.email,
    )
    profile = EmployeeProfile.objects.create(
        user=user,
        company=company,
        role=EmployeeProfile.ROLE_OWNER,
        full_name=user.get_full_name() or user.username,
        can_manage_inventory=True,
        can_manage_employees=True,
        can_view_reports=True,
        email_verified=user.is_active,
    )
    WarehouseLocation.objects.create(
        company=company,
        name="Main Warehouse",
        code="HQ",
        location_type=WarehouseLocation.TYPE_WAREHOUSE,
        is_default=True,
    )
    return profile


def get_default_location(company):
    location = company.locations.filter(is_default=True).first()
    return location or company.locations.first()


def should_preview_otp():
    return settings.DEBUG and settings.EMAIL_BACKEND in OTP_PREVIEW_BACKENDS


def otp_feedback_message(otp):
    if getattr(otp, "delivery_error", ""):
        return f"OTP generated, but email could not be sent: {otp.delivery_error}. Use this OTP for now: {otp.code}"
    if should_preview_otp():
        return f"Development mode OTP: {otp.code}"
    return "OTP sent to your email."


def send_branded_email(subject, recipient_list, template_name, context, *, fail_silently=False):
    context = {
        "app_name": "StockFlow AI",
        "support_email": settings.DEFAULT_FROM_EMAIL,
        **context,
    }
    text_body = render_to_string(f"emails/{template_name}.txt", context)
    html_body = render_to_string(f"emails/{template_name}.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=fail_silently)


def issue_otp(user, email, purpose):
    OTPCode.objects.filter(email=email, purpose=purpose, is_used=False).update(is_used=True)
    otp = OTPCode.objects.create(
        user=user,
        email=email,
        purpose=purpose,
        code=generate_otp_code(),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    otp.delivery_error = ""
    try:
        send_branded_email(
            subject=f"Your StockFlow OTP for {purpose.replace('_', ' ')}",
            recipient_list=[email],
            template_name="otp_code",
            context={
                "email": email,
                "otp_code": otp.code,
                "purpose": purpose.replace("_", " ").title(),
                "expires_minutes": 10,
            },
            fail_silently=False,
        )
    except Exception as exc:
        otp.delivery_error = str(exc)
    return otp


def verify_otp(email, purpose, code):
    otp = OTPCode.objects.filter(email=email, purpose=purpose, code=code, is_used=False).order_by("-created_at").first()
    if not otp or otp.is_expired:
        return None
    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return otp


def send_employee_invitation(company, email, username, temporary_password, full_name):
    send_branded_email(
        subject=f"You have been invited to {company.name}",
        recipient_list=[email],
        template_name="employee_invitation",
        context={
            "company_name": company.name,
            "full_name": full_name or username,
            "username": username,
            "temporary_password": temporary_password,
        },
        fail_silently=False,
    )


def create_audit_log(company, user, action, entity_type="", entity_id="", description="", metadata=None):
    return AuditLog.objects.create(
        company=company,
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id or ""),
        description=description,
        metadata=metadata or {},
    )


def create_notification(company, title, message, level=Notification.LEVEL_INFO, user=None, target_url=""):
    return Notification.objects.create(
        company=company,
        user=user,
        title=title,
        message=message,
        level=level,
        target_url=target_url,
    )


def notify_low_stock(product):
    company = product.company
    if not company:
        return
    create_notification(
        company=company,
        title="Low stock alert",
        message=f"{product.name} is below reorder level with {product.quantity} units remaining.",
        level=Notification.LEVEL_WARNING,
        target_url="/inventory/",
    )
    if company.low_stock_email_notifications:
        recipient = company.notification_email or getattr(company.owner, "email", "")
        if recipient:
            send_branded_email(
                subject=f"Low stock alert for {product.name}",
                recipient_list=[recipient],
                template_name="low_stock_alert",
                context={
                    "company_name": company.name,
                    "product_name": product.name,
                    "quantity": product.quantity,
                    "reorder_level": product.reorder_level,
                },
                fail_silently=False,
            )