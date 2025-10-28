# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

"""backend URL Configuration

The `urlpatterns` list routes URLs to viewsets. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function viewsets
    1. Add an import:  from my_app import viewsets
    2. Add a URL to urlpatterns:  path('', viewsets.home, name='home')
Class-based viewsets
    1. Add an import:  from other_app.viewsets import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.utils.views import custom404

urlpatterns = [
    path("docs/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path(
        "docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger",
    ),
    path("site-tools/management-console/", admin.site.urls),
    # path("silk/", include("silk.urls", namespace="silk")),
    # path('prometheus-server/', include('django_prometheus.urls')),
    # path('__debug__/', include('debug_toolbar.urls')),
    # path('v1/admin/', admin.site.urls, name='admin_v1'),
    path("v1/api/", include("rest_framework.urls")),
    path("v1/", include("apps.users.urls")),
    path("v1/", include("apps.events.urls")),
    path("v1/", include("apps.notifications.urls")),
    path("v1/", include("apps.organizations.urls")),
    path("v1/", include("apps.utils.urls")),
    path("v1/", include("apps.marketing.urls")),
    path("v1/", include("apps.news.urls")),
    path("v1/", include("apps.chat_rooms.urls")),
]

handler404 = custom404

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
