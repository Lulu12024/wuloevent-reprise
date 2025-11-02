
from rest_framework import serializers
from django.core.validators import MinValueValidator
from apps.events.models import Ticket, Event

class StockAllocationSerializer(serializers.Serializer):
    ticket = serializers.PrimaryKeyRelatedField(queryset=Ticket.objects.select_related('event', 'organization').all())
    quantity = serializers.IntegerField(validators=[MinValueValidator(1)])
    authorized_sale_price = serializers.DecimalField(max_digits=9, decimal_places=2, min_value=0)
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        ticket: Ticket = attrs['ticket']
        request = self.context.get('request')
        organization = getattr(request, "organization", None) or getattr(request, "super_seller_organization", None)

        # Guard: Le ticket doit appartenir à l'organisation du super-vendeur OU être vendu par ce super-vendeur
        if organization and ticket.organization_id != organization.id:
            raise serializers.ValidationError("Ce ticket n'appartient pas à votre organisation.")

        return attrs
