from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


class StockFlowSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = (sociallogin.user.email or sociallogin.account.extra_data.get("email") or "").strip().lower()
        if not email:
            return

        user_model = get_user_model()
        matching_users = list(user_model.objects.filter(email__iexact=email).order_by("id"))
        existing_user = matching_users[0] if matching_users else None
        if existing_user is None:
            return

        if len(matching_users) > 1:
            messages.error(
                request,
                "This email is linked to multiple accounts. Google login has been blocked for safety. Use the original account method and remove the duplicate account.",
            )
            raise ImmediateHttpResponse(redirect("login"))

        if sociallogin.is_existing:
            return

        existing_social = SocialAccount.objects.filter(user=existing_user, provider=sociallogin.account.provider).exists()
        if existing_social:
            return

        messages.error(
            request,
            "This email is already registered with email/password login. Please use the same sign-in method used when the account was created.",
        )
        raise ImmediateHttpResponse(redirect("login"))