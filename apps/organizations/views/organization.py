# -*- coding: utf-8 -*-
import logging
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Prefetch, Q, Sum
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import inline_serializer
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    NotFound,
)
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
)
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, OR, AND
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.events.filters import EventOrdering, EventSearch
from apps.events.models import Event, ETicket, Ticket, Order
from apps.events.parsers import MultiPartFormParser
from apps.events.permissions import IsPasswordConfirmed
from apps.events.services.events import generate_stats_for_events
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.organizations.models import (
    Organization,
    OrganizationFollow,
    Role,
    OrganizationMembership,
)
from apps.organizations.permissions import (
    IsOrganizationCoordinator,
    IsOrganizationOwner,
    IsOrganizationEventManager,
)
from apps.organizations.serializers import (
    OrganizationFollowSerializer,
    OrganizationSerializer,
)
from apps.organizations.serializers import (
    OrganizationMembersSerializer,
    AddMemberToOrganizationSerializer,
    ManageMembershipRoleSerializer,
)
from apps.organizations.serializers import WithdrawSerializer
from apps.organizations.serializers.extras import (
    EventOrientedStatsResponseSerializer,
    GlobalStatsResponseSerializer,
    WithdrawPreviewResponseSerializer,
    PossibleRolesResponseSerializer,
)
from apps.users.permissions import HasAppAdminPermissionFor
from apps.users.serializers import UserSerializerLight
from apps.utils.models import Variable
from apps.utils.paginator import Pagination
from apps.utils.utils.baseviews import BaseModelsViewSet, BaseGenericViewSet
from apps.xlib.custom_decorators import custom_paginated_response
from apps.xlib.enums import WithdrawStatusEnum, VARIABLE_NAMES_ENUM, OrderStatusEnum
from apps.xlib.error_util import ErrorUtil, ErrorEnum

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


