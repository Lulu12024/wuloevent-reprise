from rest_framework import serializers


class StatsSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    organization = serializers.IntegerField()
    event = serializers.IntegerField()
    eticket = serializers.IntegerField()
