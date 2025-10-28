# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.users.models import (
    User,
    Transaction,
)
from apps.xlib.enums import (
    TransactionStatusEnum,
)
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class TransactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Transaction
        fields = (
            "pk",
            "type",
            "user",
            "local_id",
            "amount",
            "status",
            "gateway",
            "payment_method",
            "entity_id",
            "payment_url",
            "coupon_metadata",
            "date",
        )

        read_only_fields = ("local_id", "pk", "uuid")

    def create(self, validated_data):
        try:
            progress_status = [
                TransactionStatusEnum.IN_PROGRESS.value,
                TransactionStatusEnum.PENDING.value,
            ]

            self.Meta.model.objects.get(
                uuid=validated_data.get("uuid"), status__in=progress_status
            )

            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.PAYMENT_ALREADY_IN_PROGRESS),
                code=ErrorEnum.PAYMENT_ALREADY_IN_PROGRESS.value,
            )
        except ObjectDoesNotExist:
            return super().create(validated_data)
        except Exception as exc:
            logger.exception(exc.__str__())
            raise APIException({"message": exc})
