"""Base Tornado handlers for the Jupyter server."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import functools
import inspect
import ipaddress
import json
import mimetypes
import os
import re
import types
import warnings
from collections.abc import Awaitable, Coroutine, Sequence
from http.client import responses
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

import prometheus_client
from jinja2 import TemplateNotFound
from jupyter_core.paths import is_hidden
from tornado import web
from tornado.log import app_log
from traitlets.config import Application

import jupyter_server
from jupyter_server import CallContext
from jupyter_server._sysinfo import get_sys_info
from jupyter_server._tz import utcnow
from jupyter_server.auth.decorator import allow_unauthenticated, authorized
from jupyter_server.auth.identity import User
from jupyter_server.i18n import combine_translations
from jupyter_server.services.security import csp_report_uri
from jupyter_server.utils import (
    ensure_async,
    filefind,
    url_escape,
    url_is_absolute,
    url_path_join,
    urldecode_unix_socket_path,
)

if TYPE_CHECKING:
    from logging import Logger

    from jupyter_client.kernelspec import KernelSpecManager
    from jupyter_events import EventLogger
    from jupyter_server_terminals.terminalmanager import TerminalManager
    from tornado.concurrent import Future

    from jupyter_server.auth.authorizer import Authorizer
    from jupyter_server.auth.identity import IdentityProvider
    from jupyter_server.serverapp import ServerApp
    from jupyter_server.services.config.manager import ConfigManager
    from jupyter_server.services.contents.manager import ContentsManager
    from jupyter_server.services.kernels.kernelmanager import AsyncMappingKernelManager
    from jupyter_server.services.sessions.sessionmanager import SessionManager

# -----------------------------------------------------------------------------
# Top-level handlers
# -----------------------------------------------------------------------------

_sys_info_cache = None


def json_sys_info():
    """Get sys info as json."""
    pass


def log() -> Logger:
    """Get the application log."""
    pass


class AuthenticatedHandler(web.RequestHandler):
    """A RequestHandler with an authenticated user."""

    @property
    def base_url(self) -> str:
        pass

    @property
    def content_security_policy(self) -> str:
        """The default Content-Security-Policy header

        Can be overridden by defining Content-Security-Policy in settings['headers']
        """
        pass

    def set_default_headers(self) -> None:
        """Set the default headers."""
        pass

    @property
    def cookie_name(self) -> str:
        pass

    def force_clear_cookie(self, name: str, path: str = "/", domain: str | None = None) -> None:
        """Force a cookie clear."""
        pass

    def clear_login_cookie(self) -> None:
        """Clear a login cookie."""
        pass

    def get_current_user(self) -> str:
        """Get the current user."""
        pass

    def skip_check_origin(self) -> bool:
        """Ask my login_handler if I should skip the origin_check

        For example: in the default LoginHandler, if a request is token-authenticated,
        origin checking should be skipped.
        """
        pass

    @property
    def token_authenticated(self) -> bool:
        """Have I been authenticated with a token?"""
        pass

    @property
    def logged_in(self) -> bool:
        """Is a user currently logged in?"""
        pass

    @property
    def login_handler(self) -> Any:
        """Return the login handler for this application, if any."""
        pass

    @property
    def token(self) -> str | None:
        """Return the login token for this application, if any."""
        pass

    @property
    def login_available(self) -> bool:
        """May a user proceed to log in?

        This returns True if login capability is available, irrespective of
        whether the user is already logged in or not.

        """
        pass

    @property
    def authorizer(self) -> Authorizer:
        pass

    @property
    def identity_provider(self) -> IdentityProvider:
        pass


class JupyterHandler(AuthenticatedHandler):
    """Jupyter-specific extensions to authenticated handling

    Mostly property shortcuts to Jupyter-specific settings.
    """

    @property
    def config(self) -> dict[str, Any] | None:
        pass

    @property
    def log(self) -> Logger:
        """use the Jupyter log by default, falling back on tornado's logger"""
        return log()

    @property
    def jinja_template_vars(self) -> dict[str, Any]:
        """User-supplied values to supply to jinja templates."""
        pass

    @property
    def serverapp(self) -> ServerApp | None:
        pass

    # ---------------------------------------------------------------
    # URLs
    # ---------------------------------------------------------------

    @property
    def version_hash(self) -> str:
        """The version hash to use for cache hints for static files"""
        pass

    @property
    def mathjax_url(self) -> str:
        pass

    @property
    def mathjax_config(self) -> str:
        pass

    @property
    def default_url(self) -> str:
        pass

    @property
    def ws_url(self) -> str:
        pass

    @property
    def contents_js_source(self) -> str:
        pass

    # ---------------------------------------------------------------
    # Manager objects
    # ---------------------------------------------------------------

    @property
    def kernel_manager(self) -> AsyncMappingKernelManager:
        pass

    @property
    def contents_manager(self) -> ContentsManager:
        pass

    @property
    def session_manager(self) -> SessionManager:
        pass

    @property
    def terminal_manager(self) -> TerminalManager:
        pass

    @property
    def kernel_spec_manager(self) -> KernelSpecManager:
        pass

    @property
    def config_manager(self) -> ConfigManager:
        pass

    @property
    def event_logger(self) -> EventLogger:
        pass

    # ---------------------------------------------------------------
    # CORS
    # ---------------------------------------------------------------

    @property
    def allow_origin(self) -> str:
        """Normal Access-Control-Allow-Origin"""
        pass

    @property
    def allow_origin_pat(self) -> str | None:
        """Regular expression version of allow_origin"""
        pass

    @property
    def allow_credentials(self) -> bool:
        """Whether to set Access-Control-Allow-Credentials"""
        pass

    def set_default_headers(self) -> None:
        """Add CORS headers, if defined"""
        pass

    def set_cors_headers(self) -> None:
        """Add CORS headers, if defined

        Now that current_user is async (jupyter-server 2.0),
        must be called at the end of prepare(), instead of in set_default_headers.
        """
        pass

    def set_attachment_header(self, filename: str) -> None:
        """Set Content-Disposition: attachment header

        As a method to ensure handling of filename encoding
        """
        pass

    def get_origin(self) -> str | None:
        # Handle WebSocket Origin naming convention differences
        # The difference between version 8 and 13 is that in 8 the
        # client sends a "Sec-Websocket-Origin" header and in 13 it's
        # simply "Origin".
        pass

    # origin_to_satisfy_tornado is present because tornado requires
    # check_origin to take an origin argument, but we don't use it
    def check_origin(self, origin_to_satisfy_tornado: str = "") -> bool:
        """Check Origin for cross-site API requests, including websockets

        Copied from WebSocket with changes:

        - allow unspecified host/origin (e.g. scripts)
        - allow token-authenticated requests
        """
        pass

    def check_referer(self) -> bool:
        """Check Referer for cross-site requests.
        Disables requests to certain endpoints with
        external or missing Referer.
        If set, allow_origin settings are applied to the Referer
        to whitelist specific cross-origin sites.
        Used on GET for api endpoints and /files/
        to block cross-site inclusion (XSSI).
        """
        pass

    def check_xsrf_cookie(self) -> None:
        """Bypass xsrf cookie checks when token-authenticated"""
        pass

    def check_host(self) -> bool:
        """Check the host header if remote access disallowed.

        Returns True if the request should continue, False otherwise.
        """
        pass

    async def prepare(self, *, _redirect_to_login=True) -> Awaitable[None] | None:  # type:ignore[override]
        """Prepare a response."""
        pass

    # ---------------------------------------------------------------
    # template rendering
    # ---------------------------------------------------------------

    def get_template(self, name):
        """Return the jinja template object for a given name"""
        pass

    def render_template(self, name, **ns):
        """Render a template by name."""
        pass

    @property
    def template_namespace(self) -> dict[str, Any]:
        pass

    def get_json_body(self) -> dict[str, Any] | None:
        """Return the body of the request as JSON data."""
        pass

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        """render custom error pages"""
        pass


