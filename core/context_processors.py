# ----- Core imports --------------------------------------------------------
from .utils import get_user_club, get_user_member


def core_context(request):
    """Add core context to all templates. To give access to global variables"""

    logged_in_user = request.user

    return {
        "logged_in_user_member": get_user_member(logged_in_user),
        "logged_in_user_member_club": get_user_club(logged_in_user),
    }
