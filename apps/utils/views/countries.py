# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.utils.models import Country
from apps.utils.serializers import CountrySerializer


@method_decorator(name="list", decorator=cache_page(60 * 60 * 2))
class CountriesViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    authentication_classes = [JWTAuthentication]
    serializer_class = CountrySerializer

    permission_classes_by_action = {
        'create': [permissions.IsAuthenticated],
        'retrieve': [permissions.AllowAny],
        'list': [permissions.AllowAny],
        'destroy': [permissions.IsAuthenticated, permissions.IsAdminUser],
    }

    @extend_schema(
        responses={200: CountrySerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, url_path='covered')
    def get_covered_countries_list(self, request, *args, **kwargs):
        covered_countries = self.get_queryset().filter(is_covered=True)
        covered_countries_serializer = self.get_serializer(covered_countries, many=True)
        return Response(covered_countries_serializer.data, status=status.HTTP_200_OK)

    def get_permissions(self):
        try:
            # return permission_classes depending on `action`
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        except KeyError:
            # action is not set return default permission_classes
            return [permission() for permission in self.permission_classes]
