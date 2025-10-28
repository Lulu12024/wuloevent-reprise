# -*- coding: utf-8 -*-
"""
Created on April 28 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.urls import path

from apps.users import views
from apps.users.router import router

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/register/pseudo-anonymous/", views.PseudoAnonymousRegisterView.as_view(), name='register-pseudo-anonymous'),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/check-user/", views.CheckUserExistsView.as_view(), name='check-user-exists'),
    path("auth/logout/", views.LogoutView.as_view()),
    path("auth/admin/login/", views.AdminLoginView.as_view()),
    path("auth/refresh/", views.RefreshView.as_view()),
    path("auth/validation/send/", views.SendAccountValidationRequestView.as_view()),
    path("auth/validation/check/", views.AccountValidationValidateCodeView.as_view()),
    path("auth/update-password/", views.ChangePasswordView.as_view()),
    path("auth/forgot-password/", views.SendPasswordResetRequestView.as_view()),
    path("auth/reset-password/", views.ResetPasswordValidateCodeView.as_view()),

    path("accounts/me/", views.RetrieveUserView.as_view()),
    path("accounts/organization/me/", views.RetrieveUserOrganizationInfoView.as_view()),
    path("accounts/me/profile/image/", views.ManageUserProfileImageView.as_view()),
    path("accounts/me/update/", views.UpdateUserInfosView.as_view()),
    path("accounts/me/update-phone-or-email/", views.UpdateUserEmailOrPhoneView.as_view()),
    path("accounts/me/delete/", views.DeactivateUserView.as_view()),
    # path("accounts/delete/", viewsets.DestroyUserView.as_view()),
    path("accounts/users/", views.UsersListView.as_view()),

    # path("accounts/me/followers", viewsets.UserFollowersViews.as_view()),
    # path("accounts/me/followeds", viewsets.UserFollowedViews.as_view()),
    # path("accounts/me/follow-user", viewsets.UserFollowView.as_view()),
    # path("accounts/me/unfollow-user", viewsets.UserUnFollowView.as_view()),

    # path("accounts/me/follow-location-point", viewsets.LocationPointFollowView.as_view()),
    # path("accounts/me/unfollow-location-point", viewsets.LocationPointUnFollowView.as_view()),
    # path("accounts/me/location-points-followed", viewsets.LocationPointsFollowedViews.as_view()),

    # path("accounts/me/follow-location-area", viewsets.LocationAreaFollowView.as_view()),
    # path("accounts/me/unfollow-location-area", viewsets.LocationAreaUnFollowView.as_view()),
    # path("accounts/me/location-areas-followed", viewsets.LocationAreasFollowedViews.as_view()),

]
urlpatterns += router.urls
