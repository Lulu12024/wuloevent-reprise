import json
import logging
import os

import urllib3
from django.core.management.base import BaseCommand
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator

from apps.users.models import AppPermission

logger = logging.getLogger(__name__)

requests = urllib3.PoolManager().request


class Command(BaseCommand):
    help = """
    Sync the current project endpoints base with an keycloak server resource
    cmd_sample:
        pym sync_server_resource
    """

    def __init__(self):
        super(Command, self).__init__()

    @staticmethod
    def get_endpoints_mapping():
        data = []
        _generator = OpenAPISchemaGenerator(
            info=openapi.Info(
                title="Wulo Event API Doc",
                default_version='v1',
            )
        )
        schema_path = _generator.get_schema()['paths']

        for path in list(schema_path.keys()):
            operation_names = schema_path[path].OPERATION_NAMES
            x = schema_path[path]
            for method in [y for y in x.keys() if y in operation_names]:
                operation_id = schema_path[path][method]['operationId']
                if "Admin-Operation" in operation_id:
                    operation_summary = schema_path[path][method]['summary']
                    operation_description = schema_path[path][method]['description']
                    data.append(
                        {
                            'resource_id': operation_id,
                            'resource_summary': operation_summary,
                            'resource_description': operation_description,
                            'resource_uri': path,
                            'resource_method': method.upper()
                        }
                    )
        return data

    @staticmethod
    def sync_with_local_endpoints_list_file(endpoints, output_file):
        endpoints_dict = {}
        for element in endpoints:
            """
            resource_uri
            method
            """
            endpoints_dict[element['resource_id']] = {
                "required_roles": [],
                "resource_uri": element['resource_uri'],
                "method": element['method']
            }

        if not os.path.exists(output_file):
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "w") as outfile:
                outfile.write(json.dumps(endpoints_dict))
        else:
            with open(output_file, 'r+') as outfile:
                try:
                    old_data = json.load(outfile)
                except Exception as exc:
                    logger.warning(exc)
                    old_data = {}

                endpoints_dict.update((k, old_data[k]) for k in set(endpoints_dict).intersection(old_data))
                outfile.seek(0)
                outfile.truncate()
                json.dump(endpoints_dict, outfile)

    def handle(self, **options):
        self.stdout.write(
            self.style.SUCCESS('\n \n Start syncing ... \n \n ')
        )
        endpoints_list_file = "./admin-role-endpoints.json"

        # endpoints = self.get_endpoints_mapping()
        endpoints = []

        # print(endpoints)
        # self.sync_with_local_endpoints_list_file(endpoints, endpoints_list_file)

        for item in endpoints:
            data = {
                'name': item['resource_description'],
                'entity': item['resource_summary'],
                'method': item['resource_method'],
            }
            permission, created = AppPermission.objects.get_or_create(
                codename=item['resource_id'],
                defaults=data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'\n \n {permission.name} Successfully Created. \n \n ')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'\n \n {permission.name} Already Exists. \n \n ')
                )

        self.stdout.write(
            self.style.SUCCESS('\n \n Successfully sync. \n \n ')
        )