class APIHandler(JupyterHandler):
    """Base class for API handlers"""

    async def prepare(self) -> None:  # type:ignore[override]
        """Prepare an API response."""
        pass

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        """APIHandler errors are JSON, not human pages"""
        pass

    def get_login_url(self) -> str:
        """Get the login url."""
        pass

    @property
    def content_security_policy(self) -> str:
        pass

    # set _track_activity = False on API handlers that shouldn't track activity
    _track_activity = True

    def update_api_activity(self) -> None:
        """Update last_activity of API requests"""
        pass

    def finish(self, *args: Any, **kwargs: Any) -> Future[Any]:
        """Finish an API response."""
        pass

    @allow_unauthenticated
    def options(self, *args: Any, **kwargs: Any) -> None:
        """Get the options."""
        pass


class Template404(JupyterHandler):
    """Render our 404 template"""

    async def prepare(self) -> None:  # type:ignore[override]
        """Prepare a 404 response."""
        pass


class AuthenticatedFileHandler(JupyterHandler, web.StaticFileHandler):
    """static files should only be accessible when logged in"""

    auth_resource = "contents"

    @property
    def content_security_policy(self) -> str:
        # In case we're serving HTML/SVG, confine any Javascript to a unique
        # origin so it can't interact with the Jupyter server.
        pass

    @web.authenticated
    @authorized
    def head(self, path: str) -> Awaitable[None]:  # type:ignore[override]
        """Get the head response for a path."""
        pass

    @web.authenticated
    @authorized
    def get(  # type:ignore[override]
        self, path: str, **kwargs: Any
    ) -> Awaitable[None]:
        """Get a file by path."""
        pass

    def get_content_type(self) -> str:
        """Get the content type."""
        pass

    def set_headers(self) -> None:
        """Set the headers."""
        pass

    def compute_etag(self) -> str | None:
        """Compute the etag."""
        pass

    def validate_absolute_path(self, root: str, absolute_path: str) -> str:
        """Validate and return the absolute path.

        Requires tornado 3.1

        Adding to tornado's own handling, forbids the serving of hidden files.
        """
        pass


