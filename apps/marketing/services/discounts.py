# -*- coding: utf-8 -*-
"""
Created on 24/10/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging
from decimal import Decimal, ROUND_UP
from typing import Literal
from typing import Union, Dict, TypeVar, Tuple, List

from django.db.models import Q
from django.utils import timezone

from apps.events.models import EventHighlightingType, Ticket
from apps.marketing.models import DiscountValidationRule, DiscountUsageRule, Discount, Coupon
from apps.marketing.models.discount_usages import DiscountUsage
from apps.organizations.models import SubscriptionType, Organization
from apps.users.models import User
from apps.xlib.enums import DISCOUNT_USE_ENTITY_TYPES_ENUM, DISCOUNT_TARGET_TYPES_ENUM
from apps.xlib.enums_types import DISCOUNT_TYPES_ENUM_VALUES_LIKE, DISCOUNT_TARGET_TYPES_ENUM_VALUES_LIKE

logger = logging.getLogger(__name__)

# Types definition

UserT = TypeVar("UserT", bound=User)
TicketT = TypeVar("TicketT", bound=Ticket)
OrganizationT = TypeVar("OrganizationT", bound=Organization)
SubscriptionTypeT = TypeVar("SubscriptionTypeT", bound=SubscriptionType)
EventHighlightingTypeT = TypeVar("EventHighlightingTypeT", bound=EventHighlightingType)

DISCOUNT_TARGET_TYPES: Dict[
    Union[DISCOUNT_TARGET_TYPES_ENUM_VALUES_LIKE, str], Union[Ticket, EventHighlightingType, SubscriptionType]] = {
    DISCOUNT_TARGET_TYPES_ENUM.TICKET.value: Ticket,
    DISCOUNT_TARGET_TYPES_ENUM.EVENT_HIGHLIGHTING.value: EventHighlightingType,
    DISCOUNT_TARGET_TYPES_ENUM.SUBSCRIPTION.value: SubscriptionType
}
DISCOUNT_USE_ENTITY_TYPES: Dict[Union[DISCOUNT_TARGET_TYPES_ENUM_VALUES_LIKE, str], Union[User, Organization]] = {
    DISCOUNT_TARGET_TYPES_ENUM.TICKET.value: User,
    DISCOUNT_TARGET_TYPES_ENUM.EVENT_HIGHLIGHTING.value: Organization,
    DISCOUNT_TARGET_TYPES_ENUM.SUBSCRIPTION.value: Organization
}
DISCOUNT_USE_ENTITY_TYPES_STR: Dict[Union[DISCOUNT_TARGET_TYPES_ENUM_VALUES_LIKE, str], str] = {
    DISCOUNT_TARGET_TYPES_ENUM.TICKET.value: DISCOUNT_USE_ENTITY_TYPES_ENUM.USER.value,
    DISCOUNT_TARGET_TYPES_ENUM.EVENT_HIGHLIGHTING.value: DISCOUNT_USE_ENTITY_TYPES_ENUM.ORGANIZATION.value,
    DISCOUNT_TARGET_TYPES_ENUM.SUBSCRIPTION.value: DISCOUNT_USE_ENTITY_TYPES_ENUM.ORGANIZATION.value
}


def use_discount(discount, entity_id: str, entity_type: Literal["ORGANIZATION", "USER"]):
    """
    Use to update discount usage counting for each user / organization when discount is applied
    @params:
        discount
        entity_id
        entity_type
    """
    discount_usage, created = DiscountUsage.objects.get_or_create(discount=discount, entity_id=entity_id,
                                                                  entity_type=entity_type)
    discount_usage.usages += 1
    discount_usage.save(update_fields=["usages"])

    discount.usages_count += 1
    discount.save(update_fields=["usages_count"])
    return discount_usage, created


def check_discount_target_entity(discount, entity_id: str) -> Tuple[str,
                                                                    bool,
                                                                    Union[
                                                                        Ticket,
                                                                        SubscriptionType,
                                                                        EventHighlightingType,
                                                                        None
                                                                    ]]:
    """
    Check if an entity the discount
    @prams:
        discount
        entity_id

    """
    related_entity_model = DISCOUNT_TARGET_TYPES.get(discount.target_type)
    entity = None
    try:
        entity = related_entity_model.objects.get(pk=entity_id)
    except Exception as exc:
        logger.info(exc.__str__())

    return related_entity_model._meta.verbose_name, entity is not None, entity


def check_discount_date_validity(discount, _datetime=None):
    """
    Test whether this discount is currently valid at datetime
    view point.
    @params:
        discount
        _datetime
    """
    _datetime = _datetime or timezone.now()
    s, e = discount.starts_at, discount.ends_at

    return (s is None and e is None) or (
            (s is None and e > _datetime) or
            (e is None and s < _datetime) or
            (s <= _datetime <= e)
    )


def check_discount_usage_limit_validity(discount):
    """
    Check if the discount is available on a usage limit
    view point
    @params
        discount: [ Discount]
    """
    if not discount.usage_limit:
        return True
    return discount.usages_count <= discount.usage_limit


def check_discount_minimal_amount(discount, amount: Decimal):
    """
    Check if an amount hit the minimal amount needed to apply
    the discount or match non-need minimal amount condition
    @params:
            discount: [ Decimal ]
            amount: [ Decimal ]
    """
    if not discount.minimal_amount:
        return True
    return discount.minimal_amount <= amount


def check_discount_usage_validation_conditions(discount, target: Union[OrganizationT, UserT]) -> bool:
    """
    Check if the instance passed user / organization is able
    to use the discount
    @params:
            discount: [ Discount] The discount needed
            target: [User | Organization ] The target entity
    """
    expected_class: Union[User, Organization] = DISCOUNT_USE_ENTITY_TYPES[discount.target_type]
    if not isinstance(target, expected_class):
        raise TypeError(f"Expected {expected_class.__name__}, got {type(target).__name__}")
    return discount.usage_rule.check_rule(obj=target)


def check_discount_entity_validation_conditions(discount,
                                                target: Union[TicketT, EventHighlightingTypeT, SubscriptionTypeT],
                                                consumer: Union[UserT, OrganizationT]
                                                ):
    """
    Check if a consumer match the discount validation condition for a target
    @params:
            discount: [ Discount ]
            target: [ Ticket, SubscriptionType, EventHighlightingType ]
            consumer: [ User | Organization ]
    """
    expected_class = DISCOUNT_TARGET_TYPES[discount.target_type]
    if not isinstance(target, expected_class):
        raise TypeError(f"Expected {expected_class.__name__}, got {type(target).__name__}")
    return discount.validation_rule.evaluate_conditions_for_target(discount.target_type, target, consumer)


def is_discount_available_to_user_or_organization(
        discount: Discount,
        entity: Union[TicketT, SubscriptionTypeT, EventHighlightingTypeT],
        entity_quantity: int,
        user: Union[User, None] = None,
        organization: Union[Organization, None] = None) -> Tuple[bool, str, str]:
    """
    Test whether this discount is available to the passed user or / organization.

    Returns a tuple of a boolean for whether it is successful, and a
    availability code.
    @params:
            discount: [ Discount ]
            entity: [Union[TicketT, SubscriptionTypeT, EventHighlightingTypeT]]
            entity_quantity: [int]
            user: [ User | None]
            organization: [ Organization | None]
    """

    is_available, message, code = False, "une erreur s' est produite, veuillez réessayer", ''

    try:
        # Get the right consumer entity for the validation process
        entity_type = DISCOUNT_USE_ENTITY_TYPES_STR.get(discount.target_type)
        consumer = organization if entity_type == DISCOUNT_USE_ENTITY_TYPES_ENUM.ORGANIZATION.value else user

        # Assume the consumer_entity [ organization or user]  is not None
        # Allow anonymous user checking for pseudo anonymous orders
        # This is a temporary fix until we define who to handle anonymous users
        # By pass anonymous user checks for pseudo anonymous orders
        if not consumer and entity_type == DISCOUNT_USE_ENTITY_TYPES_ENUM.ORGANIZATION.value:
            code = "DISCOUNT_CHECK_CONSUMER_ENTITY_NOT_PROVIDED"
            message = "Veuillez renseigner {0} pour la validation" \
                .format('une organisation' if entity_type == DISCOUNT_USE_ENTITY_TYPES_ENUM.ORGANIZATION.value
                        else ' un utilisateur')
            raise AssertionError
        # First, check date availability
        if not check_discount_date_validity(discount):
            code = "DISCOUNT_CHECK_DATE_VALIDITY_ERROR"
            message = "La réduction n' est pas encore disponible ou est déjà expirée."
            raise AssertionError

        # Second, check minimal amount availability
        purchase_cost = entity.get_purchase_cost(entity_quantity)
        if not check_discount_minimal_amount(discount, purchase_cost):
            code = "DISCOUNT_CHECK_MINIMAL_AMOUNT_REQUIRED_NOT_REACHED_ERROR"
            message = "Le montant minimal requis pour la réduction n' est pas atteint."
            raise AssertionError

        # Third, check usage availability
        if not check_discount_usage_limit_validity(discount):
            code = "DISCOUNT_CHECK_USAGE_LIMIT_VALIDATION_ERROR"
            message = "Le nombre d' utilisation possible pour cette réduction est dépassé."
            raise AssertionError

        if not consumer and entity_type == DISCOUNT_USE_ENTITY_TYPES_ENUM.USER.value:
            # Pass for None users
            pass
        else:
            if not check_discount_usage_validation_conditions(discount, consumer):
                code = "DISCOUNT_CHECK_USAGE_VALIDATION_ERROR"
                message = "Le nombre d' utilisation possible pour vous est dépassé."
                raise AssertionError

            # Fourth, check validation rules
            if not check_discount_entity_validation_conditions(discount, target=entity, consumer=consumer):
                code = "DISCOUNT_CHECK_CONDITIONS_VALIDATION_ERROR"
                message = "Vous ne pouvez pas utiliser cette réduction"
                raise AssertionError

        return True, "", ""
    except Exception as exc:
        logger.warning(exc)
        return False, message, code


def get_applicable_automatic_discounts(
        target: Union[TicketT, SubscriptionTypeT, EventHighlightingTypeT],
        target_quantity: int,
        user: Union[User, None] = None,
        organization: Union[Organization, None] = None
) -> List[Discount]:
    """
    Get all automatic discounts that can be applied to a given target
    
    Args:
        target: The target entity (Ticket, SubscriptionType, EventHighlightingType)
        target_quantity: Quantity of the target being purchased
        user: The user making the purchase (for user-specific discounts)
        organization: The organization making the purchase (for org-specific discounts)
    
    Returns:
        List of applicable automatic discounts
    """
    now = timezone.now()

    # Get all active automatic discounts
    automatic_discounts = Discount.objects.filter(
        is_automatic=True,
        active=True,
        target_type=target.__class__.__name__.upper(),
    ).select_related('usage_rule', 'validation_rule')

    # Filter by validity period
    automatic_discounts = automatic_discounts.filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    )

    applicable_discounts: List[Discount] = []

    # Check each discount's conditions and rules
    for discount in automatic_discounts:
        is_available, _, _ = is_discount_available_to_user_or_organization(
            discount=discount,
            entity=target,
            entity_quantity=target_quantity,
            user=user,
            organization=organization
        )
        if is_available:
            applicable_discounts.append(discount)

    return applicable_discounts


def apply_best_automatic_discount(
        target: Union[TicketT, SubscriptionTypeT, EventHighlightingTypeT],
        target_quantity: int,
        target_price: Decimal,
        user: Union[User, None] = None,
        organization: Union[Organization, None] = None
) -> Tuple[Union[Discount, None], Decimal]:
    """
    Find and apply the best automatic discount for a given target
    
    Args:
        target: The target entity (Ticket, SubscriptionType, EventHighlightingType)
        target_quantity: Quantity of the target being purchased
        target_price: Original price of the target
        user: The user making the purchase (for user-specific discounts)
        organization: The organization making the purchase (for org-specific discounts)
    
    Returns:
        Tuple of (applied discount or None, final price after discount)
    """
    applicable_discounts = get_applicable_automatic_discounts(
        target=target,
        target_quantity=target_quantity,
        user=user,
        organization=organization
    )

    if not applicable_discounts:
        return None, target_price

    # Find the discount that gives the best value
    best_discount = None
    best_final_price = target_price

    for discount in applicable_discounts:
        final_price = get_discounted_value(
            initial_value=target_price,
            discount_calculation_info={"value": discount.validation_rule.value, "method": discount.validation_rule.type}
        )

        if final_price < best_final_price:
            best_discount = discount
            best_final_price = final_price

    if best_discount:
        # Record the usage of the discount
        consumer_type = DISCOUNT_USE_ENTITY_TYPES_STR[best_discount.target_type]
        consumer_id = str(user.id if consumer_type == "USER" else organization.id)
        use_discount(best_discount, consumer_id, consumer_type)

    return best_discount, best_final_price


def create_discount_usage_rule(discount: Discount, max_uses_per_entity: int):
    """
    Used to create discount usage rule
    @params:
            discount: [ Discount ]
            max_uses_per_entity: [ int ] The maximum time an consumer can use the discount
    """
    entity_type = DISCOUNT_USE_ENTITY_TYPES_STR.get(discount.target_type)
    usage_rule = DiscountUsageRule.objects.create(entity_type=entity_type, max_uses=max_uses_per_entity)
    return usage_rule


def create_discount_validation_rule(discount_type: DISCOUNT_TYPES_ENUM_VALUES_LIKE,
                                    discount_value: Union[float, Decimal]):
    """
    Uses to create discount validation rule
    @params:
            discount_type
            discount_value
    """
    validation_rule = DiscountValidationRule.objects.create(type=discount_type, value=discount_value)
    return validation_rule


def get_discounted_value(initial_value: float | Decimal,
                         discount_calculation_info: dict):
    """
    Used to apply discount to an initial value using a discount calculation method
    @params:
        initial_value: float or Decimal
        discount: {value: float, method: Literal['FREE_SHIPPING', 'PERCENTAGE', 'FIXED']}

    """
    new_price = 0.0
    tampon = discount_calculation_info["value"]
    if type(initial_value) is Decimal:
        tampon = Decimal(tampon)

    match discount_calculation_info["method"]:
        case "PERCENTAGE":
            new_price = initial_value * tampon
        case "FIXED":
            new_price = initial_value - tampon
        case "FREE_SHIPPING":
            pass
    if type(new_price) is Decimal:
        # Todo, review Decimal conversion logic
        new_price = new_price.quantize(Decimal('1.'), rounding=ROUND_UP)
    else:
        new_price = round(new_price)

    return new_price if new_price >= 0.0 else 0.0


def create_automatic_coupon_for_discount(discount: Discount) -> 'Coupon':
    """
    Crée un coupon automatique pour une réduction donnée
    
    Args :
        discount : La réduction pour laquelle créer un coupon
        
    Returns :
        Le coupon créé
    """
    from apps.marketing.models import Coupon

    # Créer un coupon avec un code unique
    coupon = Coupon.objects.create(
        discount=discount,
        active=True,
        is_auto_generated=True  # Marquer le coupon comme généré automatiquement
    )

    return coupon
