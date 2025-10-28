import logging

from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.chat_rooms.models import ChatRoomSubscription, ChatRoom
from apps.chat_rooms.serializers.subscription import ChatRoomSubscriptionSerializer, ChatRoomSubscriptionCreateSerializer
from apps.utils.utils.baseviews import BaseModelsViewSet
from apps.xlib.enums import ChatRoomTypeEnum, ChatRoomVisibilityEnum
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)


@extend_schema(
    description="API pour la gestion des abonnements aux salons de discussion."
)
class ChatRoomSubscriptionViewSet(BaseModelsViewSet):
    """
    Viewset pour gérer les abonnements aux salons.

    Permet aux utilisateurs de :
    - S'abonner à un salon
    - Se désabonner d'un salon
    - Voir leurs abonnements
    """

    serializer_default_class = ChatRoomSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retourne les abonnements de l'utilisateur courant."""
        return ChatRoomSubscription.objects.filter(
            user=self.request.user
        ).select_related("chat_room")

    @extend_schema(
        summary="Abonnement à un salon",
        description="Permet à l'utilisateur de s'abonner à un salon de discussion.",
        parameters=[
            OpenApiParameter(
                "chat_room_pk",
                OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                required=True,
                description="ID du salon",
            )
        ],
        request=ChatRoomSubscriptionCreateSerializer,
        responses={201: ChatRoomSubscriptionSerializer},
    )
    def create(self, request, chat_room_pk=None, *args, **kwargs):
        """Abonne l'utilisateur à un salon."""
        try:
            chat_room = ChatRoom.objects.get(pk=chat_room_pk)

            # Vérifie les critères d'accès
            if chat_room.visibility == ChatRoomVisibilityEnum.PRIVATE.value:
                for criteria in chat_room.access_criteria.filter(is_active=True):
                    if not criteria.check_user_access(request.user):
                        raise ValidationError(
                            ErrorUtil.get_error_detail(
                                ErrorEnum.INVALID_CHAT_ROOM_ACCESS_CRITERIA
                            ),
                            code=ErrorEnum.INVALID_CHAT_ROOM_ACCESS_CRITERIA.value,
                        )
            username = request.user.username
            if request.data.get("username"):
                username = request.data.get("username")
            if not username:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.USERNAME_REQUIRED),
                    code=ErrorEnum.USERNAME_REQUIRED.value,
                )
            
            # Try to restore a soft-deleted subscription for this user and room
            deleted_subscriptions = ChatRoomSubscription.deleted_objects.filter(
                user=request.user, chat_room=chat_room, is_deleted=True
            )
            if deleted_subscriptions.exists():
                print("----deleted_subscriptions: ", deleted_subscriptions)
                deleted_instance = deleted_subscriptions.first()
                try:
                    deleted_instance.restore()  # restore in-place
                    restored = ChatRoomSubscription.objects.get(pk=deleted_instance.pk)
                    print("3---Subscription restored: ", restored)
                except Exception:
                    # Fallback in case restore() does not return the instance
                    restored = ChatRoomSubscription.objects.get(pk=deleted_instance.pk)
                    print("4---Subscription restored: ", restored)
                serializer = self.get_serializer(restored)
                return Response(serializer.data, status=status.HTTP_200_OK)

            # Create the subscription if none exists and no soft-deleted version to restore
            # Use get_or_create for idempotency
            subscription, created = ChatRoomSubscription.objects.get_or_create(
                user=request.user,
                chat_room=chat_room,
            )
            print("4---Subscription created: ", subscription)
            print("5---Subscription created: ", created)

            serializer = self.get_serializer(subscription)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        except ChatRoom.DoesNotExist:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.CHAT_ROOM_NOT_FOUND),
                code=ErrorEnum.CHAT_ROOM_NOT_FOUND.value,
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'abonnement: {str(e)}")
            raise e

    @extend_schema(
        summary="Désabonnement d'un salon",
        description="Permet à l'utilisateur de se désabonner d'un salon de discussion.",
        parameters=[
            OpenApiParameter(
                "chat_room_id",
                OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                required=True,
                description="ID du salon",
            )
        ],
        responses={204: None},
    )
    @action(detail=False, methods=["post"])
    def unsubscribe(self, request, chat_room_pk=None):
        """Désabonne l'utilisateur d'un salon."""
        chat_room_id = chat_room_pk

        try:
            subscription:ChatRoomSubscription = ChatRoomSubscription.objects.get(
                user=request.user, chat_room_id=chat_room_id
            )
            subscription.hard_delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        except ChatRoomSubscription.DoesNotExist:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.CHAT_ROOM_SUBSCRIPTION_NOT_FOUND),
                code=ErrorEnum.CHAT_ROOM_SUBSCRIPTION_NOT_FOUND.value,
            )
        except Exception as e:
            logger.error(f"Erreur lors du désabonnement: {str(e)}")
            raise e
