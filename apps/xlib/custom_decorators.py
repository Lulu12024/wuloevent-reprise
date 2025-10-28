from typing import Any

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers


def custom_paginated_response(name: str, code: int, serializer_class: Any, description: str = "", ):
    fields = {
        "count": serializers.IntegerField(),
        "next": serializers.CharField(),
        "previous": serializers.CharField(),
        "results": serializer_class(many=True)
    }
    return extend_schema(description=description, responses={code: inline_serializer(name=name, fields=fields)})
