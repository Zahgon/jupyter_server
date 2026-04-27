"""A kernel gateway client."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import json
import logging
import os
import typing as ty
from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.cookies import Morsel, SimpleCookie
from socket import gaierror

from jupyter_events import EventLogger
from tornado import web
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPResponse
from tornado.httputil import HTTPHeaders
from traitlets import (
    Bool,
    Float,
    Instance,
    Int,
    TraitError,
    Type,
    Unicode,
    default,
    observe,
    validate,
)
from traitlets.config import LoggingConfigurable, SingletonConfigurable

from jupyter_server import DEFAULT_EVENTS_SCHEMA_PATH, JUPYTER_SERVER_EVENTS_URI

ERROR_STATUS = "error"
SUCCESS_STATUS = "success"
STATUS_KEY = "status"
STATUS_CODE_KEY = "status_code"
MESSAGE_KEY = "msg"


class GatewayTokenRenewerMeta(ABCMeta, type(LoggingConfigurable)):  # type: ignore[misc]
    """The metaclass necessary for proper ABC behavior in a Configurable."""


class GatewayTokenRenewerBase(  # type:ignore[metaclass]
    ABC, LoggingConfigurable, metaclass=GatewayTokenRenewerMeta
):
    """
    Abstract base class for refreshing tokens used between this server and a Gateway
    server.  Implementations requiring additional configuration can extend their class
    with appropriate configuration values or convey those values via appropriate
    environment variables relative to the implementation.
    """

    @abstractmethod
    def get_token(
        self,
        auth_header_key: str,
        auth_scheme: ty.Union[str, None],
        auth_token: str,
        **kwargs: ty.Any,
    ) -> str:
        """
        Given the current authorization header key, scheme, and token, this method returns
        a (potentially renewed) token for use against the Gateway server.
        """


class NoOpTokenRenewer(GatewayTokenRenewerBase):
    """NoOpTokenRenewer is the default value to the GatewayClient trait
    `gateway_token_renewer` and merely returns the provided token.
    """

    def get_token(
        self,
        auth_header_key: str,
        auth_scheme: ty.Union[str, None],
        auth_token: str,
        **kwargs: ty.Any,
    ) -> str:
        """This implementation simply returns the current authorization token."""
        pass


class GatewayClient(SingletonConfigurable):
    """This class manages the configuration.  It's its own singleton class so
    that we can share these values across all objects.  It also contains some
    options.
    helper methods to build request arguments out of the various config
    """

    event_schema_id = JUPYTER_SERVER_EVENTS_URI + "/gateway_client/v1"
    event_logger = Instance(EventLogger).tag(config=True)

    @default("event_logger")
    def _default_event_logger(self):
        pass

    def emit(self, data):
        """Emit event using the core event schema from Jupyter Server's Gateway Client."""
        pass

    url = Unicode(
        default_value=None,
        allow_none=True,
        config=True,
        help="""The url of the Kernel or Enterprise Gateway server where
kernel specifications are defined and kernel management takes place.
If defined, this Notebook server acts as a proxy for all kernel
management and kernel specification retrieval.  (JUPYTER_GATEWAY_URL env var)
        """,
    )

    url_env = "JUPYTER_GATEWAY_URL"

    @default("url")
    def _url_default(self):
        pass

    @validate("url")
    def _url_validate(self, proposal):
        pass

    ws_url = Unicode(
        default_value=None,
        allow_none=True,
        config=True,
        help="""The websocket url of the Kernel or Enterprise Gateway server.  If not provided, this value
will correspond to the value of the Gateway url with 'ws' in place of 'http'.  (JUPYTER_GATEWAY_WS_URL env var)
        """,
    )

    ws_url_env = "JUPYTER_GATEWAY_WS_URL"

    @default("ws_url")
    def _ws_url_default(self):
        pass

    @validate("ws_url")
    def _ws_url_validate(self, proposal):
        pass

    kernels_endpoint_default_value = "/api/kernels"
    kernels_endpoint_env = "JUPYTER_GATEWAY_KERNELS_ENDPOINT"
    kernels_endpoint = Unicode(
        default_value=kernels_endpoint_default_value,
        config=True,
        help="""The gateway API endpoint for accessing kernel resources (JUPYTER_GATEWAY_KERNELS_ENDPOINT env var)""",
    )

    @default("kernels_endpoint")
    def _kernels_endpoint_default(self):
        pass

    kernelspecs_endpoint_default_value = "/api/kernelspecs"
    kernelspecs_endpoint_env = "JUPYTER_GATEWAY_KERNELSPECS_ENDPOINT"
    kernelspecs_endpoint = Unicode(
        default_value=kernelspecs_endpoint_default_value,
        config=True,
        help="""The gateway API endpoint for accessing kernelspecs (JUPYTER_GATEWAY_KERNELSPECS_ENDPOINT env var)""",
    )

    @default("kernelspecs_endpoint")
    def _kernelspecs_endpoint_default(self):
        pass

    kernelspecs_resource_endpoint_default_value = "/kernelspecs"
    kernelspecs_resource_endpoint_env = "JUPYTER_GATEWAY_KERNELSPECS_RESOURCE_ENDPOINT"
    kernelspecs_resource_endpoint = Unicode(
        default_value=kernelspecs_resource_endpoint_default_value,
        config=True,
        help="""The gateway endpoint for accessing kernelspecs resources
(JUPYTER_GATEWAY_KERNELSPECS_RESOURCE_ENDPOINT env var)""",
    )

    @default("kernelspecs_resource_endpoint")
    def _kernelspecs_resource_endpoint_default(self):
        pass

    connect_timeout_default_value = 40.0
    connect_timeout_env = "JUPYTER_GATEWAY_CONNECT_TIMEOUT"
    connect_timeout = Float(
        default_value=connect_timeout_default_value,
        config=True,
        help="""The time allowed for HTTP connection establishment with the Gateway server.
(JUPYTER_GATEWAY_CONNECT_TIMEOUT env var)""",
    )

    @default("connect_timeout")
    def _connect_timeout_default(self):
        pass

    request_timeout_default_value = 42.0
    request_timeout_env = "JUPYTER_GATEWAY_REQUEST_TIMEOUT"
    request_timeout = Float(
        default_value=request_timeout_default_value,
        config=True,
        help="""The time allowed for HTTP request completion. (JUPYTER_GATEWAY_REQUEST_TIMEOUT env var)""",
    )

    @default("request_timeout")
    def _request_timeout_default(self):
        pass

    client_key = Unicode(
        default_value=None,
        allow_none=True,
        config=True,
        help="""The filename for client SSL key, if any.  (JUPYTER_GATEWAY_CLIENT_KEY env var)
        """,
    )
    client_key_env = "JUPYTER_GATEWAY_CLIENT_KEY"

    @default("client_key")
    def _client_key_default(self):
        pass

    client_cert = Unicode(
        default_value=None,
        allow_none=True,
        config=True,
        help="""The filename for client SSL certificate, if any.  (JUPYTER_GATEWAY_CLIENT_CERT env var)
        """,
    )
    client_cert_env = "JUPYTER_GATEWAY_CLIENT_CERT"

    @default("client_cert")
    def _client_cert_default(self):
        pass

    ca_certs = Unicode(
        default_value=None,
        allow_none=True,
        config=True,
        help="""The filename of CA certificates or None to use defaults.  (JUPYTER_GATEWAY_CA_CERTS env var)
        """,
    )
    ca_certs_env = "JUPYTER_GATEWAY_CA_CERTS"

    @default("ca_certs")
    def _ca_certs_default(self):
        pass

    http_user = Unicode(
        default_value=None,
        allow_none=True,
        config=True,
        help="""The username for HTTP authentication. (JUPYTER_GATEWAY_HTTP_USER env var)
        """,
    )
    http_user_env = "JUPYTER_GATEWAY_HTTP_USER"

    @default("http_user")
    def _http_user_default(self):
        pass

    http_pwd = Unicode(
        default_value=None,
        allow_none=True,
        config=True,
        help="""The password for HTTP authentication.  (JUPYTER_GATEWAY_HTTP_PWD env var)
        """,
    )
    http_pwd_env = "JUPYTER_GATEWAY_HTTP_PWD"  # noqa: S105

    @default("http_pwd")
    def _http_pwd_default(self):
        pass

    headers_default_value = "{}"
    headers_env = "JUPYTER_GATEWAY_HEADERS"
    headers = Unicode(
        default_value=headers_default_value,
        allow_none=True,
        config=True,
        help="""Additional HTTP headers to pass on the request.  This value will be converted to a dict.
          (JUPYTER_GATEWAY_HEADERS env var)
        """,
    )

    @default("headers")
    def _headers_default(self):
        pass

    auth_header_key_default_value = "Authorization"
    auth_header_key = Unicode(
        config=True,
        help="""The authorization header's key name (typically 'Authorization') used in the HTTP headers. The
header will be formatted as::

{'{auth_header_key}': '{auth_scheme} {auth_token}'}

If the authorization header key takes a single value, `auth_scheme` should be set to None and
'auth_token' should be configured to use the appropriate value.

(JUPYTER_GATEWAY_AUTH_HEADER_KEY env var)""",
    )
    auth_header_key_env = "JUPYTER_GATEWAY_AUTH_HEADER_KEY"

    @default("auth_header_key")
    def _auth_header_key_default(self):
        pass

    auth_token_default_value = ""
    auth_token = Unicode(
        default_value=None,
        allow_none=True,
        config=True,
        help="""The authorization token used in the HTTP headers. The header will be formatted as::

{'{auth_header_key}': '{auth_scheme} {auth_token}'}

(JUPYTER_GATEWAY_AUTH_TOKEN env var)""",
    )
    auth_token_env = "JUPYTER_GATEWAY_AUTH_TOKEN"  # noqa: S105

    @default("auth_token")
    def _auth_token_default(self):
        pass

    auth_scheme_default_value = "token"  # This value is purely for backwards compatibility
    auth_scheme = Unicode(
        allow_none=True,
        config=True,
        help="""The auth scheme, added as a prefix to the authorization token used in the HTTP headers.
(JUPYTER_GATEWAY_AUTH_SCHEME env var)""",
    )
    auth_scheme_env = "JUPYTER_GATEWAY_AUTH_SCHEME"

    @default("auth_scheme")
    def _auth_scheme_default(self):
        pass

    validate_cert_default_value = True
    validate_cert_env = "JUPYTER_GATEWAY_VALIDATE_CERT"
    validate_cert = Bool(
        default_value=validate_cert_default_value,
        config=True,
        help="""For HTTPS requests, determines if server's certificate should be validated or not.
(JUPYTER_GATEWAY_VALIDATE_CERT env var)""",
    )

    @default("validate_cert")
    def _validate_cert_default(self):
        pass

    allowed_envs_default_value = ""
    allowed_envs_env = "JUPYTER_GATEWAY_ALLOWED_ENVS"
    allowed_envs = Unicode(
        default_value=allowed_envs_default_value,
        config=True,
        help="""A comma-separated list of environment variable names that will be included, along with
their values, in the kernel startup request.  The corresponding `client_envs` configuration
value must also be set on the Gateway server - since that configuration value indicates which
environmental values to make available to the kernel. (JUPYTER_GATEWAY_ALLOWED_ENVS env var)""",
    )

    @default("allowed_envs")
    def _allowed_envs_default(self):
        pass

    env_whitelist = Unicode(
        default_value=allowed_envs_default_value,
        config=True,
        help="""Deprecated, use `GatewayClient.allowed_envs`""",
    )

    gateway_retry_interval_default_value = 1.0
    gateway_retry_interval_env = "JUPYTER_GATEWAY_RETRY_INTERVAL"
    gateway_retry_interval = Float(
        default_value=gateway_retry_interval_default_value,
        config=True,
        help="""The time allowed for HTTP reconnection with the Gateway server for the first time.
Next will be JUPYTER_GATEWAY_RETRY_INTERVAL multiplied by two in factor of numbers of retries
but less than JUPYTER_GATEWAY_RETRY_INTERVAL_MAX.
(JUPYTER_GATEWAY_RETRY_INTERVAL env var)""",
    )

    @default("gateway_retry_interval")
    def _gateway_retry_interval_default(self):
        pass

    gateway_retry_interval_max_default_value = 30.0
    gateway_retry_interval_max_env = "JUPYTER_GATEWAY_RETRY_INTERVAL_MAX"
    gateway_retry_interval_max = Float(
        default_value=gateway_retry_interval_max_default_value,
        config=True,
        help="""The maximum time allowed for HTTP reconnection retry with the Gateway server.
(JUPYTER_GATEWAY_RETRY_INTERVAL_MAX env var)""",
    )

    @default("gateway_retry_interval_max")
    def _gateway_retry_interval_max_default(self):
        pass

    gateway_retry_max_default_value = 5
    gateway_retry_max_env = "JUPYTER_GATEWAY_RETRY_MAX"
    gateway_retry_max = Int(
        default_value=gateway_retry_max_default_value,
        config=True,
        help="""The maximum retries allowed for HTTP reconnection with the Gateway server.
(JUPYTER_GATEWAY_RETRY_MAX env var)""",
    )

    @default("gateway_retry_max")
    def _gateway_retry_max_default(self):
        pass

    gateway_token_renewer_class_default_value = (
        "jupyter_server.gateway.gateway_client.NoOpTokenRenewer"  # noqa: S105
    )
    gateway_token_renewer_class_env = "JUPYTER_GATEWAY_TOKEN_RENEWER_CLASS"  # noqa: S105
    gateway_token_renewer_class = Type(
        klass=GatewayTokenRenewerBase,
        config=True,
        help="""The class to use for Gateway token renewal. (JUPYTER_GATEWAY_TOKEN_RENEWER_CLASS env var)""",
    )

    @default("gateway_token_renewer_class")
    def _gateway_token_renewer_class_default(self):
        pass

    launch_timeout_pad_default_value = 2.0
    launch_timeout_pad_env = "JUPYTER_GATEWAY_LAUNCH_TIMEOUT_PAD"
    launch_timeout_pad = Float(
        default_value=launch_timeout_pad_default_value,
        config=True,
        help="""Timeout pad to be ensured between KERNEL_LAUNCH_TIMEOUT and request_timeout
such that request_timeout >= KERNEL_LAUNCH_TIMEOUT + launch_timeout_pad.
(JUPYTER_GATEWAY_LAUNCH_TIMEOUT_PAD env var)""",
    )

    @default("launch_timeout_pad")
    def _launch_timeout_pad_default(self):
        pass

    accept_cookies_value = False
    accept_cookies_env = "JUPYTER_GATEWAY_ACCEPT_COOKIES"
    accept_cookies = Bool(
        default_value=accept_cookies_value,
        config=True,
        help="""Accept and manage cookies sent by the service side. This is often useful
        for load balancers to decide which backend node to use.
        (JUPYTER_GATEWAY_ACCEPT_COOKIES env var)""",
    )

    @default("accept_cookies")
    def _accept_cookies_default(self):
        pass

    _deprecated_traits = {
        "env_whitelist": ("allowed_envs", "2.0"),
    }

    # Method copied from
    # https://github.com/jupyterhub/jupyterhub/blob/d1a85e53dccfc7b1dd81b0c1985d158cc6b61820/jupyterhub/auth.py#L143-L161
    @observe(*list(_deprecated_traits))
    def _deprecated_trait(self, change):
        """observer for deprecated traits"""
        pass

    @property
    def gateway_enabled(self):
        pass

    # Ensure KERNEL_LAUNCH_TIMEOUT has a default value.
    KERNEL_LAUNCH_TIMEOUT = int(os.environ.get("KERNEL_LAUNCH_TIMEOUT", "40"))

    _connection_args: dict[str, ty.Any]  # initialized on first use

    gateway_token_renewer: GatewayTokenRenewerBase

    def __init__(self, **kwargs):
        """Initialize a gateway client."""
        super().__init__(**kwargs)
        self._connection_args = {}  # initialized on first use
        self.gateway_token_renewer = self.gateway_token_renewer_class(parent=self, log=self.log)  # type:ignore[abstract]

        # store of cookies with store time
        self._cookies: dict[str, tuple[Morsel[ty.Any], datetime]] = {}

    def init_connection_args(self):
        """Initialize arguments used on every request.  Since these are primarily static values,
        we'll perform this operation once.
        """
        pass

    def load_connection_args(self, **kwargs):
        """Merges the static args relative to the connection, with the given keyword arguments.  If static
        args have yet to be initialized, we'll do that here.

        """
        pass

    def update_cookies(self, headers: HTTPHeaders) -> None:
        """Update cookies from response headers"""
        pass

    def _clear_expired_cookies(self) -> None:
        """Clear expired cookies."""
        pass

    def _update_cookie_header(self, connection_args: dict[str, ty.Any]) -> None:
        """Update a cookie header."""
        pass


