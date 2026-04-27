"""Tornado handlers for logging into the Jupyter Server."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import os
import re
import uuid
from urllib.parse import urlparse

from tornado.escape import url_escape

from ..base.handlers import JupyterHandler
from .decorator import allow_unauthenticated
from .security import passwd_check, set_password


class LoginFormHandler(JupyterHandler):
    """The basic tornado login handler

    accepts login form, passed to IdentityProvider.process_login_form.
    """

    def _render(self, message=None):
        """Render the login form."""
        pass

    def _redirect_safe(self, url, default=None):
        """Redirect if url is on our PATH

        Full-domain redirects are allowed if they pass our CORS origin checks.

        Otherwise use default (self.base_url if unspecified).
        """
        pass

    @allow_unauthenticated
    def get(self):
        """Get the login form."""
        pass

    @allow_unauthenticated
    def post(self):
        """Post a login."""
        pass


class LegacyLoginHandler(LoginFormHandler):
    """Legacy LoginHandler, implementing most custom auth configuration.

    Deprecated in jupyter-server 2.0.
    Login configuration has moved to IdentityProvider.
    """

    @property
    def hashed_password(self):
        pass

    def passwd_check(self, a, b):
        """Check a passwd."""
        pass

    @allow_unauthenticated
    def post(self):
        """Post a login form."""
        pass

    @classmethod
    def set_login_cookie(cls, handler, user_id=None):
        """Call this on handlers to set the login cookie for success"""
        pass

    auth_header_pat = re.compile(r"token\s+(.+)", re.IGNORECASE)

    @classmethod
    def get_token(cls, handler):
        """Get the user token from a request

        Default:

        - in URL parameters: ?token=<token>
        - in header: Authorization: token <token>
        """
        pass

    @classmethod
    def should_check_origin(cls, handler):
        """DEPRECATED in 2.0, use IdentityProvider API"""
        pass

    @classmethod
    def is_token_authenticated(cls, handler):
        """DEPRECATED in 2.0, use IdentityProvider API"""
        pass

    @classmethod
    def get_user(cls, handler):
        """DEPRECATED in 2.0, use IdentityProvider API"""
        pass

    @classmethod
    def get_user_cookie(cls, handler):
        """DEPRECATED in 2.0, use IdentityProvider API"""
        pass

    @classmethod
    def get_user_token(cls, handler):
        """DEPRECATED in 2.0, use IdentityProvider API"""
        pass

    @classmethod
    def validate_security(cls, app, ssl_options=None):
        """DEPRECATED in 2.0, use IdentityProvider API"""
        pass

    @classmethod
    def password_from_settings(cls, settings):
        """DEPRECATED in 2.0, use IdentityProvider API"""
        pass

    @classmethod
    def get_login_available(cls, settings):
        """DEPRECATED in 2.0, use IdentityProvider API"""
        pass


# deprecated import, so deprecated implementations get the Legacy class instead
LoginHandler = LegacyLoginHandler
