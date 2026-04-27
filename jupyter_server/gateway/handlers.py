"""Gateway API handlers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import random
import warnings
from typing import Any, Optional, cast

from jupyter_client.session import Session
from tornado import web
from tornado.concurrent import Future
from tornado.escape import json_decode, url_escape, utf8
from tornado.httpclient import HTTPRequest
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.websocket import WebSocketHandler, websocket_connect
from traitlets.config.configurable import LoggingConfigurable

from ..base.handlers import APIHandler, JupyterHandler
from ..utils import url_path_join
from .gateway_client import GatewayClient

warnings.warn(
    "The jupyter_server.gateway.handlers module is deprecated and will not be supported in Jupyter Server 3.0",
    DeprecationWarning,
    stacklevel=2,
)


# Keepalive ping interval (default: 30 seconds)
GATEWAY_WS_PING_INTERVAL_SECS = int(os.getenv("GATEWAY_WS_PING_INTERVAL_SECS", "30"))


class WebSocketChannelsHandler(WebSocketHandler, JupyterHandler):
    """Gateway web socket channels handler."""

    session = None
    gateway = None
    kernel_id = None
    ping_callback = None

    def check_origin(self, origin=None):
        """Check origin for the socket."""
        pass

    def set_default_headers(self):
        """Undo the set_default_headers in JupyterHandler which doesn't make sense for websockets"""

    def get_compression_options(self):
        """Get the compression options for the socket."""
        pass

    def authenticate(self):
        """Run before finishing the GET request

        Extend this method to add logic that should fire before
        the websocket finishes completing.
        """
        pass

    def initialize(self):
        """Initialize the socket."""
        pass

    async def get(self, kernel_id, *args, **kwargs):
        """Get the socket."""
        pass

    def send_ping(self):
        """Send a ping to the socket."""
        pass

    def open(self, kernel_id: str, *args, **kwargs) -> None:  # type: ignore[override]
        """Handle web socket connection open to notebook server and delegate to gateway web socket handler"""
        pass

    def on_message(self, message):
        """Forward message to gateway web socket handler."""
        pass

    def write_message(self, message, binary=False):
        """Send message back to notebook client.  This is called via callback from self.gateway._read_messages."""
        pass

    def on_close(self):
        """Handle a closing socket."""
        pass

    @staticmethod
    def _get_message_summary(message):
        """Get a summary of a message."""
        pass


class GatewayWebSocketClient(LoggingConfigurable):
    """Proxy web socket connection to a kernel/enterprise gateway."""

    def __init__(self, **kwargs):
        """Initialize the gateway web socket client."""
        super().__init__()
        self.kernel_id = None
        self.ws = None
        self.ws_future: Future[Any] = Future()
        self.disconnected = False
        self.retry = 0

    async def _connect(self, kernel_id, message_callback):
        """Connect to the socket."""
        pass

    def _connection_done(self, fut):
        """Handle a finished connection."""
        pass

    def _disconnect(self):
        """Handle a disconnect."""
        pass

    async def _read_messages(self, callback):
        """Read messages from gateway server."""
        pass

    def on_open(self, kernel_id, message_callback, **kwargs):
        """Web socket connection open against gateway server."""
        pass

    def on_message(self, message):
        """Send message to gateway server."""
        pass

    def _write_message(self, message):
        """Send message to gateway server."""
        pass

    def on_close(self):
        """Web socket closed event."""
        pass


class GatewayResourceHandler(APIHandler):
    """Retrieves resources for specific kernelspec definitions from kernel/enterprise gateway."""

    @web.authenticated
    async def get(self, kernel_name, path, include_body=True):
        """Get a gateway resource by name and path."""
        pass


from ..services.kernels.handlers import _kernel_id_regex
from ..services.kernelspecs.handlers import kernel_name_regex

default_handlers = [
    (r"/api/kernels/%s/channels" % _kernel_id_regex, WebSocketChannelsHandler),
    (r"/kernelspecs/%s/(?P<path>.*)" % kernel_name_regex, GatewayResourceHandler),
]
