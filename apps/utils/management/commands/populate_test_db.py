from django.core.management.base import BaseCommand

from apps.events.populate import (
    populate_event_ticket_category_model, populate_event_ticket_model, populate_event_highlighting_type,
    populate_event_type_model, populate_event_model,
)
from apps.notifications.populate import populate_notification_type_model
from apps.organizations.populate import (
    populate_organizations_subscriptions, populate_organization_model,
    populate_organization_membership, populate_role_model,
)
from apps.users.populate import populate_admin_user_model, populate_user_model, populate_subscription_type_model, \
    populate_app_role_model
from apps.utils.populate import populate_variables, populate_country


class Command(BaseCommand):
    help = "Populate test db"

    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Admin User  ***** \n\n"
                )
            )

            populate_admin_user_model()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Admin User   ***** \n")
            )
            self.stdout.write(
                self.style.SUCCESS("\n\n \t *****  Begin populating Application Roles  ***** \n\n")
            )

            populate_app_role_model()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Application Roles   ***** \n")
            )
            self.stdout.write(
                self.style.SUCCESS("\n\n \t *****  Begin populating User  ***** \n\n")
            )

            populate_user_model()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating User   ***** \n")
            )
            self.stdout.write(
                self.style.SUCCESS("\n\n \t *****  Begin populating Role  ***** \n\n")
            )

            populate_role_model()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Role   ***** \n")
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Organization  ***** \n\n"
                )
            )

            populate_organization_model()

            self.stdout.write(
                self.style.SUCCESS(
                    "\n \t *****  End populating Organization   ***** \n"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Organization Membership  ***** \n\n"
                )
            )

            populate_organization_membership()

            self.stdout.write(
                self.style.SUCCESS(
                    "\n \t *****  End populating Organization Membership   ***** \n"
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Organization Subscriptions  ***** \n\n"
                )
            )

            populate_organizations_subscriptions()

            self.stdout.write(
                self.style.SUCCESS(
                    "\n \t *****  End populating Organization Subscriptions   ***** \n"
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Subscription Type Model  ***** \n\n"
                )
            )

            populate_subscription_type_model()

            self.stdout.write(
                self.style.SUCCESS(
                    "\n \t *****  End populating Subscription Type Model   ***** \n"
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Event Highlighting Model  ***** \n\n"
                )
            )
            populate_event_highlighting_type()

            self.stdout.write(
                self.style.SUCCESS(
                    "\n \t *****  End populating Event Highlighting Model   ***** \n"
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Event Type  ***** \n\n"
                )
            )

            populate_event_type_model()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Event Type   ***** \n")
            )

            self.stdout.write(
                self.style.SUCCESS("\n\n \t *****  Begin populating Event  ***** \n\n")
            )

            populate_event_model()
            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Event   ***** \n")
            )

            self.stdout.write(
                self.style.SUCCESS("\n\n \t *****  Begin populating Event Tickets Category  ***** \n\n")
            )

            populate_event_ticket_category_model()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Event Tickets Category   ***** \n")
            )

            self.stdout.write(
                self.style.SUCCESS("\n\n \t *****  Begin populating Event Tickets  ***** \n\n")
            )

            populate_event_ticket_model()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Event Tickets   ***** \n")
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Variables  ***** \n\n"
                )
            )

            populate_variables()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Variables   ***** \n")
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Notification Types  ***** \n\n"
                )
            )

            populate_notification_type_model()

            self.stdout.write(
                self.style.SUCCESS(
                    "\n \t *****  End populating Notification Types   ***** \n"
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Countries  ***** \n\n"
                )
            )

            populate_country()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Countries   ***** \n")
            )
        except Exception as exc:
            print(exc)


"""
from apps.events.populate import populate_event_model
from apps.utils.populate import populate_variables
from apps.notifications.populate import populate_notification_type_model

"""
