"""Identity Provider interface

This defines the _authentication_ layer of Jupyter Server,
to be used in combination with Authorizer for _authorization_.

.. versionadded:: 2.0
"""

from __future__ import annotations

import binascii
import datetime
import hmac
import json
import os
import re
import sys
import typing as t
import uuid
from dataclasses import asdict, dataclass
from http.cookies import Morsel

from tornado import escape, httputil, web
from traitlets import Bool, Dict, Enum, List, TraitError, Type, Unicode, default, validate
from traitlets.config import LoggingConfigurable

from jupyter_server.transutils import _i18n

from .security import passwd_check, set_password
from .utils import get_anonymous_username

if t.TYPE_CHECKING:
    import hmac

_non_alphanum = re.compile(r"[^A-Za-z0-9]")


# Define the User properties that can be updated
UpdatableField = t.Literal["name", "display_name", "initials", "avatar_url", "color"]


@dataclass
class User:
    """Object representing a User

    This or a subclass should be returned from IdentityProvider.get_user
    """

    username: str  # the only truly required field

    # these fields are filled from username if not specified
    # name is the 'real' name of the user
    name: str = ""
    # display_name is a shorter name for us in UI,
    # if different from name. e.g. a nickname
    display_name: str = ""

    # these fields are left as None if undefined
    initials: str | None = None
    avatar_url: str | None = None
    color: str | None = None

    # TODO: extension fields?
    # ext: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        self.fill_defaults()

    def fill_defaults(self):
        """Fill out default fields in the identity model

        - Ensures all values are defined
        - Fills out derivative values for name fields fields
        - Fills out null values for optional fields
        """
        pass


def _backward_compat_user(got_user: t.Any) -> User:
    """Backward-compatibility for LoginHandler.get_user

    Prior to 2.0, LoginHandler.get_user could return anything truthy.

    Typically, this was either a simple string username,
    or a simple dict.

    Make some effort to allow common patterns to keep working.
    """
    pass


