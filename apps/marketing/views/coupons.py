# -*- coding: utf-8 -*-
"""
Created on 12/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema_view, extend_schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.marketing.models import Coupon, Discount
from apps.marketing.serializers import CouponSerializer
from apps.marketing.serializers.coupons import CheckCouponRequestSerializer, CheckCouponResponseSerializer
from apps.marketing.services.discounts import is_discount_available_to_user_or_organization, \
    check_discount_target_entity, get_discounted_value
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.utils.baseviews import BaseModelsViewSet
from apps.xlib.enums import ErrorEnum
from apps.xlib.error_util import ErrorUtil

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


# Todo: Cache List
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Coupon-Create",
    operation_description="Créer un coupon",
    operation_summary="Coupons"
))
@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Coupon-List",
    operation_description="Lister les coupons",
    operation_summary="Coupons"
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Coupon-Update",
    operation_description="Mettre à jour un coupon",
    operation_summary="Coupons"
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Coupon-Destroy",
    operation_description="Supprimer un coupon",
    operation_summary="Coupons"
))
@extend_schema_view(
    check_availability=extend_schema(
        description="Check coupon availability", request=CheckCouponRequestSerializer(),
        responses={200: CheckCouponResponseSerializer()}
    )
)
class CouponViewSet(BaseModelsViewSet):
    object_class = Coupon
    serializer_default_class = CouponSerializer

    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["code", "discount__label"]

    ordering_fields = [
        "timestamp"
    ]

    http_method_names = ["post", "get", "put", "delete"]

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Coupon-Create"
                ),
            ),
        ],
        "retrieve": [AllowAny],
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Coupon-List"
                ),
            ),
        ],
        "update": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Coupon-Update"
                ),
            ),
        ],
        "check_availability": [AllowAny],
        "destroy": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor(
                    "Admin-Operation-Coupon-Destroy"
                ),
            ),
        ],
    }

    serializer_classes_by_action = {
        "check_availability": CheckCouponRequestSerializer
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)

    @action(methods=["POST"], detail=False, url_path="check-availability")
    def check_availability(self, request, *args, **kwargs):
        serializer = CheckCouponRequestSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            errors = exc.args[0]

            if errors and "coupon" in errors.keys() and errors['coupon'][0].code == "does_not_exist":
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.COUPON_NOT_FOUND),
                    code=ErrorEnum.COUPON_NOT_FOUND.value,
                )
            if errors and "organization" in errors.keys() and errors['organization'][0].code == "does_not_exist":
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.ORGANIZATION_NOT_FOUND),
                    code=ErrorEnum.ORGANIZATION_NOT_FOUND.value,
                )
            raise exc

        data = serializer.validated_data

        entity_id = data.get("entity_id")
        entity_quantity = data.get("entity_quantity")
        coupon: Coupon = data.get("coupon")
        organization = data.get("organization")

        discount = Discount.objects \
            .select_related("usage_rule", "validation_rule") \
            .get(pk=coupon.discount_id)

        validation_rule = discount.validation_rule

        discount_entity_type, entity_exists, entity = check_discount_target_entity(discount, entity_id)

        if not entity_exists:
            raise ValidationError(
                f" {discount_entity_type} avec la clé {entity_id} non trouvé.",
                code=ErrorEnum.RESOURCE_NOT_FOUND.value,
            )

        is_available, message, code = is_discount_available_to_user_or_organization(
            discount, entity=entity,
            entity_quantity=entity_quantity,
            organization=organization,
            user=request.user if not request.user.is_anonymous else None)

        if not is_available:
            raise ValidationError(
                detail=message,
                code=code,
            )

        initial_amount = entity.get_purchase_cost(quantity=entity_quantity)
        calculation_infos = validation_rule.get_calculation_infos()
        data = {
            "calculation_method": calculation_infos,
            "initial_amount": initial_amount,
            "reduced_amount": get_discounted_value(initial_value=initial_amount,
                                                   discount_calculation_info=calculation_infos)
        }

        return Response(data, status=status.HTTP_200_OK)


__all__ = ["CouponViewSet", ]
