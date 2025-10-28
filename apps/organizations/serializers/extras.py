from rest_framework import serializers

from apps.events.models import Ticket
from apps.events.serializers import LightTicketSerializer
from apps.organizations.serializers import WithdrawSerializer
from apps.users.models import User
from apps.users.serializers import UserSerializerLight


class StatsTicketDataSerializer(serializers.Serializer):
    name = serializers.CharField()
    sold = serializers.IntegerField()
    entries = serializers.FloatField()
    amount_earn = serializers.FloatField()
    available_quantity = serializers.IntegerField()


class EventOrientedStatsResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    views = serializers.IntegerField()
    participant_count = serializers.IntegerField()
    percentage_for_wuloevents = serializers.FloatField()
    tickets_data = StatsTicketDataSerializer(many=True)
    total_earn = serializers.FloatField()


# Global Stats Period Serializer
class GlobalStatsPeriodSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()


# Global Stats Withdraw Serializer
class GlobalStatsWithdrawsSerializer(serializers.Serializer):
    list = WithdrawSerializer(many=True)
    total = serializers.FloatField()


# Global Stats EventDict Serializer
class GlobalStatsEventDictDeepContentSerializer(serializers.Serializer):
    number = serializers.IntegerField()
    total_earn = serializers.IntegerField()


class GlobalStatsEventDictContentSerializer(serializers.Serializer):
    ticketName1 = GlobalStatsEventDictDeepContentSerializer()
    ticketName2 = GlobalStatsEventDictDeepContentSerializer()


class GlobalStatsEventDictSerializer(serializers.Serializer):
    eventName1 = GlobalStatsEventDictContentSerializer()
    eventName2 = GlobalStatsEventDictContentSerializer()


class GlobalStatsStatsSerializer(serializers.Serializer):
    period = GlobalStatsPeriodSerializer()
    withdraws = GlobalStatsWithdrawsSerializer()
    events_views = EventOrientedStatsResponseSerializer()
    total_ticket_sold = serializers.IntegerField()
    ticket_sold_grouped_by_event = GlobalStatsEventDictSerializer()


class GlobalStatsResponseSerializer(serializers.Serializer):
    organization_balance = serializers.FloatField()
    stats = GlobalStatsStatsSerializer()


class WithdrawPreviewResponseSerializer(serializers.Serializer):
    available_balance = serializers.FloatField()
    minimal_amount_required = serializers.FloatField()


class PossibleRolesResponseSerializer(serializers.Serializer):
    pk = serializers.UUIDField()
    name = serializers.CharField()
    weight = serializers.IntegerField()


class PossibleWithdrawWaysResponseSerializer(serializers.Serializer):
    label = serializers.CharField()
    name = serializers.CharField()
    processor_id = serializers.CharField()
    available = serializers.BooleanField()


############# Event Participants Response Serializer##################

class LightTicketSerializerWithCount(LightTicketSerializer):
    count = serializers.IntegerField()

    class Meta:
        model = Ticket
        fields = LightTicketSerializer.Meta.fields + ("count",)


class EventParticipantsResponseSerializer(UserSerializerLight):
    tickets = LightTicketSerializerWithCount(many=True)

    class Meta:
        model = User
        fields = UserSerializerLight.Meta.fields + ("tickets",)

######################################################################
