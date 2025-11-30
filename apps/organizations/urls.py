from django.urls import path

from apps.organizations.router import urls_patterns
from apps.organizations.views import OrganizationFollowersView, OrganizationFollowedView, \
    OrganizationFollowView, OrganizationUnFollowView
from apps.organizations.views import ScanETicketView

urlpatterns = [
    path("organizations/<str:organization_pk>/followers",
         OrganizationFollowersView.as_view()),
    path("organizations/followeds", OrganizationFollowedView.as_view()),
    path("organizations/<str:organization_pk>/follow",
         OrganizationFollowView.as_view()),
    path("organizations/<str:organization_pk>/unfollow",
         OrganizationUnFollowView.as_view()),

    path("organizations/<str:organization_pk>/scann-eticket/",
         ScanETicketView.as_view()),
]
urlpatterns += urls_patterns