# Todo: Cache
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Organization-Retrieve",
        operation_description="Récupérer les details d' une organisation",
        operation_summary="Organisations",
    ),
)
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Organization-List",
        operation_description="Lister les organisations",
        operation_summary="Organisations",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Organization-Update",
        operation_description="Mettre à jour une organisation",
        operation_summary="Organisations",
    ),
)
@method_decorator(
    name="members_list",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Organization-Members-List",
        operation_description="Lister les membres d' une organisation",
        operation_summary="Organisations",
    ),
)
@method_decorator(
    name="add_member",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Organization-Add-Member",
        operation_description="Ajouter des membres à une organisation",
        operation_summary="Organisations",
    ),
)
@method_decorator(
    name="manage_membership_roles",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Organization-Manage-Membership-Roles",
        operation_description="Gérer les rôles des membres d' une organisation",
        operation_summary="Organisations",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-Organization-Destroy",
        operation_description="Supprimer une organisation",
        operation_summary="Organisations",
    ),
)
class OrganizationViewSet(BaseModelsViewSet):
    object_class = Organization
    parser_classes = (MultiPartFormParser, FormParser, JSONParser)
    serializer_default_class = OrganizationSerializer

    filter_backends = [OrderingFilter]

    ordering_fields = ["timestamp"]

    permission_classes_by_action = {
        "create": [IsAuthenticated],
        "create_light": [IsAuthenticated],
        "retrieve": [
            IsAuthenticated,
            OR(
                IsOrganizationOwner(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Organization-Retrieve"),
                ),
            ),
        ],
        # "list": [
        #     IsAuthenticated,
        #     OR(
        #         IsAdminUser(),
        #         HasAppAdminPermissionFor("Admin-Operation-Organization-List"),
        #     ),
        # ],
        "list_by_user": [IsAuthenticated],
        "members_list": [
            IsAuthenticated,
            OR(
                IsOrganizationOwner(),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Organization-Members-List"
                    ),
                ),
            ),
        ],
        "update": [
            IsAuthenticated,
            OR(
                AND(IsPasswordConfirmed(), IsOrganizationOwner()),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Organization-Members-Update"
                    ),
                ),
            ),
        ],
        "add_member": [
            IsAuthenticated,
            OR(
                AND(IsPasswordConfirmed(), IsOrganizationOwner()),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Organization-Add-Member"),
                ),
            ),
        ],
        "possible_roles": [AllowAny],
        "manage_membership_roles": [
            IsAuthenticated,
            OR(
                AND(IsPasswordConfirmed(), IsOrganizationOwner()),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor(
                        "Admin-Operation-Organization-Manage-Membership-Roles"
                    ),
                ),
            ),
        ],
        "destroy": [
            IsAuthenticated,
            OR(
                AND(IsPasswordConfirmed(), IsOrganizationOwner()),
                OR(
                    IsAdminUser(),
                    HasAppAdminPermissionFor("Admin-Operation-Organization-Destroy"),
                ),
            ),
        ],
    }

    serializer_classes_by_action = {
        "create": OrganizationSerializer,
        "create_light": OrganizationSerializer,
        "retrieve": OrganizationSerializer,
        "list": OrganizationSerializer,
        "list_by_user": OrganizationSerializer,
        "members_list": OrganizationMembersSerializer,
        "add_member": AddMemberToOrganizationSerializer,
        "manage_membership_roles": ManageMembershipRoleSerializer,
        "destroy": OrganizationSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all()
    
    @action(methods=["POST"], detail=False, url_path="light")
    def create_light(self, request, *args, **kwargs):
        data = request.data.copy()
        data['active'] = False
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        responses={200: OrganizationMembersSerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path="by-me")
    def list_by_user(self, request, *args, **kwargs):
        """
        Return de list of organization that user is member of either Owner or simple Member
        """
        user = request.user
        queryset = self.filter_queryset(
            self.object_class.objects.list_by_user(user=user)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        kwargs.update({"partial": True})
        return super().update(request, *args, **kwargs)

    @extend_schema(
        description="Endpoint to get members list of an organization",
        parameters=[
            OpenApiParameter(
                "organization_pk",
                OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="The id of an organization to filter the members against ",
            ),
        ],
        responses=OrganizationMembersSerializer(many=True),
    )
    @action(methods=["GET"], detail=True, url_path="members-list")
    def members_list(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            request.organization.memberships.prefetch_related("roles", "user").all(),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: OrganizationMembersSerializer()},
    )
    @action(methods=["POST"], detail=True, url_path="add-member")
    def add_member(self, request, *args, **kwargs):
        """
        Used to add a member to an organization
        """
        organization = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user")
        member_role = serializer.validated_data.get("role", None)
        if (
                organization.memberships.filter(user=user).exists()
                or organization.owner == user
        ):
            raise APIException(
                ErrorUtil.get_error_detail(
                    ErrorEnum.USER_ALREADY_MEMBER_OF_ORGANIZATION
                ),
                code=ErrorEnum.USER_ALREADY_MEMBER_OF_ORGANIZATION.value,
            )
        new_membership = OrganizationMembership.objects.create(
            organization=organization, user=user
        )
        new_membership.roles.add(member_role)
        membership_serializer = OrganizationMembersSerializer(new_membership)
        return Response(membership_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            200: PossibleRolesResponseSerializer(),
        }
    )
    @action(methods=["GET"], detail=False, url_path="possible-roles")
    def possible_roles(self, request, *args, **kwargs):
        """
        Return the list of the possibles right that an organization can grant to his members
        """
        data = Role.objects.all().values("pk", "name", "weight")
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: OrganizationMembersSerializer()},
    )
    @action(methods=["POST"], detail=True, url_path="manage-member-roles")
    def manage_membership_roles(self, request, *args, **kwargs):
        organization = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user", "None")
        query = organization.memberships.filter(user=user)
        if not query.exists():
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.USER_NOT_MEMBER_OF_ORGANIZATION),
                code=ErrorEnum.USER_NOT_MEMBER_OF_ORGANIZATION.value,
            )

        membership = query.first()
        _action = serializer.validated_data.get("action", "ADD")
        for role in serializer.validated_data.get("roles", []):
            user_have_role = role in membership.roles.all()
            if not user_have_role and _action == "ADD":
                membership.roles.add(role)

            if user_have_role and _action == "REMOVE":
                membership.roles.remove(role)
        membership.save()

        return Response(
            OrganizationMembersSerializer(membership).data, status=status.HTTP_200_OK
        )


