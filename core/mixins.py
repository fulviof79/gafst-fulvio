# ----- Django imports --------------------------------------------------------
from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseForbidden
from django.utils.translation import gettext_lazy as _

# ----- Core Imports ----------------------------------------------------------
from .enums import GroupEnum


# ---- Messages ----------------------------------------------------------------
NOT_HAVE_PERMISSION_TO_VIEW_PAGE_ERROR_MESSAGE = _(
    "You don't have permission to access this page."
)


# ----- mixin for views --------------------------------------------------------
class AdminLoginRequiredMixin(AccessMixin):
    """Makes sure that the user is logged in and is a FSTB admin or a club admin."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        is_fstb_admin = request.user.groups.filter(
            name=GroupEnum.FSTB_ADMIN.value
        ).exists()
        is_club_admin = request.user.groups.filter(
            name=GroupEnum.CLUB_ADMIN.value
        ).exists()

        if not is_fstb_admin and not is_club_admin:
            return HttpResponseForbidden(NOT_HAVE_PERMISSION_TO_VIEW_PAGE_ERROR_MESSAGE)
        return super().dispatch(request, *args, **kwargs)


class FstbAdminLoginRequiredMixin(AccessMixin):
    """Makes sure that the user is logged in and is a FSTB admin."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        is_fstb_admin = request.user.groups.filter(
            name=GroupEnum.FSTB_ADMIN.value
        ).exists()

        if not is_fstb_admin:
            return HttpResponseForbidden(NOT_HAVE_PERMISSION_TO_VIEW_PAGE_ERROR_MESSAGE)
        return super().dispatch(request, *args, **kwargs)
