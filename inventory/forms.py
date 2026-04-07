from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm

from allauth.socialaccount.forms import SignupForm

from .models import Company, EmployeeProfile
from .utils import create_owner_company


def styled_text_input(placeholder="", input_type="text", autocomplete="off"):
    attrs = {"class": "input", "placeholder": placeholder}
    if autocomplete:
        attrs["autocomplete"] = autocomplete
    if input_type == "password":
        return forms.PasswordInput(attrs=attrs)
    if input_type == "email":
        attrs["inputmode"] = "email"
        return forms.EmailInput(attrs=attrs)
    if input_type == "number":
        return forms.NumberInput(attrs=attrs)
    return forms.TextInput(attrs=attrs)


def styled_checkbox():
    return forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-slate-600 bg-slate-900 text-cyan-400"})


class OwnerRegistrationForm(forms.Form):
    company_name = forms.CharField(max_length=180, widget=styled_text_input("Company name", autocomplete="organization"))
    full_name = forms.CharField(max_length=160, widget=styled_text_input("Full name", autocomplete="name"))
    email = forms.EmailField(widget=styled_text_input("you@company.com", input_type="email", autocomplete="email"))
    password1 = forms.CharField(widget=styled_text_input("Create password", input_type="password", autocomplete="new-password"))
    password2 = forms.CharField(widget=styled_text_input("Confirm password", input_type="password", autocomplete="new-password"))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data


class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(label="Email", widget=styled_text_input("Email or username", input_type="email", autocomplete="username"))
    password = forms.CharField(widget=styled_text_input("Password", input_type="password", autocomplete="current-password"))


class OTPRequestForm(forms.Form):
    email = forms.EmailField(widget=styled_text_input("Enter your account email", input_type="email", autocomplete="email"))


class OTPVerificationForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6, widget=styled_text_input("6-digit code", autocomplete="one-time-code"))


class PasswordResetOTPForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6, widget=styled_text_input("6-digit code", autocomplete="one-time-code"))
    password1 = forms.CharField(widget=styled_text_input("New password", input_type="password", autocomplete="new-password"))
    password2 = forms.CharField(widget=styled_text_input("Confirm new password", input_type="password", autocomplete="new-password"))

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data


class ForcePasswordChangeForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields["new_password1"].widget.attrs.update({"class": "input", "placeholder": "New password", "autocomplete": "new-password"})
        self.fields["new_password2"].widget.attrs.update({"class": "input", "placeholder": "Confirm new password", "autocomplete": "new-password"})


class EmployeeInviteForm(forms.Form):
    full_name = forms.CharField(max_length=160, widget=styled_text_input("Employee full name", autocomplete="name"))
    email = forms.EmailField(widget=styled_text_input("employee@company.com", input_type="email", autocomplete="email"))
    job_title = forms.CharField(max_length=120, required=False, widget=styled_text_input("Job title", autocomplete="organization-title"))
    can_manage_inventory = forms.BooleanField(required=False, initial=True, widget=styled_checkbox())
    can_manage_employees = forms.BooleanField(required=False, widget=styled_checkbox())
    can_view_reports = forms.BooleanField(required=False, initial=True, widget=styled_checkbox())


class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "notification_email", "low_stock_email_notifications", "dark_mode_enabled"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Company name", "autocomplete": "organization"}),
            "notification_email": forms.EmailInput(attrs={"class": "input", "placeholder": "alerts@company.com", "autocomplete": "email"}),
            "low_stock_email_notifications": styled_checkbox(),
            "dark_mode_enabled": styled_checkbox(),
        }


class CompanySocialSignupForm(SignupForm):
    company_name = forms.CharField(max_length=180, widget=styled_text_input("Company name", autocomplete="organization"))
    full_name = forms.CharField(max_length=160, required=False, widget=styled_text_input("Full name", autocomplete="name"))

    def save(self, request):
        user = super().save(request)
        full_name = self.cleaned_data.get("full_name")
        if full_name:
            user.first_name = full_name.split(" ")[0]
            user.last_name = " ".join(full_name.split(" ")[1:])
            user.save(update_fields=["first_name", "last_name"])
        create_owner_company(user, self.cleaned_data["company_name"], full_name=full_name or user.get_full_name())
        return user