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


class IsAdminOrSellerSelfOrSellerOfSuperSeller(permissions.BasePermission):
    """
    Accès:
    - Admin app: accès à tous.
    - Super-vendeur: accès uniquement aux vendeurs de sa propre organisation.
    - Vendeur: uniquement à son propre profil.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        # Admin app
        if getattr(user, "is_app_admin", False):
            return True

        # Vendeur
        seller_profile = getattr(request, "seller_profile", None)
        if seller_profile and obj.pk == seller_profile.pk:
            return True

        # Super-vendeur (vérifié)
        org = getattr(request, "organization", None) or getattr(request, "super_seller_organization", None)
        if org:
            return obj.super_seller_id == org.pk

        return False


#============

class IsSuperSellerMember(permissions.BasePermission):
    """
    Autorise les membres/owner/coordinator d'une organisation Super-Vendeur.
    Option : exiger que l'orga soit KYC VERIFIED.
    
    Usage côté vue:
        require_verified_super_seller = True  # (par défaut True) -> exige KYC vérifié
        organization_id : lu via body ou query param par resolve_organization_from_request
    """
    message = "Accès refusé : vous devez être membre d'un Super-Vendeur (KYC vérifié)."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            self.message = "Authentification requise."
            return False

        org = resolve_organization_from_request(view, request)
        if org is None:
            self.message = "organization_id manquant ou organisation introuvable."
            return False

        # est-ce que l'orga doit être vérifiée ?
        require_verified = getattr(view, "require_verified_super_seller", True)

        # vérifie que c'est un super-vendeur
        if not org.is_super_seller():
            self.message = "L'organisation n'est pas de type Super-Vendeur."
            return False

        # vérifie KYC si exigé
        if require_verified and not org.is_super_seller_verified():
            self.message = "Le Super-Vendeur n'a pas un KYC vérifié."
            return False

        # Vérifie rôle utilisateur dans l'orga
        role = user.get_user_role_for_organization(org)
        if role not in ("OWNER", "MEMBER", "COORDINATOR"):
            self.message = "Vous devez être membre de l'organisation (OWNER/MEMBER/COORDINATOR)."
            return False

        # Expose dans la vue si besoin
        setattr(view, "organization", org)
        setattr(request, "organization", org)
        return True

    def has_object_permission(self, request, view, obj):
        """
        Réutilise la même logique au niveau objet, ex: sur un objet rattaché à une orga.
        """
        user = request.user
        if not user or not user.is_authenticated:
            self.message = "Authentification requise."
            return False

        org = getattr(obj, "super_seller", None) or getattr(obj, "organization", None)
        if org is None:
            self.message = "Organisation introuvable pour l'objet ciblé."
            return False

        require_verified = getattr(view, "require_verified_super_seller", True)

        if not org.is_super_seller():
            self.message = "L'organisation n'est pas de type Super-Vendeur."
            return False

        if require_verified and not org.is_super_seller_verified():
            self.message = "Le Super-Vendeur n'a pas un KYC vérifié."
            return False

        role = user.get_user_role_for_organization(org)
        if role not in ("OWNER", "MEMBER", "COORDINATOR"):
            self.message = "Vous devez être membre de l'organisation (OWNER/MEMBER/COORDINATOR)."
            return False

        return True


class IsSellerSelf(permissions.BasePermission):
    """
    Le vendeur ne peut soumettre/voir que ses propres informations (ex: KYC).
    Repose sur `request.seller_profile`.
    """
    message = "Accès refusé : vous ne pouvez agir que pour votre propre profil vendeur."

    def has_permission(self, request, view):
        seller = getattr(request, "seller_profile", None)
        ok = bool(seller and seller.user_id == request.user.id)
        if not ok and request.user.is_authenticated:
            self.message = "Vous n'êtes pas le vendeur concerné."
        return ok


class IsSuperSellerOwnerOfSellerOrAdmin(permissions.BasePermission):
    """
    Admin : accès total.
    Super-vendeur : accès uniquement aux vendeurs de sa propre organisation.
    
    Cette permission s'appuie sur:
      - request.organization / request.super_seller_organization (middleware)
      - ou `resolve_organization_from_request` si nécessaire
      - un `seller_id` fourni dans route/kwargs ou body.
    """
    message = "Accès refusé : vous n'êtes pas propriétaire de ce vendeur."

    def _get_seller(self, view, request):
        # 1) si la vue expose un helper
        if hasattr(view, "get_seller_object"):
            seller_id = view.kwargs.get("seller_id") or request.data.get("seller_id") or request.query_params.get("seller_id")
            if not seller_id:
                return None
            return view.get_seller_object(seller_id)

        # 2) fallback : import local pour éviter circular import
        from apps.events.models.seller import Seller
        seller_id = view.kwargs.get("seller_id") or request.data.get("seller_id") or request.query_params.get("seller_id")
        if not seller_id:
            return None
        return get_object_or_404(Seller, pk=seller_id)

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            self.message = "Authentification requise."
            return False

        # Admin OK
        if getattr(user, "is_app_admin", False):
            return True

        # On tente de résoudre le vendeur ciblé
        seller = self._get_seller(view, request)
        if not seller:
            # Si pas de seller à ce niveau, on laisse passer, la check se fera en has_object_permission
            return True

        # résout org du super-vendeur
        org = getattr(request, "organization", None) or getattr(request, "super_seller_organization", None)
        if not org:
            org = resolve_organization_from_request(view, request)

        if not org:
            self.message = "Organisation super-vendeur non résolue."
            return False

        if seller.super_seller_id != org.pk:
            self.message = "Ce vendeur n'appartient pas à votre organisation."
            return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        Si `obj` est un Seller, on applique la même politique ADMIN ou super-vendeur propriétaire.
        """
        user = request.user
        if getattr(user, "is_app_admin", False):
            return True

        # obj peut être un Seller ou un modèle rattaché; on remonte Seller proprement
        seller = getattr(obj, "seller", None) or obj
        seller_id = getattr(seller, "pk", None)
        if not seller_id:
            self.message = "Objet cible invalide (seller introuvable)."
            return False

        org = getattr(request, "organization", None) or getattr(request, "super_seller_organization", None)
        if not org:
            org = resolve_organization_from_request(view, request)

        if not org or seller.super_seller_id != org.pk:
            self.message = "Accès refusé : vendeur non rattaché à votre Super-Vendeur."
            return False

        return True


class IsAdminOrSuperSellerMember(permissions.BasePermission):
    """
    Admin ou membre de l'organisation super-vendeur (OWNER/MEMBER/COORDINATOR).
    Option : exiger KYC vérifié.
    """
    message = "Accès réservé aux admins ou aux membres d'un Super-Vendeur."

    def has_permission(self, request, view):
        if getattr(request.user, "is_app_admin", False):
            return True

        org = resolve_organization_from_request(view, request)
        if org is None:
            self.message = "organization_id manquant."
            return False

        require_verified = getattr(view, "require_verified_super_seller", True)
        if not org.is_super_seller():
            self.message = "L'organisation n'est pas de type Super-Vendeur."
            return False
        if require_verified and not org.is_super_seller_verified():
            self.message = "Le Super-Vendeur n'a pas un KYC vérifié."
            return False

        role = request.user.get_user_role_for_organization(org)
        if role not in ("OWNER", "MEMBER", "COORDINATOR"):
            self.message = "Vous devez être membre de l'organisation."
            return False

        setattr(view, "organization", org)
        setattr(request, "organization", org)
        return True