def json_errors(method: Any) -> Any:  # pragma: no cover
    """Decorate methods with this to return GitHub style JSON errors.

    This should be used on any JSON API on any handler method that can raise HTTPErrors.

    This will grab the latest HTTPError exception using sys.exc_info
    and then:

    1. Set the HTTP status code based on the HTTPError
    2. Create and return a JSON body with a message field describing
       the error in a human readable form.
    """
    pass


# -----------------------------------------------------------------------------
# File handler
# -----------------------------------------------------------------------------

# to minimize subclass changes:
HTTPError = web.HTTPError


class FileFindHandler(JupyterHandler, web.StaticFileHandler):
    """subclass of StaticFileHandler for serving files from a search path

    The setting "static_immutable_cache" can be set up to serve some static
    file as immutable (e.g. file name containing a hash). The setting is a
    list of base URL, every static file URL starting with one of those will
    be immutable.
    """

    # cache search results, don't search for files more than once
    _static_paths: dict[str, str] = {}
    root: tuple[str]  # type:ignore[assignment]

    def set_headers(self) -> None:
        """Set the headers."""
        pass

    def initialize(
        self,
        path: str | list[str],
        default_filename: str | None = None,
        no_cache_paths: list[str] | None = None,
    ) -> None:
        """Initialize the file find handler."""
        pass

    def compute_etag(self) -> str | None:
        """Compute the etag."""
        pass

    # access is allowed as this class is used to serve static assets on login page
    # TODO: create an allow-list of files used on login page and remove this decorator
    @allow_unauthenticated
    def get(self, path: str, include_body: bool = True) -> Coroutine[Any, Any, None]:
        pass

    # access is allowed as this class is used to serve static assets on login page
    # TODO: create an allow-list of files used on login page and remove this decorator
    @allow_unauthenticated
    def head(self, path: str) -> Awaitable[None]:
        pass

    @classmethod
    def get_absolute_path(cls, roots: Sequence[str], path: str) -> str:
        """locate a file to serve on our static file search path"""
        pass

    def validate_absolute_path(self, root: str, absolute_path: str) -> str | None:
        """check if the file should be served (raises 404, 403, etc.)"""
        pass


class APIVersionHandler(APIHandler):
    """An API handler for the server version."""

    _track_activity = False

    @allow_unauthenticated
    def get(self) -> None:
        """Get the server version info."""
        pass


class TrailingSlashHandler(web.RequestHandler):
    """Simple redirect handler that strips trailing slashes

    This should be the first, highest priority handler.
    """

    @allow_unauthenticated
    def get(self) -> None:
        """Handle trailing slashes in a get."""
        pass

    post = put = get


class MainHandler(JupyterHandler):
    """Simple handler for base_url."""

    @allow_unauthenticated
    def get(self) -> None:
        """Get the main template."""
        pass

    post = put = get


class FilesRedirectHandler(JupyterHandler):
    """Handler for redirecting relative URLs to the /files/ handler"""

    @staticmethod
    async def redirect_to_files(self: Any, path: str) -> None:  # noqa: PLW0211
        """make redirect logic a reusable static method

        so it can be called from other handlers.
        """
        pass

    @allow_unauthenticated
    async def get(self, path: str = "") -> None:
        pass


class RedirectWithParams(web.RequestHandler):
    """Same as web.RedirectHandler, but preserves URL parameters"""

    def initialize(self, url: str, permanent: bool = True) -> None:
        """Initialize a redirect handler."""
        pass

    @allow_unauthenticated
    def get(self) -> None:
        """Get a redirect."""
        pass


class PrometheusMetricsHandler(JupyterHandler):
    """
    Return prometheus metrics for this server
    """

    @allow_unauthenticated
    def get(self) -> None:
        """Get prometheus metrics."""
        pass


class PublicStaticFileHandler(web.StaticFileHandler):
    """Same as web.StaticFileHandler, but decorated to acknowledge that auth is not required."""

    @allow_unauthenticated
    def head(self, path: str) -> Awaitable[None]:
        pass

    @allow_unauthenticated
    def get(self, path: str, include_body: bool = True) -> Coroutine[Any, Any, None]:
        pass


# -----------------------------------------------------------------------------
# URL pattern fragments for reuse
# -----------------------------------------------------------------------------

# path matches any number of `/foo[/bar...]` or just `/` or ''
path_regex = r"(?P<path>(?:(?:/[^/]+)+|/?))"

# -----------------------------------------------------------------------------
# URL to handler mappings
# -----------------------------------------------------------------------------


default_handlers = [
    (r".*/", TrailingSlashHandler),
    (r"api", APIVersionHandler),
    (r"/(robots\.txt|favicon\.ico)", PublicStaticFileHandler),
    (r"/metrics", PrometheusMetricsHandler),
]