class IdentityProvider(LoggingConfigurable):
    """
    Interface for providing identity management and authentication.

    Two principle methods:

    - :meth:`~jupyter_server.auth.IdentityProvider.get_user` returns a :class:`~.User` object
      for successful authentication, or None for no-identity-found.
    - :meth:`~jupyter_server.auth.IdentityProvider.identity_model` turns a :class:`~jupyter_server.auth.User` into a JSONable dict.
      The default is to use :py:meth:`dataclasses.asdict`,
      and usually shouldn't need override.

    Additional methods can customize authentication.

    .. versionadded:: 2.0
    """

    cookie_name: str | Unicode[str, str | bytes] = Unicode(
        "",
        config=True,
        help=_i18n("Name of the cookie to set for persisting login. Default: username-${Host}."),
    )

    cookie_options = Dict(
        config=True,
        help=_i18n(
            "Extra keyword arguments to pass to `set_secure_cookie`."
            " See tornado's set_secure_cookie docs for details."
        ),
    )

    secure_cookie: bool | Bool[bool | None, bool | int | None] = Bool(
        None,
        allow_none=True,
        config=True,
        help=_i18n(
            "Specify whether login cookie should have the `secure` property (HTTPS-only)."
            "Only needed when protocol-detection gives the wrong answer due to proxies."
        ),
    )

    get_secure_cookie_kwargs = Dict(
        config=True,
        help=_i18n(
            "Extra keyword arguments to pass to `get_secure_cookie`."
            " See tornado's get_secure_cookie docs for details."
        ),
    )

    token: str | Unicode[str, str | bytes] = Unicode(
        "<generated>",
        help=_i18n(
            """Token used for authenticating first-time connections to the server.

        The token can be read from the file referenced by JUPYTER_TOKEN_FILE or set directly
        with the JUPYTER_TOKEN environment variable.

        When no password is enabled,
        the default is to generate a new, random token.

        Setting to an empty string disables authentication altogether, which is NOT RECOMMENDED.

        Prior to 2.0: configured as ServerApp.token
        """
        ),
    ).tag(config=True)

    login_handler_class = Type(
        default_value="jupyter_server.auth.login.LoginFormHandler",
        klass=web.RequestHandler,
        config=True,
        help=_i18n("The login handler class to use, if any."),
    )

    logout_handler_class = Type(
        default_value="jupyter_server.auth.logout.LogoutHandler",
        klass=web.RequestHandler,
        config=True,
        help=_i18n("The logout handler class to use."),
    )

    # Define the fields that can be updated
    updatable_fields = List(
        trait=Enum(list(t.get_args(UpdatableField))),
        default_value=["color"],  # Default updatable field
        config=True,
        help=_i18n("List of fields in the User model that can be updated."),
    )

    token_generated = False

    @default("token")
    def _token_default(self):
        pass

    @validate("updatable_fields")
    def _validate_updatable_fields(self, proposal):
        """Validate that all fields in updatable_fields are valid."""
        pass

    need_token: bool | Bool[bool, t.Union[bool, int]] = Bool(True)

    def get_user(self, handler: web.RequestHandler) -> User | None | t.Awaitable[User | None]:
        """Get the authenticated user for a request

        Must return a :class:`jupyter_server.auth.User`,
        though it may be a subclass.

        Return None if the request is not authenticated.

        _may_ be a coroutine
        """
        pass

    # not sure how to have optional-async type signature
    # on base class with `async def` without splitting it into two methods

    async def _get_user(self, handler: web.RequestHandler) -> User | None:
        """Get the user."""
        pass

    def update_user(
        self, handler: web.RequestHandler, user_data: dict[UpdatableField, str]
    ) -> User:
        """Update user information and persist the user model."""
        pass

    def check_update(self, user_data: dict[UpdatableField, str]) -> None:
        """Raises if some fields to update are not updatable."""
        pass

    def update_user_model(self, current_user: User, user_data: dict[UpdatableField, str]) -> User:
        """Update user information."""
        pass

    def persist_user_model(self, handler: web.RequestHandler) -> None:
        """Persist the user model (i.e. a cookie)."""
        pass

    def identity_model(self, user: User) -> dict[str, t.Any]:
        """Return a User as an Identity model"""
        pass

    def get_handlers(self) -> list[tuple[str, object]]:
        """Return list of additional handlers for this identity provider

        For example, an OAuth callback handler.
        """
        pass

    def user_to_cookie(self, user: User) -> str:
        """Serialize a user to a string for storage in a cookie

        If overriding in a subclass, make sure to define user_from_cookie as well.

        Default is just the user's username.
        """
        pass

    def user_from_cookie(self, cookie_value: str) -> User | None:
        """Inverse of user_to_cookie"""
        pass

    def get_cookie_name(self, handler: web.RequestHandler) -> str:
        """Return the login cookie name

        Uses IdentityProvider.cookie_name, if defined.
        Default is to generate a string taking host into account to avoid
        collisions for multiple servers on one hostname with different ports.
        """
        pass

    def set_login_cookie(self, handler: web.RequestHandler, user: User) -> None:
        """Call this on handlers to set the login cookie for success"""
        pass

    def _force_clear_cookie(
        self, handler: web.RequestHandler, name: str, path: str = "/", domain: str | None = None
    ) -> None:
        """Deletes the cookie with the given name.

        Tornado's cookie handling currently (Jan 2018) stores cookies in a dict
        keyed by name, so it can only modify one cookie with a given name per
        response. The browser can store multiple cookies with the same name
        but different domains and/or paths. This method lets us clear multiple
        cookies with the same name.

        Due to limitations of the cookie protocol, you must pass the same
        path and domain to clear a cookie as were used when that cookie
        was set (but there is no way to find out on the server side
        which values were used for a given cookie).
        """
        pass

    def clear_login_cookie(self, handler: web.RequestHandler) -> None:
        """Clear the login cookie, effectively logging out the session."""
        pass

    def get_user_cookie(
        self, handler: web.RequestHandler
    ) -> User | None | t.Awaitable[User | None]:
        """Get user from a cookie

        Calls user_from_cookie to deserialize cookie value
        """
        pass

    auth_header_pat = re.compile(r"(token|bearer)\s+(.+)", re.IGNORECASE)

    def get_token(self, handler: web.RequestHandler) -> str | None:
        """Get the user token from a request

        Default:

        - in URL parameters: ?token=<token>
        - in header: Authorization: token <token>
        """
        pass

    async def get_user_token(self, handler: web.RequestHandler) -> User | None:
        """Identify the user based on a token in the URL or Authorization header

        Returns:
        - uuid if authenticated
        - None if not
        """
        pass

    def generate_anonymous_user(self, handler: web.RequestHandler) -> User:
        """Generate a random anonymous user.

        For use when a single shared token is used,
        but does not identify a user.
        """
        pass

    def should_check_origin(self, handler: web.RequestHandler) -> bool:
        """Should the Handler check for CORS origin validation?

        Origin check should be skipped for token-authenticated requests.

        Returns:
        - True, if Handler must check for valid CORS origin.
        - False, if Handler should skip origin check since requests are token-authenticated.
        """
        pass

    def is_token_authenticated(self, handler: web.RequestHandler) -> bool:
        """Returns True if handler has been token authenticated. Otherwise, False.

        Login with a token is used to signal certain things, such as:

        - permit access to REST API
        - xsrf protection
        - skip origin-checks for scripts
        """
        pass

    def validate_security(
        self,
        app: t.Any,
        ssl_options: dict[str, t.Any] | None = None,
    ) -> None:
        """Check the application's security.

        Show messages, or abort if necessary, based on the security configuration.
        """
        pass

    def process_login_form(self, handler: web.RequestHandler) -> User | None:
        """Process login form data

        Return authenticated User if successful, None if not.
        """
        pass

    @property
    def auth_enabled(self):
        """Is authentication enabled?

        Should always be True, but may be False in rare, insecure cases
        where requests with no auth are allowed.

        Previously: LoginHandler.get_login_available
        """
        pass

    @property
    def login_available(self):
        """Whether a LoginHandler is needed - and therefore whether the login page should be displayed."""
        pass

    @property
    def logout_available(self):
        """Whether a LogoutHandler is needed."""
        pass

    def cookie_secret_hook(self, h: hmac.HMAC) -> hmac.HMAC:
        """Update cookie secret input

        Subclasses may call `h.update()` with any credentials that,
        when changed, should invalidate existing cookies, such as a
        password.

        The updated hashlib object should be returned.

        """
        pass


