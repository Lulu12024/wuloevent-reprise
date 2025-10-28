from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.events.models import Event, ETicket
from apps.organizations.models import Organization
from apps.users.models import User
from apps.users.permissions import HasAppAdminPermissionFor
from apps.utils.serializers import StatsSerializer


@extend_schema_view(
    statistics=extend_schema(
        description="Endpoint to get stats", responses=StatsSerializer
    )
)
@method_decorator(name='statistics', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-Get-Statistics",
    operation_description="Récupérer les statistiques dans l' applications",
    operation_summary="Statistiques"
))
class StatsViewSet(viewsets.ViewSet):
    http_method_names = ["get"]
    authentication_classes = [JWTAuthentication]
    permission_classes = [
        IsAuthenticated,
        OR(
            IsAdminUser(),
            HasAppAdminPermissionFor("Admin-Operation-Get-Statistics")
        )
    ]

    def get_permissions(self):
        def get_permission_function(instance):
            try:
                return instance()
            except TypeError:
                return instance

        return [get_permission_function(permission) for permission in self.permission_classes]

    @extend_schema(
        responses=StatsSerializer,
    )
    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        user_count = User.objects.filter(is_active=True).count()
        organization_count = Organization.objects.all().count()
        event_count = Event.objects.all().count()
        ticket_count = ETicket.objects.all().count()

        stats = StatsSerializer(
            data={
                "user": user_count,
                "organization": organization_count,
                "event": event_count,
                "eticket": ticket_count,
            }
        )
        stats.is_valid(raise_exception=True)
        return Response(stats.data)
