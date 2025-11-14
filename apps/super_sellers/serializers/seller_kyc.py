
"""
Created on November 5, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""


from rest_framework import serializers
from apps.super_sellers.models.kyc_submission import SellerKYCSubmission, IdentityDocType
from apps.events.models.seller import SellerKYCStatus

class SellerKYCSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerKYCSubmission
        fields = (
            "identity_type",
            "passport_image", "id_front", "id_back",
            "selfie_with_document", "proof_of_address",
            "additional_documents",
        )
        extra_kwargs = {"additional_documents": {"required": False}}

    def validate(self, attrs):
        identity_type = attrs.get("identity_type")

        if identity_type == IdentityDocType.PASSPORT:
            if not attrs.get("passport_image"):
                raise serializers.ValidationError("Pour un passeport, `passport_image` est requis.")
        else:
            if not attrs.get("id_front") or not attrs.get("id_back"):
                raise serializers.ValidationError("Pour une pièce d'identité, `id_front` et `id_back` sont requis.")

        if not attrs.get("selfie_with_document"):
            raise serializers.ValidationError("`selfie_with_document` est requis.")
        if not attrs.get("proof_of_address"):
            raise serializers.ValidationError("`proof_of_address` est requis.")

        return attrs


class SellerKYCReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["verify", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if attrs["action"] == "reject" and not attrs.get("reason"):
            raise serializers.ValidationError("Un motif de rejet est requis.")
        return attrs
