# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import datetime
import logging

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.utils.timezone import now, make_aware, get_default_timezone
from django_filters.utils import translate_validation
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, OR
from rest_framework.response import Response

from apps.events.filters import EventOrdering, EventSearch, EventFilter
from apps.events.models import Event
from apps.events.paginator import EventPagination
from apps.events.parsers import MultiPartFormParser
from apps.events.permissions import OrganizationIsObjectCreator, IsPasswordConfirmed
from apps.events.serializers import (
    EventCreationSerializer,
    EventSerializer,
    LightEventSerializer,
)
from apps.events.services.events import get_event_participants
from apps.events.views.utils import WriteOnlyNestedModelViewSet, ReadOnlyModelViewSet
from apps.organizations.models import Organization
from apps.organizations.permissions import (
    IsOrganizationEventManager,
    OrganizationHaveActiveSubscription,
    IsOrganizationMember,
    IsOrganizationOwner,
    IsOrganizationActive,
)
from apps.organizations.serializers.extras import EventParticipantsResponseSerializer
from apps.users.models import User
from apps.users.permissions import HasAppAdminPermissionFor
from apps.xlib.custom_decorators import custom_paginated_response
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Create",
        operation_description="Créer un évènement",
        operation_summary="Évènements",
    ),
)
@method_decorator(
    name="create_private",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Create-Private",
        operation_description="Créer un évènement privé",
        operation_summary="Évènements",
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Partial-Update",
        operation_description="Mettre à jour un évènement",
        operation_summary="Évènements",
    ),
)
@method_decorator(
    name="get_participants",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Participants",
        operation_description="Voir la liste des participants d' un évènement",
        operation_summary="Évènements",
    ),
)
@method_decorator(
    name="deactivate",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Deactivate",
        operation_description="Désactiver un évènement",
        operation_summary="Évènements",
    ),
)
@method_decorator(
    name="activate",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Activate",
        operation_description="Activer un évènement",
        operation_summary="Évènements",
    ),
)
@method_decorator(
    name="get_events_by_organization",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-List-By-Organization",
        operation_description="Récupérer la liste des évènements d' une organisation",
        operation_summary="Évènements",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Destroy",
        operation_description="Supprimer un évènement",
        operation_summary="Évènement",
    ),
)
@method_decorator(
    name="update_participant_limit",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-Update-Participant-Limit",
        operation_description="Mettre à jour la limite de participants d' un évènement",
        operation_summary="Évènement",
    ),
)
@extend_schema_view(
    update=extend_schema(
        description="Endpoint to update (put) organization event",
        parameters=[
            OpenApiParameter(
                "password",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Password field for event managers",
                required=False,
            ),
        ],
        responses={200: EventSerializer()},
    ),
    partial_update=extend_schema(
        description="Endpoint to update (patch) organization event",
        parameters=[
            OpenApiParameter(
                "password",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Password field for event managers",
                required=False,
            )
        ],
        responses={200: EventSerializer()},
    ),
    deactivate=extend_schema(
        description="Endpoint to deactivate organization event",
        parameters=[
            OpenApiParameter(
                "password",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Password field for event managers",
                required=False,
            )
        ],
        request=None,
        responses={200: LightEventSerializer()},
    ),
    activate=extend_schema(
        description="Endpoint to activate organization event",
        parameters=[
            OpenApiParameter(
                "password",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Password field for event managers",
                required=False,
            )
        ],
        request=None,
        responses={200: LightEventSerializer()},
    ),
    destroy=extend_schema(
        description="Endpoint to delete organization event",
        parameters=[
            OpenApiParameter(
                "password",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Password field for event managers",
                required=False,
            )
        ],
    ),
)
class WriteOnlyEventViewSet(WriteOnlyNestedModelViewSet):
    """

    create:
        Create a new event.

    delete:
        Remove an existing event.

    partial_update:
        Update one or more fields on an existing event.

    update:
        Update a event.
    """

    object_class = Event
    serializer_default_class = EventSerializer
    parser_classes = (MultiPartFormParser, FormParser, JSONParser)
    pagination_class = EventPagination

    parent_queryset = Organization.objects.all()
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    permission_classes_by_action = {
        "create": [
            IsAuthenticated,
            OR(
                (OrganizationHaveActiveSubscription & IsOrganizationEventManager)(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Create"),
                ),
            ),
        ],
        "create_private": [
            IsAuthenticated,
            OR(
                (IsOrganizationActive & IsOrganizationEventManager)(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Create-Private"),
                ),
            ),
        ],
        "partial_update": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsOrganizationEventManager
                        & OrganizationIsObjectCreator
                        & IsPasswordConfirmed
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Partial-Update"),
                ),
            ),
        ],
        "get_participants": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsOrganizationEventManager
                        & OrganizationIsObjectCreator
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Participants"),
                ),
            ),
        ],
        "deactivate": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsOrganizationEventManager
                        & OrganizationIsObjectCreator
                        & IsPasswordConfirmed
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Deactivate"),
                ),
            ),
        ],
        "activate": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsOrganizationEventManager
                        & OrganizationIsObjectCreator
                        & IsPasswordConfirmed
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Activate"),
                ),
            ),
        ],
        # 'get_events_by_organization': [IsAuthenticated, OrganizationHaveActiveSubscription, IsOrganizationMember],
        "get_events_by_organization": [
            IsAuthenticated,
            OR(
                IsOrganizationMember(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Event-List-By-Organization"
                    ),
                ),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsPasswordConfirmed
                        & (IsOrganizationOwner | IsOrganizationEventManager)
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Destroy"),
                ),
            ),
        ],
        "update_participant_limit": [
            IsAuthenticated,
            OR(
                (
                        OrganizationHaveActiveSubscription
                        & IsPasswordConfirmed
                        & (IsOrganizationOwner | IsOrganizationEventManager)
                )(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Event-Update-Participant-Limit"),
                ),
            ),
        ],
    }

    serializer_classes_by_action = {
        "create": EventCreationSerializer,
        "create_private": EventCreationSerializer,
        "update": EventCreationSerializer,
        "partial_update": EventCreationSerializer,
        "update_participant_limit": EventCreationSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all().order_by("-highlight_level")

    def get_pagination_page(self, queryset):
        page = self.paginate_queryset(queryset)

        if page is None:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_PAGE_NUMBER),
                code=ErrorEnum.MISSING_PAGE_NUMBER.value,
            )

        return page

    def format_response(self, queryset):
        filterset = EventFilter(self.request.GET, queryset=queryset)
        if not filterset.is_valid():
            raise translate_validation(filterset.errors)
        page = self.get_pagination_page(filterset.qs)

        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = True
        instance = self.get_object()
        current_datetime = now()
        event_datetime = make_aware(
            datetime.datetime.combine(instance.date, instance.hour),
            get_default_timezone(),
        )
        if current_datetime > event_datetime:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.CANNOT_UPDATE_PASS_EVENT),
                code=ErrorEnum.CANNOT_UPDATE_PASS_EVENT.value,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        user = str(request.user.pk)
        data = request.data | {
            "publisher": user,
            "organization": kwargs.get("organization_pk", None),
        }
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        headers = self.get_success_headers(serializer.data)
        serializer = LightEventSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
    @action(methods=["POST"], detail=False, url_path="private")
    def create_private(self, request, *args, **kwargs):
        user = str(request.user.pk)
        data = request.data | {
            "publisher": user,
            "organization": kwargs.get("organization_pk", None),
            "private": True,
        }
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        headers = self.get_success_headers(serializer.data)
        serializer = LightEventSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @custom_paginated_response(
        name="EventListOrganizationByUserPaginatedResponseSerializer",
        description="Retrieve events list by organizations",
        code=200,
        serializer_class=EventSerializer,
    )
    @action(methods=["GET"], detail=False, url_path="by-organization")
    def get_events_by_organization(self, request, *args, **kwargs):
        queryset = self.filter_queryset(
            self.object_class.objects.filter(organization=request.organization)
        )
        return self.format_response(queryset)

    @custom_paginated_response(
        name="EventParticipantsPaginatedResponseSerializer",
        description="Retrieve event participants",
        code=200,
        serializer_class=EventParticipantsResponseSerializer,
    )
    @action(methods=["GET"], detail=True, url_path="participants")
    def get_participants(self, request, pk, *args, **kwargs):
        queryset = User.objects.filter(related_orders__related_e_tickets__event_id=pk).only("id")
        page = self.get_pagination_page(queryset=queryset)
        return Response(get_event_participants(event_pk=pk, users_ids=[str(item.pk) for item in page]),
                        status=status.HTTP_200_OK)

    @action(methods=["PUT"], detail=True, url_path="deactivate")
    def deactivate(self, request, *args, **kwargs):
        event = self.get_object()
        event.deactivate()
        return Response(LightEventSerializer(event).data, status=status.HTTP_200_OK)

    @action(methods=["PUT"], detail=True, url_path="activate")
    def activate(self, request, *args, **kwargs):
        event = self.get_object()
        event.activate()
        return Response(LightEventSerializer(event).data, status=status.HTTP_200_OK)

    @action(methods=["PUT"], detail=True, url_path="update-participant-limit")
    def update_participant_limit(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = True

        data = {"participant_limit": request.data.get("participant_limit")}

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


# Todo: Cache
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Event-List",
        operation_description="Lister les évènements",
        operation_summary="Évènements",
    ),
)
@extend_schema_view(
    get=extend_schema(
        description="Endpoint to get events list",
        parameters=[
            OpenApiParameter(
                "from_admin",
                OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Request coming from admin",
            ),
            OpenApiParameter(
                "eventPk",
                OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Request coming from admin",
            ),
        ],
        responses=EventSerializer,
    )
)
class ReadOnlyEventViewSet(ReadOnlyModelViewSet):
    """
    retrieve:
        Return an event instance.

    list:
        Return all event, ordered by most recently joined.
    """

    object_class = Event
    serializer_default_class = EventSerializer
    pagination_class = EventPagination
    filter_backends = [EventOrdering, EventSearch]
    parser_classes = (MultiPartFormParser, FormParser, JSONParser)
    search_fields = ["name", "description", "type__name", "location_name"]
    ordering_fields = [
        "name",
        "default_price",
        "location_name",
        "date",
        "views",
        "timestamp",
        "have_passed_validation",
    ]

    permission_classes_by_action = {
        "retrieve": [AllowAny],
        "list": [AllowAny],
        "get_events_by_type": [
            AllowAny,
        ],
        "get_events_by_location": [
            AllowAny,
        ],
        "get_events_by_date": [
            AllowAny,
        ],
        "get_events_by_date_range": [
            AllowAny,
        ],
        "get_highlighted_events": [
            AllowAny,
        ],
    }

    serializer_classes_by_action = {
        "get_event_by_type": LightEventSerializer,
    }

    def get_queryset(self):
        request = self.request

        from_admin = request and request.query_params.get("from_admin") == "true"

        if from_admin:
            queryset = self.object_class.admin_objects.all()
            if not OR(
                    IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Event-List")
            ).has_permission(request, self):
                raise PermissionDenied(
                    ErrorUtil.get_error_detail(ErrorEnum.RESOURCE_RESERVED_TO_ADMIN),
                    code=ErrorEnum.RESOURCE_RESERVED_TO_ADMIN.value,
                )

        else:
            current_datetime = now()
            organizations_with_valid_subscription = Organization.objects.filter(
                subscriptions__start_date__lte=current_datetime,
                subscriptions__end_date__gte=current_datetime,
                subscriptions__active_status=True,
            ).values_list("pk", flat=True)

            queryset = self.object_class.objects.filter(
                organization_id__in=list(organizations_with_valid_subscription),
                have_passed_validation=True,
                valid=True,
                active=True,
            )

        return queryset

    def get_next_events(self):
        queryset = self.get_queryset()

        if getattr(queryset, "from_admin", False):
            return queryset

        current_datetime = now()
        return queryset.filter(
            expiry_date__gte=current_datetime,
        )

    def get_object(self):
        obj = super(ReadOnlyEventViewSet, self).get_object()
        obj.increment_by_one_view()
        # event_tasks.update_event_views_count.delay(obj.pk)
        return obj

    def get_pagination_page(self, queryset):
        page = self.paginate_queryset(queryset)

        if page is None:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_PAGE_NUMBER),
                code=ErrorEnum.MISSING_PAGE_NUMBER.value,
            )

        return page

    def format_response(self, queryset):
        filterset = EventFilter(self.request.GET, queryset=queryset)
        if not filterset.is_valid():
            raise translate_validation(filterset.errors)
        page = self.get_pagination_page(filterset.qs)

        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        description="Endpoint to get events list",
        parameters=[
            OpenApiParameter(
                "price",
                OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description="Filter where event price is exactly equal to this value",
            ),
            OpenApiParameter(
                "price_gt",
                OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description="Filter where event' s price is greater than this value ",
            ),
            OpenApiParameter(
                "price_lt",
                OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description="Filter where event' s price is lower than this value ",
            ),
            OpenApiParameter(
                "valid",
                OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter valid events",
            ),
            OpenApiParameter(
                "from_admin",
                OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Request coming from admin",
            ),
            OpenApiParameter(
                "expiry_date_gt",
                OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter event on expired date",
            ),
            OpenApiParameter(
                "expiry_date_lt",
                OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter event on expired date",
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_next_events().filter(private=False))
        return self.format_response(queryset)

    @custom_paginated_response(
        name="CustomEventListPaginatedResponseSerializer",
        description="Retrieve Events List By Type",
        code=200,
        serializer_class=EventSerializer,
    )
    @action(methods=["GET"], detail=False, url_path="by-type")
    def get_events_by_type(self, request, *args, **kwargs):
        eventy_type_pk = request.GET.get("event_type_pk", None)
        queryset = self.filter_queryset(
            self.get_next_events().filter(type__pk=eventy_type_pk)
        )
        return self.format_response(queryset)

    @custom_paginated_response(
        name="CustomEventListPaginatedResponseSerializer",
        description="Retrieve Events List By Location",
        code=200,
        serializer_class=EventSerializer,
    )
    @action(methods=["GET"], detail=False, url_path="by-location")
    def get_events_by_location(self, request, *args, **kwargs):
        longitude = float(request.GET.get("long", 0))
        latitude = float(request.GET.get("lat", 0))
        location = Point(longitude, latitude, srid=4326)
        queryset = self.filter_queryset(
            self.get_next_events()
                .annotate(distance=Distance("location", location))
                .order_by("distance")
        )
        return self.format_response(queryset)

    @custom_paginated_response(
        name="CustomEventListPaginatedResponseSerializer",
        description="Retrieve Events List By Date",
        code=200,
        serializer_class=EventSerializer,
    )
    @action(methods=["GET"], detail=False, url_path="by-date")
    def get_events_by_date(self, request, *args, **kwargs):
        logger.info(request.GET)
        try:
            date = request.GET.get("date")
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_DATE),
                code=ErrorEnum.MISSING_DATE.value,
            )
        try:
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_DATE_FORMAT),
                code=ErrorEnum.INVALID_DATE_FORMAT.value,
            )

        queryset = self.filter_queryset(self.get_next_events().filter(date=date))
        return self.format_response(queryset)

    @custom_paginated_response(
        name="CustomEventListPaginatedResponseSerializer",
        description="Retrieve Events List By Date Range",
        code=200,
        serializer_class=EventSerializer,
    )
    @action(methods=["GET"], detail=False, url_path="by-daterange")
    def get_events_by_date_range(self, request, *args, **kwargs):
        try:
            start_date = request.GET.get("start_date")
            end_date = request.GET.get("end_date")
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_DATE_RANGE),
                code=ErrorEnum.MISSING_DATE_RANGE.value,
            )
        try:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_DATE_FORMAT),
                code=ErrorEnum.INVALID_DATE_FORMAT.value,
            )

        queryset = self.filter_queryset(
            self.get_next_events().filter(date__lte=end_date, date__gte=start_date)
        )
        return self.format_response(queryset)

    @custom_paginated_response(
        name="CustomEventListPaginatedResponseSerializer",
        description="Retrieve Highlighted Events List",
        code=200,
        serializer_class=EventSerializer,
    )
    @action(methods=["GET"], detail=False, url_path="highlighted")
    def get_highlighted_events(self, request, *args, **kwargs):
        _now = datetime.datetime.now()
        base_queryset = self.get_next_events().filter(
            highlight__active_status=True,
            highlight__start_date__lte=_now,
            highlight__end_date__gte=_now,
        )
        queryset = self.filter_queryset(base_queryset)
        return self.format_response(queryset)
