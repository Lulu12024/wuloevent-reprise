from django.core.management.base import BaseCommand

from apps.events.populate import populate_event_type_model, populate_event_highlighting_type
from apps.notifications.populate import populate_notification_type_model
from apps.organizations.populate import populate_role_model, populate_admin_organization
from apps.users.populate import populate_subscription_type_model, populate_app_role_model, populate_admin_user_model
from apps.utils.populate import populate_country, populate_variables


class Command(BaseCommand):
    help = 'Populate prod db fixtures'

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
                self.style.SUCCESS(
                    "\n\n \t *****  Begin populating Admin Organization  ***** \n\n"
                )
            )
            populate_admin_organization()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Admin Organization   ***** \n")
            )

            self.stdout.write(
                self.style.SUCCESS("\n\n \t *****  Begin populating Application Roles  ***** \n\n")
            )

            populate_app_role_model()

            self.stdout.write(
                self.style.SUCCESS("\n \t *****  End populating Application Roles   ***** \n")
            )
            self.stdout.write(self.style.SUCCESS(
                '\n\n \t *****  Begin populating Role  ***** \n\n'))

            populate_role_model()

            self.stdout.write(self.style.SUCCESS(
                '\n \t *****  End populating Role   ***** \n'))

            self.stdout.write(self.style.SUCCESS(
                '\n\n \t *****  Begin populating Subscription Type Model  ***** \n\n'))

            populate_subscription_type_model()

            self.stdout.write(self.style.SUCCESS(
                '\n \t *****  End populating Subscription Type Model   ***** \n'))

            self.stdout.write(self.style.SUCCESS(
                '\n\n \t *****  Begin populating Event Highlighting Model  ***** \n\n'))

            populate_event_highlighting_type()

            self.stdout.write(self.style.SUCCESS(
                '\n \t *****  End populating Event Highlighting Model   ***** \n'))

            self.stdout.write(self.style.SUCCESS(
                '\n\n \t *****  Begin populating Event Type  ***** \n\n'))

            populate_event_type_model()

            self.stdout.write(self.style.SUCCESS(
                '\n \t *****  End populating Event Type   ***** \n'))

            self.stdout.write(self.style.SUCCESS(
                '\n\n \t *****  Begin populating Variables  ***** \n\n'))

            populate_variables()

            self.stdout.write(self.style.SUCCESS(
                '\n \t *****  End populating Variables   ***** \n'))
            self.stdout.write(self.style.SUCCESS(
                '\n\n \t *****  Begin populating Notification Types  ***** \n\n'))

            populate_notification_type_model()

            self.stdout.write(self.style.SUCCESS(
                '\n \t *****  End populating Notification Types   ***** \n'))

            self.stdout.write(self.style.SUCCESS(
                '\n\n \t *****  Begin populating Countries  ***** \n\n'))

            populate_country()

            self.stdout.write(self.style.SUCCESS(
                '\n \t *****  End populating Countries   ***** \n'))
        except Exception as exc:
            print(exc)
