"""An implementation of a kernel connection."""

from __future__ import annotations

import asyncio
import json
import time
import typing as t
import weakref
from concurrent.futures import Future
from textwrap import dedent

from jupyter_client import protocol_version as client_protocol_version  # type:ignore[attr-defined]
from tornado import web
from tornado.ioloop import IOLoop
from tornado.websocket import WebSocketClosedError
from traitlets import Any, Bool, Dict, Float, Instance, Int, List, Unicode, default

try:
    from jupyter_client.jsonutil import json_default
except ImportError:
    from jupyter_client.jsonutil import date_default as json_default

from jupyter_core.utils import ensure_async

from jupyter_server.transutils import _i18n

from ..websocket import KernelWebsocketHandler
from .abc import KernelWebsocketConnectionABC
from .base import (
    BaseKernelWebsocketConnection,
    deserialize_binary_message,
    deserialize_msg_from_ws_v1,
    serialize_binary_message,
    serialize_msg_to_ws_v1,
)


def _ensure_future(f):
    """Wrap a concurrent future as an asyncio future if there is a running loop."""
    pass


class ZMQChannelsWebsocketConnection(BaseKernelWebsocketConnection):
    """A Jupyter Server Websocket Connection"""

    limit_rate = Bool(
        True,
        config=True,
        help=_i18n(
            "Whether to limit the rate of IOPub messages (default: True). "
            "If True, use iopub_msg_rate_limit, iopub_data_rate_limit and/or rate_limit_window "
            "to tune the rate."
        ),
    )

    iopub_msg_rate_limit = Float(
        1000,
        config=True,
        help=_i18n(
            """(msgs/sec)
        Maximum rate at which messages can be sent on iopub before they are
        limited."""
        ),
    )

    iopub_data_rate_limit = Float(
        1000000,
        config=True,
        help=_i18n(
            """(bytes/sec)
        Maximum rate at which stream output can be sent on iopub before they are
        limited."""
        ),
    )

    rate_limit_window = Float(
        3,
        config=True,
        help=_i18n(
            """(sec) Time window used to
        check the message and data rate limits."""
        ),
    )

    websocket_handler = Instance(KernelWebsocketHandler)

    @property
    def write_message(self):
        """Alias to the websocket handler's write_message method."""
        return self.websocket_handler.write_message

    # class-level registry of open sessions
    # allows checking for conflict on session-id,
    # which is used as a zmq identity and must be unique.
    _open_sessions: dict[str, KernelWebsocketHandler] = {}
    _open_sockets: t.MutableSet[ZMQChannelsWebsocketConnection] = weakref.WeakSet()

    _kernel_info_future: Future[t.Any]
    _close_future: Future[t.Any]

    channels = Dict({})
    kernel_info_channel = Any(allow_none=True)

    _kernel_info_future = Instance(klass=Future)  # type:ignore[assignment]

    @default("_kernel_info_future")
    def _default_kernel_info_future(self):
        """The default kernel info future."""
        pass

    _close_future = Instance(klass=Future)  # type:ignore[assignment]

    @default("_close_future")
    def _default_close_future(self):
        """The default close future."""
        pass

    session_key = Unicode("")

    _iopub_window_msg_count = Int()
    _iopub_window_byte_count = Int()
    _iopub_msgs_exceeded = Bool(False)
    _iopub_data_exceeded = Bool(False)
    # Queue of (time stamp, byte count)
    # Allows you to specify that the byte count should be lowered
    # by a delta amount at some point in the future.
    _iopub_window_byte_queue: List[t.Any] = List([])

    @classmethod
    async def close_all(cls):
        """Tornado does not provide a way to close open sockets, so add one."""
        pass

    @property
    def subprotocol(self):
        """The sub protocol."""
        pass

    def create_stream(self):
        """Create a stream."""
        pass

    def nudge(self):
        """Nudge the zmq connections with kernel_info_requests
        Returns a Future that will resolve when we have received
        a shell or control reply and at least one iopub message,
        ensuring that zmq subscriptions are established,
        sockets are fully connected, and kernel is responsive.
        Keeps retrying kernel_info_request until these are both received.
        """
        pass

    def _reserialize_reply(self, msg_or_list, channel=None):
        """Reserialize a reply message using JSON.

        msg_or_list can be an already-deserialized msg dict or the zmq buffer list.
        If it is the zmq list, it will be deserialized with self.session.

        This takes the msg list from the ZMQ socket and serializes the result for the websocket.
        This method should be used by self._on_zmq_reply to build messages that can
        be sent back to the browser.

        """
        pass

    def _on_zmq_reply(self, stream, msg_list):
        """Handle a zmq reply."""
        pass

    def request_kernel_info(self):
        """send a request for kernel_info"""
        pass

    def _handle_kernel_info_reply(self, msg):
        """process the kernel_info_reply

        enabling msg spec adaptation, if necessary
        """
        pass

    def _finish_kernel_info(self, info):
        """Finish handling kernel_info reply

        Set up protocol adaptation, if needed,
        and signal that connection can continue.
        """
        pass

    def write_stderr(self, error_message, parent_header):
        """Write a message to stderr."""
        pass

    def _limit_rate(self, channel, msg, msg_list):
        """Limit the message rate on a channel."""
        pass

    def _send_status_message(self, status):
        """Send a status message."""
        pass

    def on_kernel_restarted(self):
        """Handle a kernel restart."""
        pass

    def on_restart_failed(self):
        """Handle a kernel restart failure."""
        pass

    def _on_error(self, channel, msg, msg_list):
        """Handle an error message."""
        pass


KernelWebsocketConnectionABC.register(ZMQChannelsWebsocketConnection)
