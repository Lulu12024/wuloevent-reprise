# -*- coding: utf-8 -*-
"""
Created on October 29, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""


import logging
import typing

from django.http import HttpRequest
from rest_framework import permissions
from apps.organizations.utils import resolve_organization_from_request
logger = logging.getLogger(__name__)
logger.setLevel("INFO")

class IsVerifiedSuperSellerAndMember(permissions.BasePermission):
    """
    Autorise uniquement si:
    - l'organisation ciblée est un Super-Vendeur ET KYC VERIFIED
    - l'utilisateur est OWNER/MEMBER/COORDINATOR de cette organisation
    """
    message = "Accès refusé: orga non autorisée ou vous n'êtes pas membre habilité."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            self.message = "Authentification requise."
            return False

        org = resolve_organization_from_request(view, request)
        if org is None:
            self.message = "organization_id manquant."
            return False

        # 1) Vérif super-vendeur + KYC
        # if not org.is_super_seller_verified():
        #     self.message = "L'organisation n'est pas un Super-Vendeur vérifié (KYC)."
        #     return False

        # 2) Vérif appartenance/autorisation
        role = user.get_user_role_for_organization(org)
        if role not in ("OWNER", "MEMBER", "COORDINATOR"):
            self.message = "Vous devez être membre de l'organisation pour inviter."
            return False

        setattr(view, "organization", org)
        return True

    def has_object_permission(self, request, view, obj):
        """
        Si tu utilises des permissions objet (ex: sur une Invitation spécifique),
        on réapplique la même logique en récupérant l'orga depuis l'objet.
        """
        user = request.user
        if not user or not user.is_authenticated:
            self.message = "Authentification requise."
            return False

        org = getattr(obj, "super_seller", None) or getattr(obj, "organization", None)
        if org is None:
            self.message = "Organisation introuvable pour l'objet ciblé."
            return False

        if not org.is_super_seller_verified():
            self.message = "L'organisation n'est pas un Super-Vendeur vérifié (KYC)."
            return False

        role = user.get_user_role_for_organization(org)
        if role not in ("OWNER", "MEMBER", "COORDINATOR"):
            self.message = "Vous devez être membre de l'organisation."
            return False

        return True

class IsActiveSeller(permissions.BasePermission):
    """
    Permission pour vérifier si le vendeur est actif.
    """
    def has_permission(self, request, view):
        seller = getattr(request, "seller_profile", None)
        return bool(seller and seller.can_sell())
