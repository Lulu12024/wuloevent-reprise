from typing import Any

from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from apps.xlib.error_util import ErrorUtil, ErrorEnum


class CheckParentPermissionMixin:
    parent_queryset: QuerySet
    parent_lookup_field: str
    parent_lookup_url_kwarg: str

    def __init__(self, **kwargs):
        self.parent_obj: Any = None
        super().__init__(**kwargs)

    def check_permissions(self, request):
        # check permissions for the parent object
        parent_lookup_url_kwarg = (
                self.parent_lookup_url_kwarg or self.parent_lookup_field
        )
        if not self.kwargs[parent_lookup_url_kwarg]:
            raise ValidationError(
                ErrorUtil.get_error_detail(
                    ErrorEnum.EMPTY_OR_NULL_ORGANIZATION_PK_IN_URL
                ),
                code=ErrorEnum.EMPTY_OR_NULL_ORGANIZATION_PK_IN_URL.value,
            )
        filter_kwargs = {self.parent_lookup_field: self.kwargs[parent_lookup_url_kwarg]}
        self.parent_obj = request.organization
        if not self.parent_obj:
            raise NotFound(
                ErrorUtil.get_error_detail(ErrorEnum.SPECIFIED_PARENT_ORGANIZATION_NOT_FOUND),
                code=ErrorEnum.SPECIFIED_PARENT_ORGANIZATION_NOT_FOUND.value,
            )
        self.parent_obj._is_parent_obj = True
        if not self.parent_obj.active:
            raise PermissionDenied(
                ErrorUtil.get_error_detail(ErrorEnum.INACTIVE_ORGANIZATION),
                code=ErrorEnum.INACTIVE_ORGANIZATION.value,
            )
        if not self.parent_obj.is_owner_verified:
            raise PermissionDenied(
                ErrorUtil.get_error_detail(ErrorEnum.UNVERIFIED_OWNER_ACCOUNT),
                code=ErrorEnum.UNVERIFIED_OWNER_ACCOUNT.value,
            )
        super().check_permissions(request)
