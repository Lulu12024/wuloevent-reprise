from django.conf import settings

from apps.users.models.account_requests import AccountValidationRequest, ResetPasswordRequest


def get_password_reset_code_expiry_time():
    """
    Returns the password reset token expirty time in hours (default: 24)
    Set Django SETTINGS.RESET_PASSWORD_REQUEST_EXPIRY_TIME to overwrite this time
    :return: expiry time
    """
    # get token validation time
    return getattr(settings, 'RESET_PASSWORD_REQUEST_EXPIRY_TIME', 24)


def clear_password_reset_expired(expiry_time):
    """
    Remove all expired tokens
    :param expiry_time: Token expiration time
    """
    ResetPasswordRequest.objects.filter(timestamp__lte=expiry_time).delete()


def get_account_validation_code_expiry_time():
    """
    Returns the password reset token expirty time in hours (default: 24)
    Set Django SETTINGS.RESET_PASSWORD_REQUEST_EXPIRY_TIME to overwrite this time
    :return: expiry time
    """
    # get token validation time
    return getattr(settings, 'ACCOUNT_VALIDATION_EXPIRY_TIME', 24)


def clear_account_validation_expired(expiry_time):
    """
    Remove all expired tokens
    :param expiry_time: Token expiration time
    """
    AccountValidationRequest.objects.filter(
        timestamp__lte=expiry_time).delete()
