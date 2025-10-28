from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import (
    ComponentRegistry,
)


class CustomAutoSchema(AutoSchema):
    def get_operation(
            self, path, path_regex, path_prefix, method, registry: ComponentRegistry
    ):
        if method.upper() == "PATCH":
            return {}
        return super().get_operation(path, path_regex, path_prefix, method, registry)

    def get_operation_id(self):
        operation_id = list(map(str.title, super().get_operation_id().split("_")))
        return " ".join(operation_id[-1:] + operation_id[:-1])