class OrganizationFollowView(CreateModelMixin, GenericAPIView):
    object_model = Organization
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = OrganizationFollowSerializer
    lookup_url_kwarg = "organization_pk"

    def get_queryset(self):
        return self.object_model.objects.filter(active=True)

    def post(self, request, *args, **kwargs):
        organization = self.get_object()
        serializer = self.serializer_class(
            data={"follower": request.user.pk, "organization": organization.pk}
        )
        serializer.is_valid(raise_exception=True)
        instance = None
        try:
            instance = OrganizationFollow.objects.filter(
                follower=request.user, organization=organization
            )
        except:
            pass
        if instance.exists():
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.ALREADY_FOLLOWING_ORGANIZATION),
                code=ErrorEnum.ALREADY_FOLLOWING_ORGANIZATION.value,
            )
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class OrganizationUnFollowView(DestroyModelMixin, GenericAPIView):
    object_model = Organization
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = OrganizationFollowSerializer
    lookup_url_kwarg = "organization_pk"

    def get_queryset(self):
        return self.object_model.objects.filter(active=True)

    @extend_schema(
        responses={
            204: inline_serializer(
                name="OrganizationUnFollowResponseSerializer",
                fields={},
            )
        }
    )
    def post(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        organization = self.get_object()
        serializer = self.serializer_class(
            data={"follower": request.user.pk, "organization": organization.pk}
        )
        serializer.is_valid(raise_exception=True)
        try:
            instance = OrganizationFollow.objects.get(
                follower=request.user, organization=organization
            )
            self.perform_destroy(instance)
        except:
            raise NotFound("YOU_HAVE_NOT_FOLLOW_THIS_ORGANIZATION")
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationFollowersView(RetrieveModelMixin, GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrganizationCoordinator]
    authentication_classes = [JWTAuthentication]
    serializer_class = UserSerializerLight
    pagination_class = Pagination
    object_class = Organization
    lookup_url_kwarg = "organization_pk"

    @custom_paginated_response(
        name="OrganizationFollowersListPaginatedResponseSerializer",
        description="Retrieve the list of users that are following an organization",
        code=200,
        serializer_class=UserSerializerLight,
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_queryset(self):
        return self.object_class.objects.filter(active=True)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user_followers = list(
            instance.users_followings_me.order_by("-timestamp").values_list(
                "follower", flat=True
            )
        )
        users_list = User.objects.filter(pk__in=user_followers)

        page = self.paginate_queryset(users_list)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        else:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_PAGE_NUMBER),
                code=ErrorEnum.MISSING_PAGE_NUMBER.value,
            )


class OrganizationFollowedView(ListModelMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = OrganizationSerializer
    pagination_class = Pagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        organizations_followed = list(
            self.request.user.me_following_organizations.order_by(
                "-timestamp"
            ).values_list("organization", flat=True)
        )
        return User.objects.filter(pk__in=organizations_followed)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        else:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.MISSING_PAGE_NUMBER),
                code=ErrorEnum.MISSING_PAGE_NUMBER.value,
            )


