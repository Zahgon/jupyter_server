"""A tornado based Jupyter server."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import datetime
import errno
import gettext
import hashlib
import hmac
import ipaddress
import json
import logging
import mimetypes
import os
import pathlib
import random
import re
import select
import signal
import socket
import stat
import sys
import threading
import time
import typing as t
import urllib
import warnings
from base64 import encodebytes
from functools import partial
from pathlib import Path

import jupyter_client
from jupyter_client.kernelspec import KernelSpecManager
from jupyter_client.manager import KernelManager
from jupyter_client.session import Session
from jupyter_core.application import JupyterApp, base_aliases, base_flags
from jupyter_core.paths import jupyter_runtime_dir
from jupyter_events.logger import EventLogger
from nbformat.sign import NotebookNotary
from tornado import httpserver, ioloop, web
from tornado.httputil import url_concat
from tornado.log import LogFormatter, access_log, app_log, gen_log
from tornado.netutil import bind_sockets
from tornado.routing import Matcher, Rule

if not sys.platform.startswith("win"):
    from tornado.netutil import bind_unix_socket

if sys.platform.startswith("win"):
    try:
        import colorama

        colorama.init()
    except ImportError:
        pass

from traitlets import (
    Any,
    Bool,
    Bytes,
    Dict,
    Float,
    Instance,
    Integer,
    List,
    TraitError,
    Type,
    Unicode,
    Union,
    default,
    observe,
    validate,
)
from traitlets.config import Config
from traitlets.config.application import boolean_flag, catch_config_error

from jupyter_server import (
    DEFAULT_EVENTS_SCHEMA_PATH,
    DEFAULT_JUPYTER_SERVER_PORT,
    DEFAULT_STATIC_FILES_PATH,
    DEFAULT_TEMPLATE_PATH_LIST,
    JUPYTER_SERVER_EVENTS_URI,
    __version__,
)
from jupyter_server._sysinfo import get_sys_info
from jupyter_server._tz import utcnow
from jupyter_server.auth.authorizer import AllowAllAuthorizer, Authorizer
from jupyter_server.auth.identity import (
    IdentityProvider,
    LegacyIdentityProvider,
    PasswordIdentityProvider,
)
from jupyter_server.auth.login import LoginHandler
from jupyter_server.auth.logout import LogoutHandler
from jupyter_server.base.handlers import (
    FileFindHandler,
    MainHandler,
    RedirectWithParams,
    Template404,
)
from jupyter_server.extension.config import ExtensionConfigManager
from jupyter_server.extension.manager import ExtensionManager
from jupyter_server.extension.serverextension import ServerExtensionApp
from jupyter_server.gateway.connections import GatewayWebSocketConnection
from jupyter_server.gateway.gateway_client import GatewayClient
from jupyter_server.gateway.managers import (
    GatewayKernelSpecManager,
    GatewayMappingKernelManager,
    GatewaySessionManager,
)
from jupyter_server.log import log_request
from jupyter_server.prometheus.metrics import (
    ACTIVE_DURATION,
    LAST_ACTIVITY,
    SERVER_EXTENSION_INFO,
    SERVER_INFO,
    SERVER_STARTED,
)
from jupyter_server.services.config import ConfigManager
from jupyter_server.services.contents.filemanager import (
    AsyncFileContentsManager,
    FileContentsManager,
)
from jupyter_server.services.contents.largefilemanager import AsyncLargeFileManager
from jupyter_server.services.contents.manager import AsyncContentsManager, ContentsManager
from jupyter_server.services.kernels.connection.base import BaseKernelWebsocketConnection
from jupyter_server.services.kernels.connection.channels import ZMQChannelsWebsocketConnection
from jupyter_server.services.kernels.kernelmanager import (
    AsyncMappingKernelManager,
    MappingKernelManager,
)
from jupyter_server.services.sessions.sessionmanager import SessionManager
from jupyter_server.utils import (
    JupyterServerAuthWarning,
    check_pid,
    fetch,
    unix_socket_in_use,
    url_escape,
    url_path_join,
    urlencode_unix_socket_path,
)

try:
    import resource
except ImportError:
    # Windows
    resource = None  # type:ignore[assignment]

from jinja2 import Environment, FileSystemLoader
from jupyter_core.paths import secure_write
from jupyter_core.utils import ensure_async

from jupyter_server.transutils import _i18n, trans
from jupyter_server.utils import pathname2url, urljoin

# the minimum viable tornado version: needs to be kept in sync with setup.py
MIN_TORNADO = (6, 1, 0)

try:
    import tornado

    assert tornado.version_info >= MIN_TORNADO
except (ImportError, AttributeError, AssertionError) as e:  # pragma: no cover
    raise ImportError(_i18n("The Jupyter Server requires tornado >=%s.%s.%s") % MIN_TORNADO) from e

try:
    import resource
except ImportError:
    # Windows
    resource = None  # type:ignore[assignment]

# -----------------------------------------------------------------------------
# Module globals
# -----------------------------------------------------------------------------

_examples = """
jupyter server                       # start the server
jupyter server  --certfile=mycert.pem # use SSL/TLS certificate
jupyter server password              # enter a password to protect the server
"""

JUPYTER_SERVICE_HANDLERS = {
    "auth": None,
    "api": ["jupyter_server.services.api.handlers"],
    "config": ["jupyter_server.services.config.handlers"],
    "contents": ["jupyter_server.services.contents.handlers"],
    "files": ["jupyter_server.files.handlers"],
    "kernels": [
        "jupyter_server.services.kernels.handlers",
    ],
    "kernelspecs": [
        "jupyter_server.kernelspecs.handlers",
        "jupyter_server.services.kernelspecs.handlers",
    ],
    "nbconvert": [
        "jupyter_server.nbconvert.handlers",
        "jupyter_server.services.nbconvert.handlers",
    ],
    "security": ["jupyter_server.services.security.handlers"],
    "sessions": ["jupyter_server.services.sessions.handlers"],
    "shutdown": ["jupyter_server.services.shutdown"],
    "view": ["jupyter_server.view.handlers"],
    "events": ["jupyter_server.services.events.handlers"],
}

# Added for backwards compatibility from classic notebook server.
DEFAULT_SERVER_PORT = DEFAULT_JUPYTER_SERVER_PORT

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def random_ports(port: int, n: int) -> t.Generator[int, None, None]:
    """Generate a list of n random ports near the given port.

    The first 5 ports will be sequential, and the remaining n-5 will be
    randomly selected in the range [port-2*n, port+2*n].
    """
    pass


def load_handlers(name: str) -> t.Any:
    """Load the (URL pattern, handler) tuples for each component."""
    pass


# -----------------------------------------------------------------------------
# The Tornado web application
# -----------------------------------------------------------------------------


class ServerWebApplication(web.Application):
    """A server web application."""

    def __init__(
        self,
        jupyter_app,
        default_services,
        kernel_manager,
        contents_manager,
        session_manager,
        kernel_spec_manager,
        config_manager,
        event_logger,
        extra_services,
        log,
        base_url,
        default_url,
        settings_overrides,
        jinja_env_options,
        *,
        authorizer=None,
        identity_provider=None,
        kernel_websocket_connection_class=None,
        websocket_ping_interval=None,
        websocket_ping_timeout=None,
    ):
        """Initialize a server web application."""
        if identity_provider is None:
            warnings.warn(
                "identity_provider unspecified. Using default IdentityProvider."
                " Specify an identity_provider to avoid this message.",
                RuntimeWarning,
                stacklevel=2,
            )
            identity_provider = IdentityProvider(parent=jupyter_app)

        if authorizer is None:
            warnings.warn(
                "authorizer unspecified. Using permissive AllowAllAuthorizer."
                " Specify an authorizer to avoid this message.",
                JupyterServerAuthWarning,
                stacklevel=2,
            )
            authorizer = AllowAllAuthorizer(parent=jupyter_app, identity_provider=identity_provider)

        settings = self.init_settings(
            jupyter_app,
            kernel_manager,
            contents_manager,
            session_manager,
            kernel_spec_manager,
            config_manager,
            event_logger,
            extra_services,
            log,
            base_url,
            default_url,
            settings_overrides,
            jinja_env_options,
            authorizer=authorizer,
            identity_provider=identity_provider,
            kernel_websocket_connection_class=kernel_websocket_connection_class,
            websocket_ping_interval=websocket_ping_interval,
            websocket_ping_timeout=websocket_ping_timeout,
        )
        handlers = self.init_handlers(default_services, settings)

        undecorated_methods = []
        for matcher, handler, *_ in handlers:
            undecorated_methods.extend(self._check_handler_auth(matcher, handler))

        if undecorated_methods:
            message = (
                "Core endpoints without @allow_unauthenticated, @ws_authenticated, nor @web.authenticated:\n"
                + "\n".join(undecorated_methods)
            )
            if jupyter_app.allow_unauthenticated_access:
                warnings.warn(
                    message,
                    JupyterServerAuthWarning,
                    stacklevel=2,
                )
            else:
                raise Exception(message)

        super().__init__(handlers, **settings)

    def add_handlers(self, host_pattern, host_handlers):
        pass

    def init_settings(
        self,
        jupyter_app,
        kernel_manager,
        contents_manager,
        session_manager,
        kernel_spec_manager,
        config_manager,
        event_logger,
        extra_services,
        log,
        base_url,
        default_url,
        settings_overrides,
        jinja_env_options=None,
        *,
        authorizer=None,
        identity_provider=None,
        kernel_websocket_connection_class=None,
        websocket_ping_interval=None,
        websocket_ping_timeout=None,
    ):
        """Initialize settings for the web application."""
        pass

    def init_handlers(self, default_services, settings):
        """Load the (URL pattern, handler) tuples for each component."""
        pass

    def last_activity(self):
        """Get a UTC timestamp for when the server last did something.

        Includes: API activity, kernel activity, kernel shutdown, and terminal
        activity.
        """
        pass

    def _check_handler_auth(
        self, matcher: t.Union[str, Matcher], handler: type[web.RequestHandler]
    ):
        pass


def _has_tornado_web_authenticated(method: t.Callable[..., t.Any]) -> bool:
    """Check if given method was decorated with @web.authenticated.

    Note: it is ok if we reject on @authorized @web.authenticated
    because the correct order is @web.authenticated @authorized.
    """
    pass


class JupyterPasswordApp(JupyterApp):
    """Set a password for the Jupyter server.

    Setting a password secures the Jupyter server
    and removes the need for token-based authentication.
    """

    description: str = __doc__

    def _config_file_default(self):
        """the default config file."""
        pass

    def start(self):
        """Start the password app."""
        pass


def shutdown_server(server_info, timeout=5, log=None):
    """Shutdown a Jupyter server in a separate process.

    *server_info* should be a dictionary as produced by list_running_servers().

    Will first try to request shutdown using /api/shutdown .
    On Unix, if the server is still running after *timeout* seconds, it will
    send SIGTERM. After another timeout, it escalates to SIGKILL.

    Returns True if the server was stopped by any means, False if stopping it
    failed (on Windows).
    """
    pass


class JupyterServerStopApp(JupyterApp):
    """An application to stop a Jupyter server."""

    version: str = __version__
    description: str = "Stop currently running Jupyter server for a given port"

    port = Integer(
        DEFAULT_JUPYTER_SERVER_PORT,
        config=True,
        help="Port of the server to be killed. Default %s" % DEFAULT_JUPYTER_SERVER_PORT,
    )

    sock = Unicode("", config=True, help="UNIX socket of the server to be killed.")

    def parse_command_line(self, argv=None):
        """Parse command line options."""
        pass

    def shutdown_server(self, server):
        """Shut down a server."""
        pass

    def _shutdown_or_exit(self, target_endpoint, server):
        """Handle a shutdown."""
        pass

    @staticmethod
    def _maybe_remove_unix_socket(socket_path):
        """Try to remove a socket path."""
        pass

    def start(self):
        """Start the server stop app."""
        pass


class JupyterServerListApp(JupyterApp):
    """An application to list running Jupyter servers."""

    version: str = __version__
    description: str = _i18n("List currently running Jupyter servers.")

    flags = {
        "jsonlist": (
            {"JupyterServerListApp": {"jsonlist": True}},
            _i18n("Produce machine-readable JSON list output."),
        ),
        "json": (
            {"JupyterServerListApp": {"json": True}},
            _i18n("Produce machine-readable JSON object on each line of output."),
        ),
    }

    jsonlist = Bool(
        False,
        config=True,
        help=_i18n(
            "If True, the output will be a JSON list of objects, one per "
            "active Jupyer server, each with the details from the "
            "relevant server info file."
        ),
    )
    json = Bool(
        False,
        config=True,
        help=_i18n(
            "If True, each line of output will be a JSON object with the "
            "details from the server info file. For a JSON list output, "
            "see the JupyterServerListApp.jsonlist configuration value"
        ),
    )

    def start(self):
        """Start the server list application."""
        pass


# -----------------------------------------------------------------------------
# Aliases and Flags
# -----------------------------------------------------------------------------

flags = dict(base_flags)

flags["allow-root"] = (
    {"ServerApp": {"allow_root": True}},
    _i18n("Allow the server to be run from root user."),
)
flags["no-browser"] = (
    {"ServerApp": {"open_browser": False}, "ExtensionApp": {"open_browser": False}},
    _i18n("Prevent the opening of the default url in the browser."),
)
flags["debug"] = (
    {"ServerApp": {"log_level": "DEBUG"}, "ExtensionApp": {"log_level": "DEBUG"}},
    _i18n("Set debug level for the extension and underlying server applications."),
)
flags["autoreload"] = (
    {"ServerApp": {"autoreload": True}},
    """Autoreload the webapp
    Enable reloading of the tornado webapp and all imported Python packages
    when any changes are made to any Python src files in server or
    extensions.
    """,
)


# Add notebook manager flags
flags.update(
    boolean_flag(
        "script",
        "FileContentsManager.save_script",
        "DEPRECATED, IGNORED",
        "DEPRECATED, IGNORED",
    )
)

aliases = dict(base_aliases)

aliases.update(
    {
        "ip": "ServerApp.ip",
        "port": "ServerApp.port",
        "port-retries": "ServerApp.port_retries",
        "sock": "ServerApp.sock",
        "sock-mode": "ServerApp.sock_mode",
        "transport": "KernelManager.transport",
        "keyfile": "ServerApp.keyfile",
        "certfile": "ServerApp.certfile",
        "client-ca": "ServerApp.client_ca",
        "notebook-dir": "ServerApp.root_dir",
        "preferred-dir": "ServerApp.preferred_dir",
        "browser": "ServerApp.browser",
        "pylab": "ServerApp.pylab",
        "gateway-url": "GatewayClient.url",
    }
)

# -----------------------------------------------------------------------------
# ServerApp
# -----------------------------------------------------------------------------


class ServerApp(JupyterApp):
    """The Jupyter Server application class."""

    name = "jupyter-server"
    version: str = __version__
    description: str = _i18n(
        """The Jupyter Server.

    This launches a Tornado-based Jupyter Server."""
    )
    examples = _examples

    flags = Dict(flags)
    aliases = Dict(aliases)

    classes = [
        KernelManager,
        Session,
        MappingKernelManager,
        KernelSpecManager,
        AsyncMappingKernelManager,
        ContentsManager,
        FileContentsManager,
        AsyncContentsManager,
        AsyncFileContentsManager,
        NotebookNotary,
        GatewayMappingKernelManager,
        GatewayKernelSpecManager,
        GatewaySessionManager,
        GatewayWebSocketConnection,
        GatewayClient,
        Authorizer,
        EventLogger,
        ZMQChannelsWebsocketConnection,
    ]

    subcommands: dict[str, t.Any] = {
        "list": (
            JupyterServerListApp,
            JupyterServerListApp.description.splitlines()[0],
        ),
        "stop": (
            JupyterServerStopApp,
            JupyterServerStopApp.description.splitlines()[0],
        ),
        "password": (
            JupyterPasswordApp,
            JupyterPasswordApp.description.splitlines()[0],
        ),
        "extension": (
            ServerExtensionApp,
            ServerExtensionApp.description.splitlines()[0],
        ),
    }

    # A list of services whose handlers will be exposed.
    # Subclasses can override this list to
    # expose a subset of these handlers.
    default_services = (
        "api",
        "auth",
        "config",
        "contents",
        "files",
        "kernels",
        "kernelspecs",
        "nbconvert",
        "security",
        "sessions",
        "shutdown",
        "view",
        "events",
    )

    _log_formatter_cls = LogFormatter  # type:ignore[assignment]
    _stopping = Bool(False, help="Signal that we've begun stopping.")

    @default("log_level")
    def _default_log_level(self) -> int:
        pass

    @default("log_format")
    def _default_log_format(self) -> str:
        """override default log format to include date & time"""
        pass

    # file to be opened in the Jupyter server
    file_to_run = Unicode("", help="Open the named file when the application is launched.").tag(
        config=True
    )

    file_url_prefix = Unicode(
        "notebooks", help="The URL prefix where files are opened directly."
    ).tag(config=True)

    # Network related information
    allow_origin = Unicode(
        "",
        config=True,
        help="""Set the Access-Control-Allow-Origin header

        Use '*' to allow any origin to access your server.

        Takes precedence over allow_origin_pat.
        """,
    )

    allow_origin_pat = Unicode(
        "",
        config=True,
        help="""Use a regular expression for the Access-Control-Allow-Origin header

        Requests from an origin matching the expression will get replies with:

            Access-Control-Allow-Origin: origin

        where `origin` is the origin of the request.

        Ignored if allow_origin is set.
        """,
    )

    allow_credentials = Bool(
        False,
        config=True,
        help=_i18n("Set the Access-Control-Allow-Credentials: true header"),
    )

    allow_root = Bool(
        False,
        config=True,
        help=_i18n("Whether to allow the user to run the server as root."),
    )

    autoreload = Bool(
        False,
        config=True,
        help=_i18n("Reload the webapp when changes are made to any Python src files."),
    )

    default_url = Unicode("/", config=True, help=_i18n("The default URL to redirect to from `/`"))

    ip = Unicode(
        "localhost",
        config=True,
        help=_i18n("The IP address the Jupyter server will listen on."),
    )

    @default("ip")
    def _default_ip(self) -> str:
        """Return localhost if available, 127.0.0.1 otherwise.

        On some (horribly broken) systems, localhost cannot be bound.
        """
        pass

    @validate("ip")
    def _validate_ip(self, proposal: t.Any) -> str:
        pass

    custom_display_url = Unicode(
        "",
        config=True,
        help=_i18n(
            """Override URL shown to users.

        Replace actual URL, including protocol, address, port and base URL,
        with the given value when displaying URL to the users. Do not change
        the actual connection URL. If authentication token is enabled, the
        token is added to the custom URL automatically.

        This option is intended to be used when the URL to display to the user
        cannot be determined reliably by the Jupyter server (proxified
        or containerized setups for example)."""
        ),
    )

    port_env = "JUPYTER_PORT"
    port_default_value = DEFAULT_JUPYTER_SERVER_PORT

    port = Integer(
        config=True,
        help=_i18n("The port the server will listen on (env: JUPYTER_PORT)."),
    )

    @default("port")
    def _port_default(self) -> int:
        pass

    port_retries_env = "JUPYTER_PORT_RETRIES"
    port_retries_default_value = 50
    port_retries = Integer(
        port_retries_default_value,
        config=True,
        help=_i18n(
            "The number of additional ports to try if the specified port is not "
            "available (env: JUPYTER_PORT_RETRIES)."
        ),
    )

    @default("port_retries")
    def _port_retries_default(self) -> int:
        pass

    sock = Unicode("", config=True, help="The UNIX socket the Jupyter server will listen on.")

    sock_mode = Unicode(
        "0600",
        config=True,
        help="The permissions mode for UNIX socket creation (default: 0600).",
    )

    @validate("sock_mode")
    def _validate_sock_mode(self, proposal: t.Any) -> t.Any:
        pass

    certfile = Unicode(
        "",
        config=True,
        help=_i18n("""The full path to an SSL/TLS certificate file."""),
    )

    keyfile = Unicode(
        "",
        config=True,
        help=_i18n("""The full path to a private key file for usage with SSL/TLS."""),
    )

    client_ca = Unicode(
        "",
        config=True,
        help=_i18n(
            """The full path to a certificate authority certificate for SSL/TLS client authentication."""
        ),
    )

    cookie_secret_file = Unicode(
        config=True, help=_i18n("""The file where the cookie secret is stored.""")
    )

    @default("cookie_secret_file")
    def _default_cookie_secret_file(self) -> str:
        pass

    cookie_secret = Bytes(
        b"",
        config=True,
        help="""The random bytes used to secure cookies.
        By default this is generated on first start of the server and persisted across server
        sessions by writing the cookie secret into the `cookie_secret_file` file.
        When using an executable config file you can override this to be random at each server restart.

        Note: Cookie secrets should be kept private, do not share config files with
        cookie_secret stored in plaintext (you can read the value from a file).
        """,
    )

    @default("cookie_secret")
    def _default_cookie_secret(self) -> bytes:
        pass

    def _write_cookie_secret_file(self, secret: bytes) -> None:
        """write my secret to my secret_file"""
        pass

    _token_set = False

    token = Unicode("<DEPRECATED>", help=_i18n("""DEPRECATED. Use IdentityProvider.token""")).tag(
        config=True
    )

    @observe("token")
    def _deprecated_token(self, change: t.Any) -> None:
        pass

    @default("token")
    def _deprecated_token_access(self) -> str:
        pass

    min_open_files_limit = Integer(
        config=True,
        help="""
        Gets or sets a lower bound on the open file handles process resource
        limit. This may need to be increased if you run into an
        OSError: [Errno 24] Too many open files.
        This is not applicable when running on Windows.
        """,
        allow_none=True,
    )

    @default("min_open_files_limit")
    def _default_min_open_files_limit(self) -> t.Optional[int]:
        pass

    max_body_size = Integer(
        512 * 1024 * 1024,
        config=True,
        help="""
        Sets the maximum allowed size of the client request body, specified in
        the Content-Length request header field. If the size in a request
        exceeds the configured value, a malformed HTTP message is returned to
        the client.

        Note: max_body_size is applied even in streaming mode.
        """,
    )

    max_buffer_size = Integer(
        512 * 1024 * 1024,
        config=True,
        help="""
        Gets or sets the maximum amount of memory, in bytes, that is allocated
        for use by the buffer manager.
        """,
    )

    password = Unicode(
        "",
        config=True,
        help="""DEPRECATED in 2.0. Use PasswordIdentityProvider.hashed_password""",
    )

    password_required = Bool(
        False,
        config=True,
        help="""DEPRECATED in 2.0. Use PasswordIdentityProvider.password_required""",
    )

    allow_password_change = Bool(
        True,
        config=True,
        help="""DEPRECATED in 2.0. Use PasswordIdentityProvider.allow_password_change""",
    )

    def _warn_deprecated_config(
        self, change: t.Any, clsname: str, new_name: t.Optional[str] = None
    ) -> None:
        """Warn on deprecated config."""
        pass

    @observe("password")
    def _deprecated_password(self, change: t.Any) -> None:
        pass

    @observe("password_required", "allow_password_change")
    def _deprecated_password_config(self, change: t.Any) -> None:
        pass

    disable_check_xsrf = Bool(
        False,
        config=True,
        help="""Disable cross-site-request-forgery protection

        Jupyter server includes protection from cross-site request forgeries,
        requiring API requests to either:

        - originate from pages served by this server (validated with XSRF cookie and token), or
        - authenticate with a token

        Some anonymous compute resources still desire the ability to run code,
        completely without authentication.
        These services can disable all authentication and security checks,
        with the full knowledge of what that implies.
        """,
    )

    _allow_unauthenticated_access_env = "JUPYTER_SERVER_ALLOW_UNAUTHENTICATED_ACCESS"

    allow_unauthenticated_access = Bool(
        True,
        config=True,
        help=f"""Allow unauthenticated access to endpoints without authentication rule.

        When set to `True` (default in jupyter-server 2.0, subject to change
        in the future), any request to an endpoint without an authentication rule
        (either `@tornado.web.authenticated`, or `@allow_unauthenticated`)
        will be permitted, regardless of whether user has logged in or not.

        When set to `False`, logging in will be required for access to each endpoint,
        excluding the endpoints marked with `@allow_unauthenticated` decorator.

        This option can be configured using `{_allow_unauthenticated_access_env}`
        environment variable: any non-empty value other than "true" and "yes" will
        prevent unauthenticated access to endpoints without `@allow_unauthenticated`.
        """,
    )

    @default("allow_unauthenticated_access")
    def _allow_unauthenticated_access_default(self):
        pass

    allow_remote_access = Bool(
        config=True,
        help="""Allow requests where the Host header doesn't point to a local server

       By default, requests get a 403 forbidden response if the 'Host' header
       shows that the browser thinks it's on a non-local domain.
       Setting this option to True disables this check.

       This protects against 'DNS rebinding' attacks, where a remote web server
       serves you a page and then changes its DNS to send later requests to a
       local IP, bypassing same-origin checks.

       Local IP addresses (such as 127.0.0.1 and ::1) are allowed as local,
       along with hostnames configured in local_hostnames.
       """,
    )

    @default("allow_remote_access")
    def _default_allow_remote(self) -> bool:
        """Disallow remote access if we're listening only on loopback addresses"""
        pass

    use_redirect_file = Bool(
        True,
        config=True,
        help="""Disable launching browser by redirect file
     For versions of notebook > 5.7.2, a security feature measure was added that
     prevented the authentication token used to launch the browser from being visible.
     This feature makes it difficult for other users on a multi-user system from
     running code in your Jupyter session as you.
     However, some environments (like Windows Subsystem for Linux (WSL) and Chromebooks),
     launching a browser using a redirect file can lead the browser failing to load.
     This is because of the difference in file structures/paths between the runtime and
     the browser.

     Disabling this setting to False will disable this behavior, allowing the browser
     to launch by using a URL and visible token (as before).
     """,
    )

    local_hostnames = List(
        Unicode(),
        ["localhost"],
        config=True,
        help="""Hostnames to allow as local when allow_remote_access is False.

       Local IP addresses (such as 127.0.0.1 and ::1) are automatically accepted
       as local as well.
       """,
    )

    open_browser = Bool(
        False,
        config=True,
        help="""Whether to open in a browser after starting.
                        The specific browser used is platform dependent and
                        determined by the python standard library `webbrowser`
                        module, unless it is overridden using the --browser
                        (ServerApp.browser) configuration option.
                        """,
    )

    browser = Unicode(
        "",
        config=True,
        help="""Specify what command to use to invoke a web
                      browser when starting the server. If not specified, the
                      default browser will be determined by the `webbrowser`
                      standard library module, which allows setting of the
                      BROWSER environment variable to override it.
                      """,
    )

    webbrowser_open_new = Integer(
        2,
        config=True,
        help=_i18n(
            """Specify where to open the server on startup. This is the
        `new` argument passed to the standard library method `webbrowser.open`.
        The behaviour is not guaranteed, but depends on browser support. Valid
        values are:

         - 2 opens a new tab,
         - 1 opens a new window,
         - 0 opens in an existing window.

        See the `webbrowser.open` documentation for details.
        """
        ),
    )

    tornado_settings = Dict(
        config=True,
        help=_i18n(
            "Supply overrides for the tornado.web.Application that the Jupyter server uses."
        ),
    )

    websocket_compression_options = Any(
        None,
        config=True,
        help=_i18n(
            """
        Set the tornado compression options for websocket connections.

        This value will be returned from :meth:`WebSocketHandler.get_compression_options`.
        None (default) will disable compression.
        A dict (even an empty one) will enable compression.

        See the tornado docs for WebSocketHandler.get_compression_options for details.
        """
        ),
    )
    terminado_settings = Dict(
        Union([List(), Unicode()]),
        config=True,
        help=_i18n('Supply overrides for terminado. Currently only supports "shell_command".'),
    )

    cookie_options = Dict(
        config=True,
        help=_i18n("DEPRECATED. Use IdentityProvider.cookie_options"),
    )
    get_secure_cookie_kwargs = Dict(
        config=True,
        help=_i18n("DEPRECATED. Use IdentityProvider.get_secure_cookie_kwargs"),
    )

    @observe("cookie_options", "get_secure_cookie_kwargs")
    def _deprecated_cookie_config(self, change: t.Any) -> None:
        pass

    ssl_options = Dict(
        allow_none=True,
        config=True,
        help=_i18n(
            """Supply SSL options for the tornado HTTPServer.
            See the tornado docs for details."""
        ),
    )

    jinja_environment_options = Dict(
        config=True,
        help=_i18n("Supply extra arguments that will be passed to Jinja environment."),
    )

    jinja_template_vars = Dict(
        config=True,
        help=_i18n("Extra variables to supply to jinja templates when rendering."),
    )

    base_url = Unicode(
        "/",
        config=True,
        help="""The base URL for the Jupyter server.

                       Leading and trailing slashes can be omitted,
                       and will automatically be added.
                       """,
    )

    @validate("base_url")
    def _update_base_url(self, proposal: t.Any) -> str:
        pass

    extra_static_paths = List(
        Unicode(),
        config=True,
        help="""Extra paths to search for serving static files.

        This allows adding javascript/css to be available from the Jupyter server machine,
        or overriding individual files in the IPython""",
    )

    @property
    def static_file_path(self) -> list[str]:
        """return extra paths + the default location"""
        pass

    static_custom_path = List(Unicode(), help=_i18n("""Path to search for custom.js, css"""))

    @default("static_custom_path")
    def _default_static_custom_path(self) -> list[str]:
        pass

    extra_template_paths = List(
        Unicode(),
        config=True,
        help=_i18n(
            """Extra paths to search for serving jinja templates.

        Can be used to override templates from jupyter_server.templates."""
        ),
    )

    @property
    def template_file_path(self) -> list[str]:
        """return extra paths + the default locations"""
        pass

    extra_services = List(
        Unicode(),
        config=True,
        help=_i18n(
            """handlers that should be loaded at higher priority than the default services"""
        ),
    )

    websocket_url = Unicode(
        "",
        config=True,
        help="""The base URL for websockets,
        if it differs from the HTTP server (hint: it almost certainly doesn't).

        Should be in the form of an HTTP origin: ws[s]://hostname[:port]
        """,
    )

    quit_button = Bool(
        True,
        config=True,
        help="""If True, display controls to shut down the Jupyter server, such as menu items or buttons.""",
    )

    contents_manager_class = Type(
        default_value=AsyncLargeFileManager,
        klass=ContentsManager,
        config=True,
        help=_i18n("The content manager class to use."),
    )

    kernel_manager_class = Type(
        klass=MappingKernelManager,
        config=True,
        help=_i18n("The kernel manager class to use."),
    )

    @default("kernel_manager_class")
    def _default_kernel_manager_class(self) -> t.Union[str, type[AsyncMappingKernelManager]]:
        pass

    session_manager_class = Type(
        config=True,
        help=_i18n("The session manager class to use."),
    )

    @default("session_manager_class")
    def _default_session_manager_class(self) -> t.Union[str, type[SessionManager]]:
        pass

    kernel_websocket_connection_class = Type(
        klass=BaseKernelWebsocketConnection,
        config=True,
        help=_i18n("The kernel websocket connection class to use."),
    )

    @default("kernel_websocket_connection_class")
    def _default_kernel_websocket_connection_class(
        self,
    ) -> t.Union[str, type[ZMQChannelsWebsocketConnection]]:
        pass

    websocket_ping_interval = Integer(
        config=True,
        help="""
            Configure the websocket ping interval in seconds.

            Websockets are long-lived connections that are used by some Jupyter
            Server extensions.

            Periodic pings help to detect disconnected clients and keep the
            connection active. If this is set to None, then no pings will be
            performed.

            When a ping is sent, the client has ``websocket_ping_timeout``
            seconds to respond. If no response is received within this period,
            the connection will be closed from the server side.
        """,
    )
    websocket_ping_timeout = Integer(
        config=True,
        help="""
            Configure the websocket ping timeout in seconds.

            See ``websocket_ping_interval`` for details.
        """,
    )

    config_manager_class = Type(
        default_value=ConfigManager,
        config=True,
        help=_i18n("The config manager class to use"),
    )

    kernel_spec_manager = Instance(KernelSpecManager, allow_none=True)

    kernel_spec_manager_class = Type(
        config=True,
        help="""
        The kernel spec manager class to use. Should be a subclass
        of `jupyter_client.kernelspec.KernelSpecManager`.

        The Api of KernelSpecManager is provisional and might change
        without warning between this version of Jupyter and the next stable one.
        """,
    )

    @default("kernel_spec_manager_class")
    def _default_kernel_spec_manager_class(self) -> t.Union[str, type[KernelSpecManager]]:
        pass

    login_handler_class = Type(
        default_value=LoginHandler,
        klass=web.RequestHandler,
        allow_none=True,
        config=True,
        help=_i18n("The login handler class to use."),
    )

    logout_handler_class = Type(
        default_value=LogoutHandler,
        klass=web.RequestHandler,
        allow_none=True,
        config=True,
        help=_i18n("The logout handler class to use."),
    )
    # TODO: detect deprecated login handler config

    authorizer_class = Type(
        default_value=AllowAllAuthorizer,
        klass=Authorizer,
        config=True,
        help=_i18n("The authorizer class to use."),
    )

    identity_provider_class = Type(
        default_value=PasswordIdentityProvider,
        klass=IdentityProvider,
        config=True,
        help=_i18n("The identity provider class to use."),
    )

    trust_xheaders = Bool(
        False,
        config=True,
        help=(
            _i18n(
                "Whether to trust or not X-Scheme/X-Forwarded-Proto and X-Real-Ip/X-Forwarded-For headers"
                "sent by the upstream reverse proxy. Necessary if the proxy handles SSL"
            )
        ),
    )

    event_logger = Instance(
        EventLogger,
        allow_none=True,
        help="An EventLogger for emitting structured event data from Jupyter Server and extensions.",
    )

    info_file = Unicode()

    @default("info_file")
    def _default_info_file(self) -> str:
        pass

    no_browser_open_file = Bool(
        False, help="If True, do not write redirect HTML file disk, or show in messages."
    )

    browser_open_file = Unicode()

    @default("browser_open_file")
    def _default_browser_open_file(self) -> str:
        pass

    browser_open_file_to_run = Unicode()

    @default("browser_open_file_to_run")
    def _default_browser_open_file_to_run(self) -> str:
        pass

    pylab = Unicode(
        "disabled",
        config=True,
        help=_i18n(
            """
        DISABLED: use %pylab or %matplotlib in the notebook to enable matplotlib.
        """
        ),
    )

    @observe("pylab")
    def _update_pylab(self, change: t.Any) -> None:
        """when --pylab is specified, display a warning and exit"""
        pass

    notebook_dir = Unicode(config=True, help=_i18n("DEPRECATED, use root_dir."))

    @observe("notebook_dir")
    def _update_notebook_dir(self, change: t.Any) -> None:
        pass

    external_connection_dir = Unicode(
        None,
        allow_none=True,
        config=True,
        help=_i18n(
            "The directory to look at for external kernel connection files, if allow_external_kernels is True. "
            "Defaults to Jupyter runtime_dir/external_kernels. "
            "Make sure that this directory is not filled with left-over connection files, "
            "that could result in unnecessary kernel manager creations."
        ),
    )

    allow_external_kernels = Bool(
        False,
        config=True,
        help=_i18n(
            "Whether or not to allow external kernels, whose connection files are placed in external_connection_dir."
        ),
    )

    root_dir = Unicode(config=True, help=_i18n("The directory to use for notebooks and kernels."))
    _root_dir_set = False

    @default("root_dir")
    def _default_root_dir(self) -> str:
        pass

    def _normalize_dir(self, value: str) -> str:
        """Normalize a directory."""
        pass

    @validate("root_dir")
    def _root_dir_validate(self, proposal: t.Any) -> str:
        pass

    @observe("root_dir")
    def _root_dir_changed(self, change: t.Any) -> None:
        # record that root_dir is set,
        # which affects loading of deprecated notebook_dir
        pass

    preferred_dir = Unicode(
        config=True,
        help=trans.gettext(
            "Preferred starting directory to use for notebooks and kernels. ServerApp.preferred_dir is deprecated in jupyter-server 2.0. Use FileContentsManager.preferred_dir instead"
        ),
    )

    @default("preferred_dir")
    def _default_prefered_dir(self) -> str:
        pass

    @validate("preferred_dir")
    def _preferred_dir_validate(self, proposal: t.Any) -> str:
        pass

    @observe("server_extensions")
    def _update_server_extensions(self, change: t.Any) -> None:
        pass

    jpserver_extensions = Dict(
        default_value={},
        value_trait=Bool(),
        config=True,
        help=(
            _i18n(
                "Dict of Python modules to load as Jupyter server extensions."
                "Entry values can be used to enable and disable the loading of"
                "the extensions. The extensions will be loaded in alphabetical "
                "order."
            )
        ),
    )

    reraise_server_extension_failures = Bool(
        False,
        config=True,
        help=_i18n("Reraise exceptions encountered loading server extensions?"),
    )

    kernel_ws_protocol = Unicode(
        allow_none=True,
        config=True,
        help=_i18n("DEPRECATED. Use ZMQChannelsWebsocketConnection.kernel_ws_protocol"),
    )

    @observe("kernel_ws_protocol")
    def _deprecated_kernel_ws_protocol(self, change: t.Any) -> None:
        pass

    limit_rate = Bool(
        allow_none=True,
        config=True,
        help=_i18n("DEPRECATED. Use ZMQChannelsWebsocketConnection.limit_rate"),
    )

    @observe("limit_rate")
    def _deprecated_limit_rate(self, change: t.Any) -> None:
        pass

    iopub_msg_rate_limit = Float(
        allow_none=True,
        config=True,
        help=_i18n("DEPRECATED. Use ZMQChannelsWebsocketConnection.iopub_msg_rate_limit"),
    )

    @observe("iopub_msg_rate_limit")
    def _deprecated_iopub_msg_rate_limit(self, change: t.Any) -> None:
        pass

    iopub_data_rate_limit = Float(
        allow_none=True,
        config=True,
        help=_i18n("DEPRECATED. Use ZMQChannelsWebsocketConnection.iopub_data_rate_limit"),
    )

    @observe("iopub_data_rate_limit")
    def _deprecated_iopub_data_rate_limit(self, change: t.Any) -> None:
        pass

    rate_limit_window = Float(
        allow_none=True,
        config=True,
        help=_i18n("DEPRECATED. Use ZMQChannelsWebsocketConnection.rate_limit_window"),
    )

    @observe("rate_limit_window")
    def _deprecated_rate_limit_window(self, change: t.Any) -> None:
        pass

    shutdown_no_activity_timeout = Integer(
        0,
        config=True,
        help=(
            "Shut down the server after N seconds with no kernels"
            "running and no activity. "
            "This can be used together with culling idle kernels "
            "(MappingKernelManager.cull_idle_timeout) to "
            "shutdown the Jupyter server when it's not in use. This is not "
            "precisely timed: it may shut down up to a minute later. "
            "0 (the default) disables this automatic shutdown."
        ),
    )

    terminals_enabled = Bool(
        config=True,
        help=_i18n(
            """Set to False to disable terminals.

         This does *not* make the server more secure by itself.
         Anything the user can in a terminal, they can also do in a notebook.

         Terminals may also be automatically disabled if the terminado package
         is not available.
         """
        ),
    )

    @default("terminals_enabled")
    def _default_terminals_enabled(self) -> bool:
        pass

    authenticate_prometheus = Bool(
        True,
        help=""""
        Require authentication to access prometheus metrics.
        """,
        config=True,
    )

    record_http_request_metrics = Bool(
        True,
        help="""
        Record http_request_duration_seconds metric in the metrics endpoint.

        Since a histogram is exposed for each request handler, this can create a
        *lot* of metrics, creating operational challenges for multitenant deployments.

        Set to False to disable recording the http_request_duration_seconds metric.
        """,
    )

    extra_log_scrub_param_keys = List(
        Unicode(),
        default_value=[],
        config=True,
        help="""
        Additional URL parameter keys to scrub from logs.

        These will be added to the default list of scrubbed parameter keys.
        Any URL parameter whose key contains one of these substrings will have
        its value replaced with '[secret]' in the logs. This is to prevent
        sensitive information like authentication tokens from being leaked
        in log files.

        Default scrubbed keys: ["token", "auth", "key", "code", "state", "xsrf"]
        """,
    )

    static_immutable_cache = List(
        Unicode(),
        help="""
        Paths to set up static files as immutable.

        This allow setting up the cache control of static files as immutable.
        It should be used for static file named with a hash for instance.
        """,
        config=True,
    )

    _starter_app = Instance(
        default_value=None,
        allow_none=True,
        klass="jupyter_server.extension.application.ExtensionApp",
    )

    @property
    def starter_app(self) -> t.Any:
        """Get the Extension that started this server."""
        pass

    def parse_command_line(self, argv: t.Optional[list[str]] = None) -> None:
        """Parse the command line options."""
        pass

    def init_configurables(self) -> None:
        """Initialize configurables."""
        pass

    def init_logging(self) -> None:
        """Initialize logging."""
        pass

    def init_event_logger(self) -> None:
        """Initialize the Event Bus."""
        pass

    def init_webapp(self) -> None:
        """initialize tornado webapp"""
        pass

    def init_resources(self) -> None:
        """initialize system resources"""
        pass

    def _get_urlparts(
        self, path: t.Optional[str] = None, include_token: bool = False
    ) -> urllib.parse.ParseResult:
        """Constructs a urllib named tuple, ParseResult,
        with default values set by server config.
        The returned tuple can be manipulated using the `_replace` method.
        """
        pass

    @property
    def public_url(self) -> str:
        pass

    @property
    def local_url(self) -> str:
        pass

    @property
    def display_url(self) -> str:
        """Human readable string with URLs for interacting
        with the running Jupyter Server
        """
        pass

    @property
    def connection_url(self) -> str:
        pass

    def init_signal(self) -> None:
        """Initialize signal handlers."""
        pass

    def _handle_sigint(self, sig: t.Any, frame: t.Any) -> None:
        """SIGINT handler spawns confirmation dialog

        Note:
            JupyterHub replaces this method with _signal_stop
            in order to bypass the interactive prompt.
            https://github.com/jupyterhub/jupyterhub/pull/4864

        """
        pass

    def _restore_sigint_handler(self) -> None:
        """callback for restoring original SIGINT handler"""
        pass

    def _confirm_exit(self) -> None:
        """confirm shutdown on ^C

        A second ^C, or answering 'y' within 5s will cause shutdown,
        otherwise original SIGINT handler will be restored.

        This doesn't work on Windows.
        """
        pass

    def _signal_stop(self, sig: t.Any, frame: t.Any) -> None:
        """Handle a stop signal.

        Note:
            JupyterHub configures this method to be called for SIGINT.
            https://github.com/jupyterhub/jupyterhub/pull/4864

        """
        pass

    def _signal_info(self, sig: t.Any, frame: t.Any) -> None:
        """Handle an info signal."""
        pass

    def init_components(self) -> None:
        """Check the components submodule, and warn if it's unclean"""
        # TODO: this should still check, but now we use bower, not git submodule

    def find_server_extensions(self) -> None:
        """
        Searches Jupyter paths for jpserver_extensions.
        """
        pass

    def init_server_extensions(self) -> None:
        """
        If an extension's metadata includes an 'app' key,
        the value must be a subclass of ExtensionApp. An instance
        of the class will be created at this step. The config for
        this instance will inherit the ServerApp's config object
        and load its own config.
        """
        pass

    def load_server_extensions(self) -> None:
        """Load any extensions specified by config.

        Import the module, then call the load_jupyter_server_extension function,
        if one exists.

        The extension API is experimental, and may change in future releases.
        """
        pass

    def init_mime_overrides(self) -> None:
        # On some Windows machines, an application has registered incorrect
        # mimetypes in the registry.
        # Tornado uses this when serving .css and .js files, causing browsers to
        # reject these files. We know the mimetype always needs to be text/css for css
        # and application/javascript for JS, so we override it here
        # and explicitly tell the mimetypes to not trust the Windows registry
        pass

    def shutdown_no_activity(self) -> None:
        """Shutdown server on timeout when there are no kernels or terminals."""
        pass

    def init_shutdown_no_activity(self) -> None:
        """Initialize a shutdown on no activity."""
        pass

    @property
    def http_server(self) -> httpserver.HTTPServer:
        """An instance of Tornado's HTTPServer class for the Server Web Application."""
        pass

    def init_httpserver(self) -> None:
        """Creates an instance of a Tornado HTTPServer for the Server Web Application
        and sets the http_server attribute.
        """
        pass

    def _bind_http_server(self) -> None:
        """Bind our http server."""
        pass

    def _bind_http_server_unix(self) -> bool:
        """Bind an http server on unix."""
        pass

    def _bind_http_server_tcp(self) -> bool:
        """Bind a tcp server."""
        pass

    def _find_http_port(self) -> None:
        """Find an available http port."""
        pass

    @staticmethod
    def _init_asyncio_patch() -> None:
        """set default asyncio policy to be compatible with tornado

        Tornado 6.0 is not compatible with default asyncio
        ProactorEventLoop, which lacks basic *_reader methods.
        Tornado 6.1 adds a workaround to add these methods in a thread,
        but SelectorEventLoop should still be preferred
        to avoid the extra thread for ~all of our events,
        at least until asyncio adds *_reader methods
        to proactor.
        """
        pass

    def init_metrics(self) -> None:
        """
        Initialize any prometheus metrics that need to be set up on server startup
        """
        pass

    @catch_config_error
    def initialize(
        self,
        argv: t.Optional[list[str]] = None,
        find_extensions: bool = True,
        new_httpserver: bool = True,
        starter_extension: t.Any = None,
    ) -> None:
        """Initialize the Server application class, configurables, web application, and http server.

        Parameters
        ----------
        argv : list or None
            CLI arguments to parse.
        find_extensions : bool
            If True, find and load extensions listed in Jupyter config paths. If False,
            only load extensions that are passed to ServerApp directly through
            the `argv`, `config`, or `jpserver_extensions` arguments.
        new_httpserver : bool
            If True, a tornado HTTPServer instance will be created and configured for the Server Web
            Application. This will set the http_server attribute of this class.
        starter_extension : str
            If given, it references the name of an extension point that started the Server.
            We will try to load configuration from extension point
        """
        pass

    async def cleanup_kernels(self) -> None:
        """Shutdown all kernels.

        The kernels will shutdown themselves when this process no longer exists,
        but explicit shutdown allows the KernelManagers to cleanup the connection files.
        """
        pass

    async def cleanup_extensions(self) -> None:
        """Call shutdown hooks in all extensions."""
        pass

    def running_server_info(self, kernel_count: bool = True) -> str:
        """Return the current working directory and the server url information"""
        pass

    def server_info(self) -> dict[str, t.Any]:
        """Return a JSONable dict of information about this server."""
        pass

    def write_server_info_file(self) -> None:
        """Write the result of server_info() to the JSON file info_file."""
        pass

    def remove_server_info_file(self) -> None:
        """Remove the jpserver-<pid>.json file created for this server.

        Ignores the error raised when the file has already been removed.
        """
        pass

    def _resolve_file_to_run_and_root_dir(self) -> str:
        """Returns a relative path from file_to_run
        to root_dir. If root_dir and file_to_run
        are incompatible, i.e. on different subtrees,
        crash the app and log a critical message. Note
        that if root_dir is not configured and file_to_run
        is configured, root_dir will be set to the parent
        directory of file_to_run.
        """
        pass

    def _write_browser_open_file(self, url: str, fh: t.Any) -> None:
        """Write the browser open file."""
        pass

    def write_browser_open_files(self) -> None:
        """Write an `browser_open_file` and `browser_open_file_to_run` files

        This can be used to open a file directly in a browser.
        """
        pass

    def write_browser_open_file(self) -> None:
        """Write an jpserver-<pid>-open.html file

        This can be used to open the notebook in a browser
        """
        pass

    def remove_browser_open_files(self) -> None:
        """Remove the `browser_open_file` and `browser_open_file_to_run` files
        created for this server.

        Ignores the error raised when the file has already been removed.
        """
        pass

    def remove_browser_open_file(self) -> None:
        """Remove the jpserver-<pid>-open.html file created for this server.

        Ignores the error raised when the file has already been removed.
        """
        pass

    def _prepare_browser_open(self) -> tuple[str, t.Optional[str]]:
        """Prepare to open the browser."""
        pass

    def launch_browser(self) -> None:
        """Launch the browser."""
        pass

    def start_app(self) -> None:
        """Start the Jupyter Server application."""
        pass

    async def _cleanup(self) -> None:
        """General cleanup of files, extensions and kernels created
        by this instance ServerApp.
        """
        pass

    def start_ioloop(self) -> None:
        """Start the IO Loop."""
        pass

    def init_ioloop(self) -> None:
        """init self.io_loop so that an extension can use it by io_loop.call_later() to create background tasks"""
        pass

    async def _post_start(self):
        """Add an async hook to start tasks after the event loop is running.

        This will also attempt to start all tasks found in
        the `start_extension` method in Extension Apps.
        """
        pass

    def start(self) -> None:
        """Start the Jupyter server app, after initialization

        This method takes no arguments so all configuration and initialization
        must be done prior to calling this method."""
        pass

    async def _stop(self) -> None:
        """Cleanup resources and stop the IO Loop."""
        pass

    def stop(self, from_signal: bool = False) -> None:
        """Cleanup resources and stop the server."""
        pass


def list_running_servers(
    runtime_dir: t.Optional[str] = None, log: t.Optional[logging.Logger] = None
) -> t.Generator[t.Any, None, None]:
    """Iterate over the server info files of running Jupyter servers.

    Given a runtime directory, find jpserver-* files in the security directory,
    and yield dicts of their information, each one pertaining to
    a currently running Jupyter server instance.
    """
    pass


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------

main = launch_new_instance = ServerApp.launch_instance
