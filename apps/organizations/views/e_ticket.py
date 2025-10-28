import logging

from drf_spectacular.utils import extend_schema, inline_serializer
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated, OR, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import ETicket
from apps.events.serializers import ScanETicketSerializer
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import Organization
from apps.organizations.permissions import IsOrganizationMember
from apps.users.permissions import HasAppAdminPermissionFor
from apps.xlib.enums import ErrorEnum
from apps.xlib.error_util import ErrorUtil

logger = logging.getLogger(__name__)


class ScanETicketView(CheckParentPermissionMixin, APIView):
    permission_classes = [
        IsAuthenticated,
        OR(
            IsOrganizationMember(),
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Scan-ETicket")
            ))
    ]
    serializer_class = ScanETicketSerializer

    parent_queryset = Organization.objects.all()
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    def get_permissions(self):
        def get_permission_function(instance):
            try:
                return instance()
            except TypeError:
                return instance

        return [get_permission_function(permission) for permission in self.permission_classes]

    @swagger_auto_schema(
        operation_id="Admin-Operation-Scan-ETicket",
        operation_description="Scanner un ticket acheté",
        operation_summary="ETicket"
    )
    @extend_schema(
        responses={
            202: inline_serializer(
                name="ScanEticketResponseSerializer",
                fields={
                },
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        logger.info('########### Star scanning ticket ##############')
        logger.info(data)
        is_valid, instance = ETicket.verify_secret_phrase(data, organization_pk=self.parent_obj.pk)
        logger.info(is_valid, instance)

        if instance is None:
            logger.warning("Error: End process with 'Ticket Instance is None'")
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.TICKET_NOT_FOUND),
                code=ErrorEnum.TICKET_NOT_FOUND.value,
            )
        elif not is_valid:
            logger.warning("Error: End process with 'Not valid ticket'")
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_TICKET),
                code=ErrorEnum.INVALID_TICKET.value,
            )
        if not instance.active:
            logger.warning("Error: End process with 'Not active ticket'")
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.ALREADY_USED_TICKET),
                code=ErrorEnum.ALREADY_USED_TICKET.value,
            )
        else:
            instance.active = False
            instance.save()

        logger.info('########### Finish scanning ticket, with success ##############')
        return Response(status=status.HTTP_202_ACCEPTED)
