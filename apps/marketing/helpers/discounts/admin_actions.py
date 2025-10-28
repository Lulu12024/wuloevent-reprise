# -*- coding: utf-8 -*-
"""
Created on 08/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib.admin import ModelAdmin
from django.utils import timezone


# Create your actions here
# ========================
def reset_coupon_usage(model_admin, request, queryset):
    for coupon_user in queryset:
        coupon_user.times_used = 0
        coupon_user.save()

    ModelAdmin.message_user(model_admin, request, "Coupons remis à zéro!")


def delete_expired_coupons(model_admin, request, queryset):
    count = 0
    for coupon in queryset:
        expiration_date = coupon.ruleset.validity.expiration_date
        if timezone.now() >= expiration_date:
            coupon.delete()
            count += 1

    ModelAdmin.message_user(
        model_admin, request, "{0} Coupons expirés supprimés!".format(count)
    )


# Actions short descriptions
# ==========================
reset_coupon_usage.short_description = "Remettre à zero l' usage de coupon"
delete_expired_coupons.short_description = "Supprimer les coupons expirés"
