# -*- coding: utf-8 -*-
"""
Created on October 22, 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging

from apps.marketing.models import Coupon
from apps.marketing.services.discounts import use_discount

logger = logging.getLogger(__name__)


def update_coupon_related_to_transaction_usage(transaction, entity_id: str, entity_type: str):
    if not transaction.paid or not transaction.coupon_metadata.get('use_coupon', False):
        return
    try:
        related_coupon = Coupon.objects.select_related("discount").get(
            pk=transaction.coupon_metadata.get('coupon_id', False))
        related_coupon.use_coupon()
        use_discount(related_coupon.discount, entity_id, entity_type)
    except Exception as exc:
        logger.warning(exc.__str__())
