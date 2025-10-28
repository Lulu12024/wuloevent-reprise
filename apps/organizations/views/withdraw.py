import logging

from django.db import transaction
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.events.permissions import IsPasswordConfirmed
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import Organization
from apps.organizations.models import Withdraw
from apps.organizations.permissions import IsOrganizationOwner
from apps.organizations.serializers import WithdrawSerializer
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.utils.baseviews import BaseGenericViewSet

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@extend_schema_view(
    create=extend_schema(
        description="Endpoint to create a withdraw for a company",
        parameters=[
            OpenApiParameter('password', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True,
                             description="The password of the user making the request."),
        ],
    )
)
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Withdraw-Create",
    operation_description="Créer un retrait",
    operation_summary="Retraits"
))
@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Withdraw-List",
    operation_description="Lister les retraits",
    operation_summary="Retraits"
))
class WithdrawViewSet(
    CheckParentPermissionMixin, CreateModelMixin, ListModelMixin, BaseGenericViewSet
):
    permission_classes = [IsAuthenticated, IsOrganizationOwner]
    authentication_classes = [JWTAuthentication]
    object_class = Withdraw
    serializer_class = WithdrawSerializer

    filter_backends = [OrderingFilter]

    ordering_fields = [
        "timestamp"
    ]

    parent_queryset = Organization.objects.filter(active=True)
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    permission_classes_by_action = {
        "create": [IsAuthenticated,
                   IsPasswordConfirmed,
                   OR(
                       IsOrganizationOwner(),
                       OR(
                           IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Withdraw-Create")
                       )
                   )],
        "list": [IsAuthenticated, IsPasswordConfirmed, OR(
            IsOrganizationOwner(),
            OR(
                IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Withdraw-List")
            )
        )],
    }

    def get_queryset(self):
        return self.object_class.objects.filter(organization_id=self.request.organization.pk)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        method = request.data.get("method", None)
        #
        # if method != WithdrawMethodEnum.MTN_BENIN.value:
        #     raise NotAcceptable(
        #         {"message": "Seul le réseau MTN est supporté actuellement."}
        #     )

        data = request.data

        serializer = self.serializer_class(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        withdraw: Withdraw = serializer.save()

        serialized_created_object = self.serializer_class(withdraw)
        headers = self.get_success_headers(serialized_created_object.data)
        return Response(
            serialized_created_object.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )
