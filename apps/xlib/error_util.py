from dataclasses import dataclass

from apps.xlib.enums import ErrorEnum

ERROR_MAP = {
    ErrorEnum.RESOURCE_NOT_FOUND.value: "RESOURCE_NOT_FOUND",
    ErrorEnum.RESOURCE_RESERVED_TO_ADMIN.value: "Resource réservée aux admins",
    ErrorEnum.NO_ROLE_SPECIFIED_FOR_THE_ADMIN.value: "Le rôle de l' admin n' est pas spécifié",
    ErrorEnum.EVENT_PAST_DATE.value: "La date de l' événement est passée, vous ne pouvez pas l' ajouter ou la mettre"
                                     " à jour.",
    ErrorEnum.CANNOT_UPDATE_PASS_EVENT.value: "Vous ne pouvez pas mettre à jour un événement passé.",
    ErrorEnum.CANNOT_ADD_EVENT_ON_PASS_DATE.value: "Vous ne pouvez ajouter un évènement sur une date passée.",
    ErrorEnum.MISSING_PAGE_NUMBER.value: "Le numéro de page est manquant.",
    ErrorEnum.MISSING_DATE.value: "La date est manquante.",
    ErrorEnum.MISSING_DEVICE_REGISTRATION_ID.value: "Le token du téléphone est manquant.",
    ErrorEnum.INVALID_DATE_FORMAT.value: "Le format de la date est invalide. Utilisez le format YYYY-MM-DD.",
    ErrorEnum.MISSING_DATE_RANGE.value: "L' intervalle de dates est manquant.",
    ErrorEnum.EMPTY_OR_NULL_ORGANIZATION_PK_IN_URL.value: "La clé primaire de l' organisation est vide ou nulle dans"
                                                          " l' URL.",
    ErrorEnum.INACTIVE_ORGANIZATION.value: "Cette organisation n' est pas active.",
    ErrorEnum.SPECIFIED_PARENT_ORGANIZATION_NOT_FOUND.value: "L' organization parent spécifié n' existe pas.",
    ErrorEnum.UNVERIFIED_OWNER_ACCOUNT.value: "Le compte du propriétaire de l' organisation doit être vérifié.",
    ErrorEnum.INVALID_PHONE_NUMBER.value: "Le numéro de téléphone est invalide.",
    ErrorEnum.EMAIL_OR_PHONE_REQUIRED.value: "L' email ou le numéro de téléphone est requis.",
    ErrorEnum.USER_DOES_NOT_EXIST.value: "L' utilisateur n' existe pas ou n' est pas actif.",
    ErrorEnum.ALREADY_FOLLOWING_ORGANIZATION.value: "Vous suivez déjà cette organisation.",
    ErrorEnum.DISABLE_ACCOUNT.value: "Votre compte a été désactivé.",
    ErrorEnum.INCORRECT_EMAIL_OR_PASSWORD.value: "L' email ou le mot de passe est incorrect.",
    ErrorEnum.INCORRECT_PHONE_OR_PASSWORD.value: "Le numéro de téléphone ou le mot de passe est incorrect.",
    ErrorEnum.EMAIL_OR_PHONE_SHOULD_BE_SET.value: "L' email ou le numéro de téléphone doit être spécifié.",
    ErrorEnum.EMAIL_OR_PHONE_ALREADY_USED.value: "L' email ou le numéro de téléphone est déjà utilisé.",
    ErrorEnum.EMAIL_ALREADY_USED.value: "L' email est déjà utilisé.",
    ErrorEnum.PHONE_NUMBER_ALREADY_USED.value: "Le numéro de téléphone est déjà utilisé.",
    ErrorEnum.INSUFFICIENT_BALANCE.value: "Solde insuffisant dans votre compte pour effectuer cette opération.",
    ErrorEnum.USER_NOT_FOUND.value: "L' utilisateur n'a pas été trouvé.",
    ErrorEnum.PASSWORD_REQUIRED.value: "Le mot de passe est requis",
    ErrorEnum.PHONE_REQUIRED.value: "Numéro de téléphone requis.",
    ErrorEnum.SERVER_ERROR.value: "Erreur du serveur.",
    ErrorEnum.EVENT_UNDERGOING_VALIDATION.value: "L' événement est en cours de validation.",
    ErrorEnum.INVALID_EVENT_DATA.value: "Données invalides pour cet événement.",
    ErrorEnum.INSUFFICIENT_TICKET_QUANTITY.value: "Quantité de billets insuffisante.",
    ErrorEnum.INSUFFICIENT_ITEMS_FOR_ORDERING.value: "Le nombre de ticket choisi est insuffisant.",
    ErrorEnum.TICKET_ALREADY_DOWNLOADED.value: "Le billet a déjà été téléchargé.",
    ErrorEnum.EVENT_NOT_FOUND.value: "Événement introuvable.",
    ErrorEnum.EVENT_PARTICIPANT_LIMIT_REACHED.value: "Limite de participants atteinte pour cet événement.",
    ErrorEnum.PARTICIPANT_COUNT_EXCEEDS_LIMIT.value: "Le nombre de participants ne peut pas dépasser la limite de participants.",
    ErrorEnum.CANNOT_UPDATE_PARTICIPANT_LIMIT_WITHOUT_ACTIVE_SUBSCRIPTION.value: "Impossible de mettre à jour la limite de participants sans un abonnement actif.",
    ErrorEnum.EVENT_HIGHLIGHTING_TYPE_NOT_FOUND.value: "Type de mise en évidence d' événement introuvable.",
    ErrorEnum.PROMOTION_ALREADY_EXISTS.value: "La promotion existe déjà pour cet événement.",
    ErrorEnum.ORDER_NOT_YET_PAID.value: "La commande n'a pas encore été payée.",
    ErrorEnum.USER_ALREADY_MEMBER_OF_ORGANIZATION.value: "L' utilisateur est déjà membre de cette organisation.",
    ErrorEnum.USER_NOT_MEMBER_OF_ORGANIZATION.value: "L' utilisateur n' est pas membre de cette organisation.",
    ErrorEnum.TICKET_NOT_FOUND.value: "Billet non trouvé.",
    ErrorEnum.INVALID_TICKET.value: "Billet invalide.",
    ErrorEnum.ALREADY_USED_TICKET.value: "Le billet a déjà été utilisé.",
    ErrorEnum.PAYMENT_ALREADY_IN_PROGRESS.value: "Un paiement est déjà en cours pour cette transaction.",
    ErrorEnum.PAYMENT_TRANSACTION_NOT_FOUND.value: "Transaction de paiement introuvable.",
    ErrorEnum.WITHDRAW_TRANSACTION_NOT_FOUND.value: "Transaction de retrait introuvable.",
    ErrorEnum.INVALID_TRANSACTION_TYPE.value: "Le l' objet de la transaction est invalide.",
    ErrorEnum.GATEWAY_PAYMENT_FAILED.value: "Nous n' arrivons pas à lancer le paiement",
    ErrorEnum.TRANSACTION_ALREADY_PAID.value: "Cette transaction a déjà été payé",
    ErrorEnum.TRANSACTION_INVALID_STATUS.value: "Invalid status",
    ErrorEnum.TRANSACTION_ALREADY_COMPLETED.value: "La transaction est déjà résolu.",
    ErrorEnum.MINIMAL_AMOUNT_FOR_WITHDRAW_NOT_REACHED.value: "La valeur minimale requise pour un retrait "
                                                             "n' est pas atteinte.",
    ErrorEnum.BAD_REFRESH_TOKEN.value: "Mauvais refresh token",
    ErrorEnum.NO_ACTIVE_SUBSCRIPTION.value: "Aucun abonnement actif",
    # Discount validation errors
    ErrorEnum.WRONG_MAX_USES_PER_ENTITY.value: "Nombre d' utilisation par  utilisateur supérieur "
                                               "au nombre de réduction disponible",
    ErrorEnum.WRONG_PERCENTAGE_VALUE.value: "Le pourcentage doit être compris entre 0 et 100",
    ErrorEnum.START_DATE_AFTER_END_DATE.value: "La date de début doit précéder la date de fin",
    ErrorEnum.FIXED_AMOUNT_VALUE_GREATER_THAN_MINIMAL_VALUE.value: "La valeur fixe pour une réduction ne peut pas "
                                                                   "dépasser la valeur minimale requise pour la "
                                                                   "réduction ",
    ErrorEnum.DISCOUNT_FOR_TICKET_NOT_APPLICABLE_TO_ORGANIZATION.value: "Cette réduction n' est pas offerte pour ce ticket .",
    ErrorEnum.YOUR_ORGANIZATION_IS_NOT_CREATOR_OF_THIS_DISCOUNT.value: "Votre organisation n' est pas le "
                                                                       "créateur de cette réduction .",
    ErrorEnum.COUPON_NOT_FOUND.value: "Ce coupon n' existe pas .",
    ErrorEnum.ORGANIZATION_NOT_FOUND.value: "Cette organisation n' existe pas .",
    ErrorEnum.COUPON_WITH_THIS_CODE_ALREADY_EXISTS.value: "Un coupon avec ce code promo existe déjà.",
    ErrorEnum.APP_ROLE_DOES_NOT_EXIST.value: "Ce role n' existe pas ou n' est pas actif.",
    ErrorEnum.CHAT_ROOM_NOT_FOUND.value: "Le salon spécifié n'existe pas.",
    ErrorEnum.CHAT_ROOM_SUBSCRIPTION_NOT_FOUND.value: "Vous n'êtes pas abonné à ce salon.",
    ErrorEnum.CHAT_ROOM_ALREADY_EXISTS.value: "Ce salon existe déjà.",
    ErrorEnum.USER_NOT_MEMBER_OF_CHAT_ROOM.value: "L'utilisateur n'est pas membre de ce salon.",
    ErrorEnum.USER_ALREADY_MEMBER_OF_CHAT_ROOM.value: "L'utilisateur est déjà membre de ce salon.",
    ErrorEnum.INVALID_CHAT_ROOM_TYPE.value: "Le type de salon spécifié n'est pas valide.",
    ErrorEnum.INVALID_CHAT_ROOM_VISIBILITY.value: "La visibilité du salon spécifié n'est pas valide.",
    ErrorEnum.INVALID_CHAT_ROOM_MEMBER_TYPE.value: "Le type de membre du salon spécifié n'est pas valide.",
    ErrorEnum.INVALID_CHAT_ROOM_ACCESS_CRITERIA.value: "Les critères d'accès du salon spécifié n'sont pas valides.",
    ErrorEnum.CANNOT_ADD_CRITERIA_T0_CHAT_ROOM.value: "Impossible d'ajouter un critère d'accès au salon.",
    ErrorEnum.CHAT_ROOM_SUBSCRIPTION_ALREADY_EXISTS.value: "Vous êtes déjà abonné à ce salon.",

    ErrorEnum.EMAIL_REQUIRED.value: "L'adresse email est requise.",
    ErrorEnum.USERNAME_REQUIRED.value: "Le nom d'utilisateur est requis.",
    ErrorEnum.USER_REQUIRED.value:"L'utilisateur est requis",
    ErrorEnum.PRIVATE_CHAT_ROOM_NOT_FOUND_BETWEEN_USERS.value: "Le salon privé entre vous et l'utilisateur spécifié n'existe pas.",
}


@dataclass
class ErrorUtil:
    def get_error_detail(code: ErrorEnum, detail_message=""):
        if len(detail_message) != 0:
            return detail_message
        return ERROR_MAP[code.value]
