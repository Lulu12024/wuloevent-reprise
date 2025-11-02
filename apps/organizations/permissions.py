# -*- coding: utf-8 -*-
"""
Created on April 29 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
import typing

from django.http import HttpRequest
from rest_framework import permissions
logger = logging.getLogger(__name__)
logger.setLevel("INFO")

class IsOrganizationActive(permissions.BasePermission):
    message = 'ORGANIZATION_OWNER_ACCOUNT_MUST_BE_VERIFIED'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')
            return organization.is_owner_verified
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(request.user and request.user.is_authenticated and obj.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(obj,
                                                                                                          'MEMBER'))
        return super().has_object_permission(request, view, obj)


class OrganizationHaveActiveSubscription(permissions.BasePermission):
    message = "THE_ORGANIZATION_DOES_NOT_HAVE_ACTIVE_SUBSCRIPTION"

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        assert hasattr(
            view,
            'parent_obj'), "Parent Object not in nested view attrs. Try to check or create mixing for adding parent object."
        organization = getattr(view, 'parent_obj')
        return organization.have_active_subscription


class IsOrganizationOwner(permissions.BasePermission):
    message = 'YOU_ARE_NOT_ORGANIZATION_OWNER'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        # assert hasattr(
        #     view, 'parent_obj'), "Parent Object not in wested view attrs.
        #     Try to check or create mixing for adding parent object."
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')
            return bool(
                request.user and request.user.is_authenticated and request.user == organization.owner)
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(
                request.user and request.user.is_authenticated and request.user == obj.owner)
        return super().has_object_permission(request, view, obj)


class IsOrganizationCoordinator(permissions.BasePermission):
    message = 'YOU_ARE_NOT_ORGANIZATION_COORDINATOR'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        # assert hasattr(
        #     view, 'parent_obj'), "Parent Object not in wested view attrs. Try to check or create mixing for adding parent object."
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')
            return bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(organization,
                                                                                                          'COORDINATOR'))
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(obj,
                                                                                                          'COORDINATOR'))
        return super().has_object_permission(request, view, obj)


class IsOrganizationEventManager(permissions.BasePermission):
    message = 'YOU_MUST_BE_ORGANIZATION_OWNER_OR_MEMBER_WITH_COORDINATOR_ROLES'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        # assert hasattr(
        #     view, 'parent_obj'), "Parent Object not in nested view attrs. Try to check or create mixing for adding parent object."
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')

            return bool(request.user and request.user.is_authenticated and organization.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(organization,
                                                                                                          'COORDINATOR'))
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(request.user and request.user.is_authenticated and obj.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(obj,
                                                                                                          'COORDINATOR'))
        return super().has_object_permission(request, view, obj)


class IsOrganizationMember(permissions.BasePermission):
    message = 'YOU_ARE_NOT_ORGANIZATION_MEMBER'

    def has_permission(self, request: HttpRequest, view: typing.Any) -> bool:
        # assert hasattr(
        #     view, 'parent_obj'), "Parent Object not in wested view attrs. Try to check or create mixing for adding parent object."
        if hasattr(view, 'parent_obj'):
            organization = getattr(view, 'parent_obj')
            return bool(request.user and request.user.is_authenticated and organization.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(
                    organization, 'MEMBER'))
        return super().has_permission(request, view)

    def has_object_permission(self, request: HttpRequest, view: typing.Any, obj: typing.Any) -> bool:
        if not hasattr(view, 'parent_obj'):
            return bool(request.user and request.user.is_authenticated and obj.is_owner(request.user)) or bool(
                request.user and request.user.is_authenticated and request.user.check_organization_access(obj,
                                                                                                          'MEMBER'))
        return super().has_object_permission(request, view, obj)
    



class IsSuperSeller(permissions.BasePermission):
    """
    Permission : L'utilisateur doit appartenir à une organisation super-vendeur.
    
    Vérifie que :
    - L'utilisateur est authentifié
    - L'utilisateur est membre d'une organisation
    - L'organisation est de type SUPER_SELLER
    """
    
    message = "Vous devez être membre d'une organisation Super-Vendeur pour accéder à cette ressource."
    
    def has_permission(self, request, view):
        # Vérifier l'authentification
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Vérifier si l'utilisateur est membre d'une organisation
        from apps.organizations.models import OrganizationMember
        
        try:
            # Chercher les organisations dont l'utilisateur est membre
            member = OrganizationMember.objects.filter(
                user=request.user,
                active=True
            ).select_related('organization').first()
            
            if not member:
                logger.warning(
                    f"Accès refusé : {request.user.email} n'est membre d'aucune organisation"
                )
                return False
            
            organization = member.organization
            
            # Vérifier que c'est une organisation super-vendeur
            if organization.organization_type != 'SUPER_SELLER':
                logger.warning(
                    f"Accès refusé : {request.user.email} n'appartient pas à un super-vendeur "
                    f"(Type: {organization.organization_type})"
                )
                return False
            
            # Stocker l'organisation dans la request pour utilisation ultérieure
            request.super_seller_organization = organization
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur vérification permission IsSuperSeller : {e}")
            return False


class IsSuperSellerVerified(permissions.BasePermission):
    """
    Permission : L'utilisateur doit appartenir à un super-vendeur VÉRIFIÉ (KYC validé).
    
    Vérifie que :
    - L'utilisateur est authentifié
    - L'utilisateur est membre d'une organisation super-vendeur
    - Le profil super-vendeur existe
    - Le KYC est vérifié (status = VERIFIED)
    - L'organisation et le profil sont actifs
    
    UTILISÉ POUR : Création d'événements éphémères (TICKET-005)
    """
    
    message = (
        "Vous devez être membre d'un super-vendeur vérifié (KYC validé) "
        "pour accéder à cette ressource."
    )
    
    def has_permission(self, request, view):
        # Vérifier l'authentification
        if not request.user or not request.user.is_authenticated:
            logger.warning("Accès refusé : utilisateur non authentifié")
            return False
        
        from apps.organizations.models import OrganizationMember
        
        try:
            # Chercher l'organisation super-vendeur de l'utilisateur
            member = OrganizationMember.objects.filter(
                user=request.user,
                active=True
            ).select_related('organization').first()
            
            if not member:
                logger.warning(
                    f"Accès refusé : {request.user.email} n'est membre d'aucune organisation"
                )
                return False
            
            organization = member.organization
            
            # 1. Vérifier que c'est un super-vendeur
            if organization.organization_type != 'SUPER_SELLER':
                logger.warning(
                    f"Accès refusé : Organisation {organization.name} n'est pas un super-vendeur"
                )
                return False
            
            # 2. Vérifier que le profil super-vendeur existe
            if not hasattr(organization, 'super_seller_profile'):
                logger.warning(
                    f"Accès refusé : Organisation {organization.name} n'a pas de profil super-vendeur"
                )
                return False
            
            profile = organization.super_seller_profile
            
            # 3. Vérifier que le profil est actif
            if not profile.active:
                logger.warning(
                    f"Accès refusé : Profil super-vendeur de {organization.name} est inactif"
                )
                return False
            
            # 4. Vérifier que le KYC est vérifié
            if not profile.is_kyc_verified():
                logger.warning(
                    f"Accès refusé : KYC non vérifié pour {organization.name} "
                    f"(Statut: {profile.get_kyc_status_display()})"
                )
                self.message = (
                    f"Le KYC de votre organisation doit être vérifié. "
                    f"Statut actuel : {profile.get_kyc_status_display()}"
                )
                return False
            
            # 5. Vérifier que l'organisation est active
            if not organization.active:
                logger.warning(
                    f"Accès refusé : Organisation {organization.name} est inactive"
                )
                return False
            
            # Tout est OK - Stocker les informations dans la request
            request.super_seller_organization = organization
            request.super_seller_profile = profile
            request.organization_member = member
            
            logger.info(
                f"Accès autorisé : {request.user.email} "
                f"(Super-vendeur vérifié : {organization.name})"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Erreur vérification permission IsSuperSellerVerified pour "
                f"{request.user.email} : {e}",
                exc_info=True
            )
            return False


class IsSeller(permissions.BasePermission):
    """
    Permission : L'utilisateur doit être un vendeur actif.
    
    Vérifie que :
    - L'utilisateur est authentifié
    - L'utilisateur a un profil vendeur
    - Le vendeur est actif
    - Le super-vendeur associé est vérifié
    """
    
    message = "Vous devez être un vendeur actif pour accéder à cette ressource."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        from apps.organizations.models import Seller
        
        try:
            # Chercher le profil vendeur
            seller = Seller.objects.filter(
                user=request.user,
                active=True
            ).select_related('super_seller', 'super_seller__super_seller_profile').first()
            
            if not seller:
                logger.warning(
                    f"Accès refusé : {request.user.email} n'a pas de profil vendeur actif"
                )
                return False
            
            # Vérifier que le vendeur peut opérer
            if not seller.can_sell():
                logger.warning(
                    f"Accès refusé : Vendeur {seller} ne peut pas opérer"
                )
                return False
            
            # Stocker dans la request
            request.seller = seller
            request.super_seller_organization = seller.super_seller
            
            logger.info(f"Accès autorisé : Vendeur {seller.user.get_full_name()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur vérification permission IsSeller : {e}")
            return False


class IsSellerOrSuperSeller(permissions.BasePermission):
    """
    Permission : L'utilisateur doit être soit un vendeur, soit un super-vendeur.
    
    Utilisé pour les endpoints accessibles aux deux types d'utilisateurs.
    """
    
    message = "Vous devez être vendeur ou super-vendeur pour accéder à cette ressource."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Essayer d'abord en tant que super-vendeur
        super_seller_check = IsSuperSellerVerified()
        if super_seller_check.has_permission(request, view):
            request.user_type = 'super_seller'
            return True
        
        # Sinon essayer en tant que vendeur
        seller_check = IsSeller()
        if seller_check.has_permission(request, view):
            request.user_type = 'seller'
            return True
        
        logger.warning(
            f"Accès refusé : {request.user.email} n'est ni vendeur ni super-vendeur"
        )
        return False


class CanManageSellers(permissions.BasePermission):
    """
    Permission : Le super-vendeur peut gérer ses vendeurs.
    
    Vérifie que l'utilisateur est un super-vendeur vérifié.
    """
    
    message = "Seuls les super-vendeurs vérifiés peuvent gérer leurs vendeurs."
    
    def has_permission(self, request, view):
        # Réutiliser la logique de IsSuperSellerVerified
        return IsSuperSellerVerified().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        """
        Vérifie que le super-vendeur ne peut gérer que SES vendeurs.
        
        Args:
            obj: Instance de Seller
        """
        if not hasattr(request, 'super_seller_organization'):
            return False
        
        # Vérifier que le vendeur appartient à ce super-vendeur
        if hasattr(obj, 'super_seller'):
            return obj.super_seller == request.super_seller_organization
        
        return False


class CanAccessEphemeralEvent(permissions.BasePermission):
    """
    Permission : Peut accéder aux événements éphémères.
    
    Vérifie que :
    - Super-vendeur créateur de l'événement, OU
    - Vendeur affilié au super-vendeur créateur, OU
    - Admin/Staff
    """
    
    message = "Vous n'avez pas accès à cet événement éphémère."
    
    def has_object_permission(self, request, view, obj):
        """
        Args:
            obj: Instance d'Event (éphémère)
        """
        if not obj.is_ephemeral:
            return True  # Événements publics accessibles à tous
        
        # Staff/Admin peuvent tout voir
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        from apps.organizations.models import OrganizationMember, Seller
        
        try:
            # Vérifier si super-vendeur créateur
            if hasattr(obj, 'created_by_super_seller') and obj.created_by_super_seller:
                member = OrganizationMember.objects.filter(
                    user=request.user,
                    organization=obj.created_by_super_seller,
                    active=True
                ).first()
                
                if member:
                    return True
            
            # Vérifier si vendeur affilié au super-vendeur créateur
            if hasattr(obj, 'created_by_super_seller') and obj.created_by_super_seller:
                seller = Seller.objects.filter(
                    user=request.user,
                    super_seller=obj.created_by_super_seller,
                    status='ACTIVE',
                    active=True
                ).first()
                
                if seller:
                    return True
            
            logger.warning(
                f"Accès refusé événement éphémère : {request.user.email} "
                f"n'a pas accès à l'événement {obj.name}"
            )
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur vérification accès événement éphémère : {e}")
            return False
