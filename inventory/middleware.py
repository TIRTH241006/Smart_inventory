from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_prefixes = (
            "/static/",
            "/logout/",
            "/admin/",
            "/otp-login/",
            "/forgot-password/",
            "/reset-password/",
            "/verify-otp/",
            "/force-password-change/",
        )

    def __call__(self, request):
        if request.user.is_authenticated and not request.path.startswith(self.exempt_prefixes):
            profile = getattr(request.user, "employee_profile", None)
            if profile and profile.must_change_password:
                allowed = {reverse("force-password-change")}
                if request.path not in allowed:
                    return redirect("force-password-change")
        return self.get_response(request)
