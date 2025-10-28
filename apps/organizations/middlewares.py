# -*- coding: utf-8 -*-
"""
Created on April 27, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
import re

from django.utils.deprecation import MiddlewareMixin

from apps.organizations.models import Organization
from backend.commons import custom_get_object_or_404 as get_object_or_404

logger = logging.getLogger(__name__)


class OrganizationAuthentication(MiddlewareMixin):
    def process_view(self, request, view_func, *view_args, **view_kwargs):
        organization = None
        path = request.path
        x = re.findall(r"/organizations/([A-Za-z0-9\-]+)", path)
        try:
            uuid = x[0]

            organization = get_object_or_404(Organization.objects.select_related("owner").all(), **{'pk': uuid})
        except Exception as exc:
            logger.debug(exc)
        request.organization = organization
