# -*- coding: utf-8 -*-
"""
Created on  20225

@author:
    Beaudelaire Lahoume, alias root-lr
"""

from django.shortcuts import get_object_or_404
from apps.organizations.models import Organization

def resolve_organization_from_request(view, request):
    """
    Ordre de résolution:
    1) view.organization si déjà posée par la view
    2) kwargs: 'organization_id' ou 'org_id'
    3) body: request.data['organization_id'] ou ['org_id']
    """
    if getattr(view, "organization", None):
        return view.organization

    org_id = (
        getattr(view, "kwargs", {}).get("organization_id")
        or getattr(view, "kwargs", {}).get("org_id")
        or request.data.get("organization_id")
        or request.data.get("org_id")
    )
    if not org_id:
        return None
    return get_object_or_404(Organization, pk=org_id)
