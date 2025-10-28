# -*- coding: utf-8 -*-
"""
Created on 08/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import random
import string

from django.conf import settings


def get_coupon_code_length(length=12):
    return (
        settings.DSC_COUPON_CODE_LENGTH
        if hasattr(settings, "COUPON_CODES_LENGTH")
        else length
    )


def get_random_code(length=12):
    length = get_coupon_code_length(length=length)
    return "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(length)
    )
