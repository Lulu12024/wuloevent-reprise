
"""
Created on November 5, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from commons.models import AbstractCommonBaseModel
from apps.events.models.super_seller_profile import KYCStatus
from apps.organizations.models import Organization

class IdentityDocType(models.TextChoices):
    PASSPORT = 'PASSPORT', 'Passeport'
    ID_CARD = 'ID_CARD', 'Carte d’identité'
    DRIVER_LICENSE = 'DRIVER_LICENSE', 'Permis de conduire'

def kyc_upload_to(instance, subfolder):
    return f"kyc/submissions/{instance.__class__.__name__}/{subfolder}/%Y/%m/"

class SuperSellerKYCSubmission(AbstractCommonBaseModel):
    super_seller = models.ForeignKey(
        Organization, related_name="kyc_submissions",
        on_delete=models.CASCADE
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='super_seller_kyc_submitted'
    )
    status = models.CharField(
        max_length=20, choices=KYCStatus.choices, default=KYCStatus.PENDING, db_index=True
    )
    identity_type = models.CharField(
        max_length=20, choices=IdentityDocType.choices
    )

    # Cas passeport
    passport_image = models.FileField(
        upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])], verbose_name="Image Passeport"
    )

    # Cas ID Card or Driving License
    id_front = models.FileField(upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])], verbose_name="Recto")
    id_back = models.FileField(upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])], verbose_name="Verso")

    selfie_with_document = models.FileField(
        upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png'])], verbose_name="Selfie document en main"
    )
    proof_of_address = models.FileField(
        upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])], verbose_name="Justificatif de domicile"
    )
    business_registration = models.FileField(
        upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])], verbose_name="Registre de commerce"
    )

    additional_documents = models.JSONField(default=list, blank=True)

    # Review
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='super_seller_kyc_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['super_seller', 'status']),
        ]

    def __str__(self):
        return f"KYC SuperSeller {self.super_seller.name} - {self.get_status_display()}"



from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from commons.models import AbstractCommonBaseModel
from apps.events.models.seller import Seller, SellerKYCStatus
from apps.super_sellers.models.kyc_submission import IdentityDocType, kyc_upload_to

class SellerKYCSubmission(AbstractCommonBaseModel):
    seller = models.ForeignKey(Seller, related_name="kyc_submissions", on_delete=models.CASCADE)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='seller_kyc_submitted'
    )
    status = models.CharField(
        max_length=20,
        choices=SellerKYCStatus.choices,
        default=SellerKYCStatus.PENDING, db_index=True
    )
    identity_type = models.CharField(max_length=20, choices=IdentityDocType.choices)

    passport_image = models.FileField(
        upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])]
    )
    id_front = models.FileField(upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])])
    id_back = models.FileField(upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])])

    selfie_with_document = models.FileField(
        upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png'])]
    )
    proof_of_address = models.FileField(
        upload_to=kyc_upload_to, null=True, blank=True,
        validators=[FileExtensionValidator(['jpg','jpeg','png','pdf'])]
    )

    additional_documents = models.JSONField(default=list, blank=True)
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='seller_kyc_reviewed'
    )
    
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['seller', 'status']),
        ]

    def __str__(self):
        return f"KYC Seller {self.seller.user.get_full_name()} - {self.get_status_display()}"
