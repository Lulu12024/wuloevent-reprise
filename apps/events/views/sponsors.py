from rest_framework import permissions, viewsets
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.events.models import Sponsor
from apps.events.serializers.sponsors import SponsorSerializer


class SponsorsViewSet(viewsets.ModelViewSet):
    queryset = Sponsor.objects.all()
    authentication_classes = [JWTAuthentication]
    serializer_class = SponsorSerializer

    permission_classes_by_action = {
        'create': [permissions.IsAuthenticated, permissions.IsAdminUser],
        'retrieve': [permissions.AllowAny],
        'list': [permissions.AllowAny],
        'destroy': [permissions.IsAuthenticated, permissions.IsAdminUser],
    }

    def get_permissions(self):
        try:
            # return permission_classes depending on `action`
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        except KeyError:
            # action is not set return default permission_classes
            return [permission() for permission in self.permission_classes]