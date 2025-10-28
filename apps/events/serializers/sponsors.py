from rest_framework import serializers
from apps.events.models import Sponsor


class SponsorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sponsor
        fields = [
            "pk", "name", "logo", "url", "active"
        ]