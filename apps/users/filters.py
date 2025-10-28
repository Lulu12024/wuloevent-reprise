import django_filters as filters

from apps.users.models import User, Transaction


class UserFilter(filters.FilterSet):
    is_event_organizer = filters.BooleanFilter(method='filter_is_event_organizer')

    def filter_is_event_organizer(self, queryset, name, value):
        return queryset.filter(**{name: value})

    class Meta:
        model = User
        fields = ['is_staff', 'is_event_organizer']


class TransactionFilter(filters.FilterSet):
    status = filters.BooleanFilter(method="filter_status")
    type = filters.CharFilter(field_name='type', lookup_expr='exact')
    user = filters.CharFilter(field_name='user__pk', lookup_expr='exact')
    gateway_id = filters.CharFilter(field_name='gateway_id', lookup_expr='exact')
    payment_method = filters.CharFilter(field_name='payment_method', lookup_expr='exact')

    def filter_status(self, queryset, name, value):
        return queryset.filter(**{name: value})

    class Meta:
        model = Transaction
        fields = ["status", "user", "type", "gateway_id", "payment_method"]
