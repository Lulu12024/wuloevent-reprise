import math
import os
import time
from datetime import datetime

from decimal import Decimal, ROUND_HALF_UP


def replace_english_words(replacers: dict, phrase: str) -> str:
    for key, value in replacers.items():
        phrase = phrase.replace(key, value)
    return phrase


class Haversine:
    def __init__(self, coord1: tuple | list, coord2: tuple | list):
        lon1, lat1 = coord1
        lon2, lat2 = coord2

        R = 6371000  # radius of Earth in meters
        phi_1 = math.radians(lat1)
        phi_2 = math.radians(lat2)

        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi_1) * math.cos(phi_2) * \
            math.sin(delta_lambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        self.meters = R * c  # output distance in meters
        # output distance in kilometers
        self.kilometers = self.meters / 1000.0
        self.miles = self.meters * 0.000621371  # output distance in miles
        self.feet = self.miles * 5280  # output distance in feet

    def get_distance(self, unit: str):
        """
        Return the havershine distance in the unit passed

        available_units = ['meters', 'kilometers', 'miles', 'feet']
        
        """
        available_units = ['meters', 'kilometers', 'miles', 'feet']
        if not unit in available_units:
            raise ValueError("This unit is not supported")
        return getattr(self, unit)


def event_types_image_upload_location(instance, filename):
    return str("img/EventTypes/Images/%s/%s" % (instance.name, filename)).lower()


def event_images_image_upload_location(instance, filename):
    return str("img/Events/%s/Images/%s" % (
        f'{instance.event.name}|{instance.event.location_name}|{instance.event.date}', filename)).lower().replace(' ',
                                                                                                                  '_')


def event_cover_upload_location(instance, filename):
    return str("img/Events/%s/Images/%s" % (
        f'{instance.name}|{instance.location_name}|{instance.date}', f'cover-{filename}')).lower().replace(' ', '_')


def profile_image_upload_location(instance, filename):
    return str("img/Users/ProfileImages/%s/%s" % (
        f'{instance.first_name} {instance.last_name} | {instance.email}', filename)).lower().replace(' ', '_')


def notification_image_upload_location(instance, filename):
    return str("img/Notifications/%s/Image/%s" % (instance.pk, f'pk-{instance.pk}-{filename}')).lower().replace(' ',
                                                                                                                '_')


def notification_icon_upload_location(instance, filename):
    return str(
        "img/Notifications/Icon/%s" % (f'Notif-{instance.title} du {instance.timestamp}-{filename}')).lower().replace(
        ' ', '_')


def eticket_qr_code_upload_location(instance, filename):
    return str("img/E-Tickets/Event %s/OrderId N°%s/%s" % (
        f'{instance.event.name}|{instance.event.date}', instance.related_order_id, f'{filename}')).lower().replace(' ',
                                                                                                                   '_')


def transaction_qr_code_upload_location(instance, filename):
    today = datetime.today().strftime('%d-%m-%Y')
    return str("img/Transactions/%s/%s/%s" % (instance.type, today, f'pk-{instance.pk}-{filename}')).lower().replace(
        ' ', '_')


def _upload_to(instance, filename):
    epoch_time = round(time.time())
    name, extension = os.path.splitext(filename)
    file = "{}_{}{}".format(name, epoch_time, extension)
    return "{}/{}".format(instance.__class__.__name__, file)


def get_blank_dict():
    return dict()


def format_to_money_string(value: Decimal, currency_symbol: str = "CFA", decimal_places: int = 0,
                           use_non_breaking_space: bool = True) -> str:
    """
    Formats a Decimal value to a CFA currency string.

    Args:
        value: The Decimal value to format.
        currency_symbol: The currency symbol to use (e.g., "CFA", "XOF", "XAF").
        decimal_places: Number of decimal places (typically 0 for CFA).
        use_non_breaking_space: If True, uses a non-breaking space for thousands separator.
                                Otherwise, uses a regular space.

    Returns:
        A string representing the formatted CFA currency.
    """
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except Exception:
            return "Invalid input"  # Or raise an error

    # Quantize to the desired number of decimal places
    quantizer = Decimal('1e-' + str(decimal_places))
    rounded_value = value.quantize(quantizer, rounding=ROUND_HALF_UP)

    # Format with comma as a temporary thousands separator
    # The {:.{dp}f} part handles the decimal places
    formatted_number_part = "{:,.{dp}f}".format(rounded_value, dp=decimal_places)

    # Replace comma with a non-breaking space (or regular space)
    thousands_separator = "\xa0" if use_non_breaking_space else " "
    if decimal_places == 0:
        # Remove .00 if no decimal places
        formatted_number_part = formatted_number_part.split('.')[0]

    formatted_number_part = formatted_number_part.replace(",", thousands_separator)

    return f"{formatted_number_part}{thousands_separator}{currency_symbol}"