class PasswordIdentityProvider(IdentityProvider):
    """A password identity provider."""

    hashed_password = Unicode(
        "",
        config=True,
        help=_i18n(
            """
            Hashed password to use for web authentication.

            To generate, type in a python/IPython shell:

                from jupyter_server.auth import passwd; passwd()

            The string should be of the form type:salt:hashed-password.
            """
        ),
    )

    password_required = Bool(
        False,
        config=True,
        help=_i18n(
            """
            Forces users to use a password for the Jupyter server.
            This is useful in a multi user environment, for instance when
            everybody in the LAN can access each other's machine through ssh.

            In such a case, serving on localhost is not secure since
            any user can connect to the Jupyter server via ssh.

            """
        ),
    )

    allow_password_change = Bool(
        True,
        config=True,
        help=_i18n(
            """
            Allow password to be changed at login for the Jupyter server.

            While logging in with a token, the Jupyter server UI will give the opportunity to
            the user to enter a new password at the same time that will replace
            the token login mechanism.

            This can be set to False to prevent changing password from the UI/API.
            """
        ),
    )

    @default("need_token")
    def _need_token_default(self):
        pass

    @default("updatable_fields")
    def _default_updatable_fields(self):
        pass

    @property
    def login_available(self) -> bool:
        """Whether a LoginHandler is needed - and therefore whether the login page should be displayed."""
        pass

    @property
    def auth_enabled(self) -> bool:
        """Return whether any auth is enabled"""
        pass

    def update_user_model(self, current_user: User, user_data: dict[UpdatableField, str]) -> User:
        """Update user information."""
        pass

    def persist_user_model(self, handler: web.RequestHandler) -> None:
        """Persist the user model to a cookie."""
        pass

    def passwd_check(self, password):
        """Check password against our stored hashed password"""
        pass

    def process_login_form(self, handler: web.RequestHandler) -> User | None:
        """Process login form data

        Return authenticated User if successful, None if not.
        """
        pass

    def validate_security(
        self,
        app: t.Any,
        ssl_options: dict[str, t.Any] | None = None,
    ) -> None:
        """Handle security validation."""
        pass

    def cookie_secret_hook(self, h: hmac.HMAC) -> hmac.HMAC:
        """Include password in cookie secret.

        This makes it so changing the password invalidates cookies.
        """
        pass


class LegacyIdentityProvider(PasswordIdentityProvider):
    """Legacy IdentityProvider for use with custom LoginHandlers

    Login configuration has moved from LoginHandler to IdentityProvider
    in Jupyter Server 2.0.
    """

    # settings must be passed for
    settings = Dict()

    @default("settings")
    def _default_settings(self):
        pass

    @default("login_handler_class")
    def _default_login_handler_class(self):
        pass

    @property
    def auth_enabled(self):
        pass

    def get_user(self, handler: web.RequestHandler) -> User | None:
        """Get the user."""
        pass

    @property
    def login_available(self) -> bool:
        pass

    def should_check_origin(self, handler: web.RequestHandler) -> bool:
        """Whether we should check origin."""
        pass

    def is_token_authenticated(self, handler: web.RequestHandler) -> bool:
        """Whether we are token authenticated."""
        pass

    def validate_security(
        self,
        app: t.Any,
        ssl_options: dict[str, t.Any] | None = None,
    ) -> None:
        """Validate security."""
        pass
