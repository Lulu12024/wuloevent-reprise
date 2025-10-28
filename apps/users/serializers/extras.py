from rest_framework import serializers

from apps.users.serializers import UserSerializer
from apps.users.models import User
from apps.xlib.enums import AppRolesEnum

from django.utils import timezone


class AuthResponseTypeSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserSerializer()


class SetRoleRequestSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=AppRolesEnum.items(), allow_null=True)


class UserOrganizationInfoSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'organizations']

    def get_organizations(self, instance):
        orgs = []
        
        # Organisations détenues (owner)
        for org in getattr(instance, 'owned_orgs', []):
            orgs.append({
                'pk': org.pk,
                'name': org.name,
                'type': 'owner',
                'subscription_active': self._check_subscription(org),
                'role': instance.get_user_role_for_organization(org)
            })
        
        # Organisations membres (member)
        for membership in getattr(instance, 'user_memberships', []):
            orgs.append({
                'pk': membership.organization.pk,
                'name': membership.organization.name,
                'type': 'member',
                'subscription_active': self._check_subscription(membership.organization),
                'role': instance.get_user_role_for_organization(membership.organization)
            })
        
        return orgs

    def _check_subscription(self, organization):
        """Vérifie si l'abonnement est actif"""
        if not hasattr(organization, 'subscriptions'):
            return False
            
        now = timezone.now().date()
        return any(
            sub.active_status and 
            sub.start_date <= now <= sub.end_date
            for sub in organization.subscriptions.all()
        )