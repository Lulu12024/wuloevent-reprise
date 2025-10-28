import logging

from django.utils.decorators import method_decorator
from drf_spectacular.utils import inline_serializer, extend_schema
from rest_framework import serializers
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.notifications.models import (
    MobileDevice,
    SubscriptionToNotificationType,
    Notification,
)
from apps.notifications.serializers import (
    MobileDeviceSerializer,
    NotificationSerializer,
    SubscriptionToNotificationTypeSerializer,
    UserDeviceTokensSerializer,
)
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.paginator import Pagination
from apps.utils.utils.baseviews import BaseGenericViewSet
from apps.xlib.custom_decorators import custom_paginated_response
from apps.xlib.enums import NOTIFICATION_STATUS_ENUM
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


# Create your viewsets here.


class MobileDeviceView(GenericAPIView, CreateModelMixin):
    object_class = MobileDevice
    permission_classes = [AllowAny]
    serializer_class = MobileDeviceSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class UserDeviceTokensView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserDeviceTokensSerializer

    @extend_schema(
        responses={
            200: UserDeviceTokensSerializer,
            404: inline_serializer(
                name="UserDeviceTokensNotFoundResponseSerializer",
                fields={
                    "message": serializers.CharField()
                },
            )
        }
    )
    def get(self, request, user_id, *args, **kwargs):
        try:
            user_device = MobileDevice.objects.filter(
                user_id=user_id,
            ).first()
            
            if not user_device:
                return Response(
                    {"message": "Aucun device trouvé pour cet utilisateur"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = self.serializer_class(user_device)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as exc:
            logger.exception(f"Erreur lors de la récupération des tokens: {exc}")
            return Response(
                {"message": "Erreur lors de la récupération des tokens"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubscriptionToNotificationTypeView(
    GenericAPIView, CreateModelMixin, DestroyModelMixin
):
    object_class = SubscriptionToNotificationType
    permission_classes = [
        IsAuthenticated,
    ]
    serializer_class = SubscriptionToNotificationTypeSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def get_queryset(self):
        return self.object_class.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data | {"user": request.user.pk}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def destroy(self, request, *args, **kwargs):
        data = request.data | {"user": request.user.pk}
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            logger.exception(exc.__str__())
            if exc.get_codes().get("non_field_errors", [None])[0] == "unique":
                user_pk = serializer.data.get("user")
                notification_type_pk = serializer.data.get("notification_type")
                instance = self.object_class.objects.get(
                    user__pk=user_pk, notification_type__pk=notification_type_pk
                )
                self.perform_destroy(instance)
            else:
                raise NotFound(
                    {
                        "message": "Vous n' avez pas souscris au notification de ce type d' abonnement."
                    }
                )
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Notification-Create",
    operation_description="Créer une Notification",
    operation_summary="Notifications"
))
@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Notification-List",
    operation_description="Lister les Notifications",
    operation_summary="Notifications"
))
@method_decorator(name='list', decorator=custom_paginated_response(
    name="NotificationListPaginatedResponseSerializer",
    description="Retrieve the notifications all notifications list",
    code=200,
    serializer_class=NotificationSerializer
))
class NotificationViewSet(BaseGenericViewSet, CreateModelMixin, ListModelMixin):
    object_class = Notification
    serializer_class = NotificationSerializer
    serializer_default_class = NotificationSerializer
    parser_classes = (JSONParser,)
    pagination_class = Pagination

    # Todo: bulk create notifications
    # Todo: Bulk send notifications list

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Notification-Create")
            )
        ],
        "list": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Notification-List")
            )
        ],
        "for_user": [IsAuthenticated],
        "set_as_read": [IsAuthenticated],
    }

    serializer_classes_by_action = {
        "create": NotificationSerializer
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @custom_paginated_response(
        name="NotificationByUserPaginatedResponseSerializer",
        description="Retrieve the notifications list of the current user",
        code=200,
        serializer_class=NotificationSerializer
    )
    @action(methods=["GET"], detail=False, url_path="for-me")
    def for_user(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(user=request.user, status=NOTIFICATION_STATUS_ENUM.SUCCESS.value,
                                              channels__contains='INBOX')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        else:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_PAGE_NUMBER),
                code=ErrorEnum.MISSING_PAGE_NUMBER.value,
            )

    @extend_schema(
        responses={
            204: inline_serializer(
                name="NotificationSettingAsReadResponseSerializer",
                fields={
                },
            )
        }
    )
    @action(methods=["PATCH"], detail=False, url_path="set-as-read")
    def set_as_read(self, request, *args, **kwargs):

        # Todo: Filter channels contains PUSH
        queryset = self.object_class.objects.filter(
            user=request.user,
        )
        queryset.update(unread=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
