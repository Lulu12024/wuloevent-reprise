# -*- coding: utf-8 -*-
"""
Created on June 21 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.xlib.enums import ErrorEnum
from apps.xlib.error_util import ErrorUtil, ERROR_MAP


def custom404(request, exception=None):
    return JsonResponse({
        'status_code': 404,
        'error': ErrorUtil.get_error_detail(ErrorEnum.RESOURCE_NOT_FOUND)
    })


@method_decorator(name="get_errors_list", decorator=cache_page(60 * 60 * 5))
class ErrorsViewSet(GenericViewSet):
    authentication_classes = [JWTAuthentication]
    http_method_names = ['get']
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: [{}]},
    )
    @action(methods=["GET"], detail=False, url_path='map')
    def get_errors_list(self, request, *args, **kwargs):
        return Response(ERROR_MAP, status=HTTP_200_OK)
