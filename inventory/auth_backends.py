from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from allauth.socialaccount.models import SocialAccount


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email")
        if not identifier or not password:
            return None

        user_model = get_user_model()
        user = user_model._default_manager.filter(username__iexact=identifier).first()
        if user is None:
            email_matches = list(user_model._default_manager.filter(email__iexact=identifier).order_by("id"))
            user = next(
                (
                    candidate
                    for candidate in email_matches
                    if candidate.has_usable_password()
                    and not SocialAccount.objects.filter(user=candidate, provider="google").exists()
                ),
                email_matches[0] if email_matches else None,
            )
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None