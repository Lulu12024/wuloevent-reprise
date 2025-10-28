# -*- coding: utf-8 -*-
"""
Created on December 5 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.middleware.common import CommonMiddleware
from django.utils.http import escape_leading_slashes
from rest_framework.exceptions import PermissionDenied


class TrailingSlashMiddleware(CommonMiddleware):
    """
    Custom middleware for taking care of trailing slash missing:

        - URL rewriting: Based on the APPEND_SLASH settings, append missing slashes.

        - If APPEND_SLASH is set and the initial URL doesn't end with a
          slash, and it is not found in urlpatterns, form a new URL by
          appending a slash at the end. If this new URL is found in
          urlpatterns, return an HTTP redirect to this new URL; otherwise
          process the initial URL as usual.

          This behavior can be customized by subclassing CommonMiddleware and
          overriding the response_redirect_class attribute.
    """

    response_redirect_class = HttpResponsePermanentRedirect

    def process_request(self, request):
        """
        Check for denied User-Agents and rewrite the URL based on
        settings.APPEND_SLASH and settings.PREPEND_WWW
        """

        # Check for denied User-Agents
        user_agent = request.META.get("HTTP_USER_AGENT")
        if user_agent is not None:
            for user_agent_regex in settings.DISALLOWED_USER_AGENTS:
                if user_agent_regex.search(user_agent):
                    raise PermissionDenied("Forbidden user agent")

        # Check for a redirect based on settings.PREPEND_WWW
        host = request.get_host()

        should_append_slash = False
        # Check if we also need to append a slash so we can do it all
        # with a single redirect. (This check may be somewhat expensive,
        # so we only do it if we already know we're sending a redirect,
        # or in process_response if we get a 404.)
        if self.should_redirect_with_slash(request):
            should_append_slash = True
            path = self.get_full_path_with_slash(request)
        else:
            path = request.get_full_path()

        if settings.PREPEND_WWW:
            return self.response_redirect_class(f"{request.scheme}://www.{host}{path}")

        if should_append_slash:
            return self.response_redirect_class(f"{request.scheme}://{host}{path}")

    def get_full_path_with_slash(self, request):
        """
        Return the full path of the request with a trailing slash appended.

        Raise a RuntimeError if settings.DEBUG is True and request.method is
        DELETE, POST, PUT, or PATCH.
        """
        new_path = request.get_full_path(force_append_slash=True)
        # Prevent construction of scheme relative urls.
        new_path = escape_leading_slashes(new_path)
        if request.method in ("DELETE", "POST", "PUT", "PATCH"):
            raise RuntimeError(
                "You called this URL via %(method)s, but the URL doesn't end "
                "in a slash and you have APPEND_SLASH set. Django can't "
                "redirect to the slash URL while maintaining %(method)s data. "
                "Change your form to point to %(url)s (note the trailing "
                "slash), or set APPEND_SLASH=False in your Django settings."
                % {
                    "method": request.method,
                    "url": request.get_host() + new_path,
                }
            )
        return new_path
