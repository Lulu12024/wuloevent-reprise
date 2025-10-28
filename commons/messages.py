from django.utils.translation import gettext_lazy as _


class Messages:
    INVALID_CREDENTIALS_ERROR = _("Unable to log in with provided credentials.")
    INACTIVE_ACCOUNT_ERROR = _("User account is disabled.")
    INVALID_TOKEN_ERROR = _("Invalid token for given user.")
    INVALID_UID_ERROR = _("Invalid user id or user doesn't exist.")
    STALE_TOKEN_ERROR = _("Stale token for given user.")
    PASSWORD_MISMATCH_ERROR = _("The two password fields didn't match.")
    USERNAME_MISMATCH_ERROR = _("The two {0} fields didn't match.")
    INVALID_PASSWORD_ERROR = _("Invalid password.")
    EMAIL_NOT_FOUND = _("User with given email does not exist.")
    CANNOT_CREATE_USER_ERROR = _("Unable to create account.")

    THIS_FIELD_MUST_NOT_BE_EMPTY = 'THIS_FIELD_MUST_NOT_BE_EMPTY'

    LEAGUE_OBJECT_WITH_THIS_ATTRS_DOES_NOT_EXIST = 'LEAGUE_OBJECT_WITH_THIS_ATTRS_DOES_NOT_EXIST'
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    NOT_ENOUGH_CASH_IN_YOUR_ACCOUNT = 'NOT_ENOUGH_CASH_IN_YOUR_ACCOUNT'