class OrganizationStatsViewSet(CheckParentPermissionMixin, BaseGenericViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationOwner]
    authentication_classes = [JWTAuthentication]
    object_class = Event
    filter_backends = [EventOrdering, EventSearch]
    search_fields = ["name", "description", "type__name", "location_name"]
    ordering_fields = ["name", "default_price", "location_name", "date", "views"]

    parent_queryset = Organization.objects.filter(active=True)
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    permission_classes_by_action = {
        "global_stats": [IsAuthenticated, IsOrganizationEventManager],
        "by_events": [IsAuthenticated, IsOrganizationEventManager],
    }

    def get_queryset(self):
        return self.object_class.objects.filter(
            organization__pk=self.parent_obj.pk, have_passed_validation=True, valid=True
        )

    @extend_schema(
        responses={200: GlobalStatsResponseSerializer()},
    )
    @action(methods=["GET"], detail=False, url_path="global")
    def global_stats(self, request, *args, **kwargs):
        import datetime

        default_start_date = datetime.datetime.now() - datetime.timedelta(30)
        default_end_date = datetime.datetime.now() + datetime.timedelta(1)
        organization = self.request.organization
        start_date = request.query_params.get("start_date", None)
        end_date = request.query_params.get("end_date", None)

        if start_date is None:
            start_date = default_start_date.date()
        else:
            try:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            except Exception as exc:
                logger.exception(exc.__str__())
                raise ValidationError(
                    {
                        "message": "Veuillez entrer un bon format (YYYY-MM-DD) pour la date de départ."
                    },
                    code=ErrorEnum.INVALID_DATE_FORMAT.value,
                )

        if end_date is None:
            end_date = default_end_date.date()
        else:
            try:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            except Exception as exc:
                logger.exception(exc.__str__())
                raise ValidationError(
                    {
                        "message": "Veuillez entrer un bon format (YYYY-MM-DD) pour la date de fin."
                    },
                    code=ErrorEnum.INVALID_DATE_FORMAT.value,
                )

        organization_financial_account = organization.get_financial_account
        organization_balance = organization_financial_account.balance

        withdraws_list_serializer = WithdrawSerializer(
            organization.withdraws.filter(
                status=WithdrawStatusEnum.FINISHED.value,
                timestamp__range=(start_date, end_date),
            ),
            many=True,
        ).data

        withdraws_sum = sum(
            [float(elmt.get("amount")) for elmt in withdraws_list_serializer]
        )
        
        organization_events = (
            Event.objects.prefetch_related(
                Prefetch(
                    "tickets",
                    queryset=Ticket.objects.filter(
                        timestamp__range=(start_date, end_date)
                    ),
                )
            )
                .prefetch_related(
                Prefetch(
                    "tickets__e_tickets",
                    queryset=ETicket.objects.filter(
                        timestamp__range=(start_date, end_date)
                    ),
                )
            )
                .filter(Q(organization=organization))
        )

        aggregated_data = Order.objects.select_related('item', 'item__ticket', 'item__ticket__event') \
            .filter(timestamp__range=(start_date, end_date)) \
            .filter(status=OrderStatusEnum.FINISHED.value, item__ticket__event__in=organization_events) \
            .values(
            "item__quantity",
            "item__line_total",
            "item__ticket__name",
            "item__ticket__event__name",
            "item__potential_discount_data__use_coupon"
        )

        event_stats = defaultdict(lambda: {})

        for entry in aggregated_data:
            event_name = entry["item__ticket__event__name"]
            ticket_name = entry["item__ticket__name"]
            has_been_discounted = entry["item__potential_discount_data__use_coupon"]
            ticket_stats = {
                "number": entry["item__quantity"],
                # "total_sold": entry["item__line_total"],
                "total_earn": Decimal(entry["item__line_total"] * Decimal(
                    1 - organization.get_retribution_percentage(has_been_discounted))).quantize(Decimal("0.01")),
            }

            # Check if the ticket already exists in the dictionary for the event
            if ticket_name in event_stats[event_name]:
                # Update the existing stats
                event_stats[event_name][ticket_name]["number"] += ticket_stats["number"]
                # event_stats[event_name][ticket_name]["total_sold"] += ticket_stats["total_sold"]
                event_stats[event_name][ticket_name]["total_earn"] += ticket_stats["total_earn"]
            else:
                # Add new ticket stats
                event_stats[event_name][ticket_name] = ticket_stats

        data = {
            "organization_balance": organization_balance,
            "stats": {
                "period": {
                    "start": start_date,
                    "end": end_date,
                },
                "withdraws": {
                    "list": withdraws_list_serializer,
                    "total": withdraws_sum,
                },
                "events_views": generate_stats_for_events(
                    organization, organization_events
                ),
                "total_ticket_sold": aggregated_data.aggregate(Sum("item__quantity"))["item__quantity__sum"],
                "ticket_sold_grouped_by_event": dict(event_stats),
            },
        }
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: EventOrientedStatsResponseSerializer()},
    )
    @action(methods=["GET"], detail=False, url_path="events-oriented")
    def by_events(self, request, *args, **kwargs):
        events_queryset = self.filter_queryset(self.get_queryset())
        data = generate_stats_for_events(request.organization, events_queryset)
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: WithdrawPreviewResponseSerializer()})
    @action(methods=["GET"], detail=False, url_path="withdraw-preview")
    def withdraw_preview(self, request, *args, **kwargs):
        financial_account = request.organization.get_financial_account
        import datetime

        default_start_date = datetime.datetime.now() - datetime.timedelta(30)
        default_end_date = datetime.datetime.now() + datetime.timedelta(1)
        start_date = request.GET.get("start_date", None)
        end_date = request.GET.get("end_date", None)

        if start_date is None:
            start_date = default_start_date.date()
        else:
            try:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            except Exception as exc:
                logger.exception(exc.__str__())
                raise ValidationError(
                    {
                        "message": "Veuillez entrer un bon format (YYYY-MM-DD) pour la date de départ."
                    },
                    code=ErrorEnum.INVALID_DATE_FORMAT.value,
                )

        if end_date is None:
            end_date = default_end_date.date()
        else:
            try:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            except Exception as exc:
                logger.exception(exc.__str__())
                raise ValidationError(
                    {
                        "message": "Veuillez entrer un bon format (YYYY-MM-DD) pour la date de fin."
                    },
                    code=ErrorEnum.INVALID_DATE_FORMAT.value,
                )

        minimal_amount_variable = Variable.objects.get(
            name=VARIABLE_NAMES_ENUM.MINIMAL_AMOUNT_REQUIRED_FOR_WITHDRAW.value
        )
        minimal_amount_valueminimal_amount_value = minimal_amount_variable.format_value(
            minimal_amount_variable.possible_values.first().value
        )
        data = {
            "available_balance": financial_account.balance,
            "minimal_amount_required": minimal_amount_valueminimal_amount_value,
        }
        return Response(data, status=status.HTTP_200_OK)
