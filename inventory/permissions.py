from rest_framework import permissions


def get_profile(user):
    return getattr(user, "employee_profile", None)


class IsCompanyOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        profile = get_profile(request.user)
        return bool(request.user and request.user.is_authenticated and profile and profile.is_owner)


class CanManageInventory(permissions.BasePermission):
    def has_permission(self, request, view):
        profile = get_profile(request.user)
        return bool(
            request.user
            and request.user.is_authenticated
            and profile
            and (profile.is_owner or profile.can_manage_inventory)
        )


class CanManageEmployees(permissions.BasePermission):
    def has_permission(self, request, view):
        profile = get_profile(request.user)
        return bool(
            request.user
            and request.user.is_authenticated
            and profile
            and (profile.is_owner or profile.can_manage_employees)
        )