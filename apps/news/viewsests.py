from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response

from apps.news.models import New
from apps.news.paginator import NewPagination
from apps.news.serializers import NewSerializer, NewCreateUpdateSerializer
from apps.utils.utils.baseviews import BaseModelsViewSet


class NewViewSet(BaseModelsViewSet):
    filter_backends = [OrderingFilter, DjangoFilterBackend]
    ordering_fields = ["expired_at"]
    pagination_class = NewPagination
    permission_classes_by_action = {
        "create": [IsAdminUser],
        "update": [IsAdminUser],
        "partial_update": [IsAdminUser],
        "destroy": [IsAdminUser],
        "list": [AllowAny],
        "retrieve": [AllowAny],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return NewCreateUpdateSerializer
        return NewSerializer

    def get_queryset(self):
        queryset = New.objects.order_by("expired_at")
        has_admin = IsAdminUser().has_permission(self.request, self)
        if not has_admin:
            queryset = queryset.filter(status=True, expired_at__gt=now())
        return queryset

    def get_permissions(self):
        if self.action in self.permission_classes_by_action:
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        return super().get_permissions()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "event",
                OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by related event",
            )
        ],
        responses={200: NewSerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path="by-event")
    def list_by_event(self, request, *args, **kwargs):
        event_id = request.query_params.get("event")
        if event_id:
            queryset = self.get_queryset().filter(event_id=event_id)
        else:
            queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)