class RetryableHTTPClient:
    """
    Inspired by urllib.util.Retry (https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html),
    this class is initialized with desired retry characteristics, uses a recursive method `fetch()` against an instance
    of `AsyncHTTPClient` which tracks the current retry count across applicable request retries.
    """

    MAX_RETRIES_DEFAULT = 2
    MAX_RETRIES_CAP = 10  # The upper limit to max_retries value.
    max_retries: int = int(os.getenv("JUPYTER_GATEWAY_MAX_REQUEST_RETRIES", MAX_RETRIES_DEFAULT))
    max_retries = max(0, min(max_retries, MAX_RETRIES_CAP))  # Enforce boundaries
    retried_methods: set[str] = {"GET", "DELETE"}
    retried_errors: set[int] = {502, 503, 504, 599}
    retried_exceptions: set[type] = {ConnectionError}
    backoff_factor: float = 0.1

    def __init__(self):
        """Initialize the retryable http client."""
        self.retry_count: int = 0
        self.client: AsyncHTTPClient = AsyncHTTPClient()

    async def fetch(self, endpoint: str, **kwargs: ty.Any) -> HTTPResponse:
        """
        Retryable AsyncHTTPClient.fetch() method.  When the request fails, this method will
        recurse up to max_retries times if the condition deserves a retry.
        """
        pass

    async def _fetch(self, endpoint: str, **kwargs: ty.Any) -> HTTPResponse:
        """
        Performs the fetch against the contained AsyncHTTPClient instance and determines
        if retry is necessary on any exceptions.  If so, retry is performed recursively.
        """
        pass

    async def _is_retryable(self, method: str, exception: Exception) -> bool:
        """Determines if the given exception is retryable based on object's configuration."""
        pass


async def gateway_request(endpoint: str, **kwargs: ty.Any) -> HTTPResponse:
    """Make an async request to kernel gateway endpoint, returns a response"""
    pass
