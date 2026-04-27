"""Base websocket classes."""

import re
import warnings
from typing import Optional, no_type_check
from urllib.parse import urlparse

from tornado import ioloop, web
from tornado.iostream import IOStream

from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.utils import JupyterServerAuthWarning

# ping interval for keeping websockets alive (30 seconds)
WS_PING_INTERVAL = 30000


class WebSocketMixin:
    """Mixin for common websocket options"""

    ping_callback = None
    last_ping = 0.0
    last_pong = 0.0
    stream: Optional[IOStream] = None

    @property
    def ping_interval(self):
        """The interval for websocket keep-alive pings.

        Set ws_ping_interval = 0 to disable pings.
        """
        pass

    @property
    def ping_timeout(self):
        """If no ping is received in this many milliseconds,
        close the websocket connection (VPNs, etc. can fail to cleanly close ws connections).
        Default is max of 3 pings or 30 seconds.
        """
        pass

    @no_type_check
    def check_origin(self, origin: Optional[str] = None) -> bool:
        """Check Origin == Host or Access-Control-Allow-Origin.

        Tornado >= 4 calls this method automatically, raising 403 if it returns False.
        """
        pass

    def clear_cookie(self, *args, **kwargs):
        """meaningless for websockets"""

    @no_type_check
    def _maybe_auth(self):
        """Verify authentication if required.

        Only used when the websocket class does not inherit from JupyterHandler.
        """
        pass

    @no_type_check
    def prepare(self, *args, **kwargs):
        """Handle a get request."""
        pass

    @no_type_check
    def open(self, *args, **kwargs):
        """Open the websocket."""
        pass

    @no_type_check
    def send_ping(self):
        """send a ping to keep the websocket alive"""
        pass

    def on_pong(self, data):
        """Handle a pong message."""
        pass
