import logging
import zoneinfo

from django.utils import timezone

logger = logging.getLogger(__name__)


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # get django_timezone from cookie
            tzname = request.headers.get("X-User-TimeZone")
            if tzname:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            else:
                timezone.deactivate()
        except Exception as exc:
            logger.info(exc)
            timezone.deactivate()

        return self.get_response(request)
