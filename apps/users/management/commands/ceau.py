import sys

from django.core import exceptions
from django.core.management.base import BaseCommand, CommandError

from apps.users import populate


class Command(BaseCommand):
    requires_migrations_checks = True
    stealth_options = ("stdin",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        try:
            self.stdout.write('\t\t\t\t #*************** Begining Populate Subscription Type ******************#')

            populate.populate_subscription_type_model()

            self.stdout.write('\t\t\t\t #*************** Finished Populate Subscription Type  ******************#')

        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)
        except exceptions.ValidationError as e:
            raise CommandError("; ".join(e.messages))
