"""Kernel gateway managers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import datetime
import json
import os
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from typing import TYPE_CHECKING, Any, Optional, cast

import websocket
from jupyter_client.asynchronous.client import AsyncKernelClient
from jupyter_client.clientabc import KernelClientABC
from jupyter_client.kernelspec import KernelSpecManager
from jupyter_client.managerabc import KernelManagerABC
from jupyter_core.utils import ensure_async
from tornado import web
from tornado.escape import json_decode, json_encode, url_escape, utf8
from traitlets import DottedObjectName, Instance, Type, default

from .._tz import UTC, utcnow
from ..services.kernels.kernelmanager import (
    AsyncMappingKernelManager,
    ServerKernelManager,
    emit_kernel_action_event,
)
from ..services.sessions.sessionmanager import SessionManager
from ..utils import url_path_join
from .gateway_client import GatewayClient, gateway_request

if TYPE_CHECKING:
    from logging import Logger


class GatewayMappingKernelManager(AsyncMappingKernelManager):
    """Kernel manager that supports remote kernels hosted by Jupyter Kernel or Enterprise Gateway."""

    # We'll maintain our own set of kernel ids
    _kernels: dict[str, GatewayKernelManager] = {}

    @default("kernel_manager_class")
    def _default_kernel_manager_class(self):
        pass

    @default("shared_context")
    def _default_shared_context(self):
        pass

    def __init__(self, **kwargs):
        """Initialize a gateway mapping kernel manager."""
        super().__init__(**kwargs)
        self.kernels_url = url_path_join(
            GatewayClient.instance().url or "", GatewayClient.instance().kernels_endpoint or ""
        )

    def remove_kernel(self, kernel_id):
        """Complete override since we want to be more tolerant of missing keys"""
        pass

    async def start_kernel(self, *, kernel_id=None, path=None, **kwargs):
        """Start a kernel for a session and return its kernel_id.

        Parameters
        ----------
        kernel_id : uuid
            The uuid to associate the new kernel with. If this
            is not None, this kernel will be persistent whenever it is
            requested.
        path : API path
            The API path (unicode, '/' delimited) for the cwd.
            Will be transformed to an OS path relative to root_dir.
        """
        pass

    async def kernel_model(self, kernel_id):
        """Return a dictionary of kernel information described in the
        JSON standard model.

        Parameters
        ----------
        kernel_id : uuid
            The uuid of the kernel.
        """
        pass

    async def list_kernels(self, **kwargs):
        """Get a list of running kernels from the Gateway server.

        We'll use this opportunity to refresh the models in each of
        the kernels we're managing.
        """
        pass

    async def shutdown_kernel(self, kernel_id, now=False, restart=False):
        """Shutdown a kernel by its kernel uuid.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel to shutdown.
        now : bool
            Shutdown the kernel immediately (True) or gracefully (False)
        restart : bool
            The purpose of this shutdown is to restart the kernel (True)
        """
        pass

    async def restart_kernel(self, kernel_id, now=False, **kwargs):
        """Restart a kernel by its kernel uuid.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel to restart.
        """
        pass

    async def interrupt_kernel(self, kernel_id, **kwargs):
        """Interrupt a kernel by its kernel uuid.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel to interrupt.
        """
        pass

    async def shutdown_all(self, now=False):
        """Shutdown all kernels."""
        pass

    async def cull_kernels(self):
        """Override cull_kernels, so we can be sure their state is current."""
        pass


class GatewayKernelSpecManager(KernelSpecManager):
    """A gateway kernel spec manager."""

    def __init__(self, **kwargs):
        """Initialize a gateway kernel spec manager."""
        super().__init__(**kwargs)
        base_endpoint = url_path_join(
            GatewayClient.instance().url or "", GatewayClient.instance().kernelspecs_endpoint
        )

        self.base_endpoint = GatewayKernelSpecManager._get_endpoint_for_user_filter(base_endpoint)
        self.base_resource_endpoint = url_path_join(
            GatewayClient.instance().url or "",
            GatewayClient.instance().kernelspecs_resource_endpoint,
        )

    @staticmethod
    def _get_endpoint_for_user_filter(default_endpoint):
        """Get the endpoint for a user filter."""
        pass

    def _replace_path_kernelspec_resources(self, kernel_specs):
        """Helper method that replaces any gateway base_url with the server's base_url
        This enables clients to properly route through jupyter_server to a gateway
        for kernel resources such as logo files
        """
        pass

    def _get_kernelspecs_endpoint_url(self, kernel_name=None):
        """Builds a url for the kernels endpoint
        Parameters
        ----------
        kernel_name : kernel name (optional)
        """
        pass

    async def get_all_specs(self):
        """Get all of the kernel specs for the gateway."""
        pass

    async def list_kernel_specs(self):
        """Get a list of kernel specs."""
        pass

    async def get_kernel_spec(self, kernel_name, **kwargs):
        """Get kernel spec for kernel_name.

        Parameters
        ----------
        kernel_name : str
            The name of the kernel.
        """
        pass

    async def get_kernel_spec_resource(self, kernel_name, path):
        """Get kernel spec for kernel_name.

        Parameters
        ----------
        kernel_name : str
            The name of the kernel.
        path : str
            The name of the desired resource
        """
        pass


class GatewaySessionManager(SessionManager):
    """A gateway session manager."""

    kernel_manager = Instance("jupyter_server.gateway.managers.GatewayMappingKernelManager")

    async def kernel_culled(self, kernel_id: str) -> bool:  # typing: ignore
        """Checks if the kernel is still considered alive and returns true if it's not found."""
        pass


class GatewayKernelManager(ServerKernelManager):
    """Manages a single kernel remotely via a Gateway Server."""

    kernel_id: Optional[str] = None
    kernel = None

    @default("cache_ports")
    def _default_cache_ports(self):
        pass

    def __init__(self, **kwargs):
        """Initialize the gateway kernel manager."""
        super().__init__(**kwargs)
        self.kernels_url = url_path_join(
            GatewayClient.instance().url or "", GatewayClient.instance().kernels_endpoint
        )
        self.kernel_url: str
        self.kernel = self.kernel_id = None
        # simulate busy/activity markers:
        self.execution_state = "starting"
        self.last_activity = utcnow()

    @property
    def has_kernel(self):
        """Has a kernel been started that we are managing."""
        pass

    client_class = DottedObjectName("jupyter_server.gateway.managers.GatewayKernelClient")
    client_factory = Type(klass="jupyter_server.gateway.managers.GatewayKernelClient")

    # --------------------------------------------------------------------------
    # create a Client connected to our Kernel
    # --------------------------------------------------------------------------

    def client(self, **kwargs):
        """Create a client configured to connect to our kernel"""
        pass

    async def refresh_model(self, model=None):
        """Refresh the kernel model.

        Parameters
        ----------
        model : dict
            The model from which to refresh the kernel.  If None, the kernel
            model is fetched from the Gateway server.
        """
        pass

    # --------------------------------------------------------------------------
    # Kernel management
    # --------------------------------------------------------------------------

    @emit_kernel_action_event(
        success_msg="Kernel {kernel_id} was started.",
    )
    async def start_kernel(self, **kwargs):
        """Starts a kernel via HTTP in an asynchronous manner.

        Parameters
        ----------
        `**kwargs` : optional
             keyword arguments that are passed down to build the kernel_cmd
             and launching the kernel (e.g. Popen kwargs).
        """
        pass

    @emit_kernel_action_event(
        success_msg="Kernel {kernel_id} was shutdown.",
    )
    async def shutdown_kernel(self, now=False, restart=False):
        """Attempts to stop the kernel process cleanly via HTTP."""
        pass

    @emit_kernel_action_event(
        success_msg="Kernel {kernel_id} was restarted.",
    )
    async def restart_kernel(self, **kw):
        """Restarts a kernel via HTTP."""
        pass

    @emit_kernel_action_event(
        success_msg="Kernel {kernel_id} was interrupted.",
    )
    async def interrupt_kernel(self):
        """Interrupts the kernel via an HTTP request."""
        pass

    async def is_alive(self):
        """Is the kernel process still running?"""
        pass

    def cleanup_resources(self, restart=False):
        """Clean up resources when the kernel is shut down"""


KernelManagerABC.register(GatewayKernelManager)


class ChannelQueue(Queue):  # type:ignore[type-arg]
    """A queue for a named channel."""

    channel_name: Optional[str] = None
    response_router_finished: bool

    def __init__(self, channel_name: str, channel_socket: websocket.WebSocket, log: Logger):
        """Initialize a channel queue."""
        super().__init__()
        self.channel_name = channel_name
        self.channel_socket = channel_socket
        self.log = log
        self.response_router_finished = False

    async def _async_get(self, timeout=None):
        """Asynchronously get from the queue."""
        pass

    async def get_msg(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Get a message from the queue."""
        pass

    def send(self, msg: dict[str, Any]) -> None:
        """Send a message to the queue."""
        pass

    @staticmethod
    def serialize_datetime(dt):
        """Serialize a datetime object."""
        pass

    def start(self) -> None:
        """Start the queue."""

    def stop(self) -> None:
        """Stop the queue."""
        pass

    def is_alive(self) -> bool:
        """Whether the queue is alive."""
        pass


class HBChannelQueue(ChannelQueue):
    """A queue for the heartbeat channel."""

    def is_beating(self) -> bool:
        """Whether the channel is beating."""
        pass


class GatewayKernelClient(AsyncKernelClient):
    """Communicates with a single kernel indirectly via a websocket to a gateway server.

    There are five channels associated with each kernel:

    * shell: for request/reply calls to the kernel.
    * iopub: for the kernel to publish results to frontends.
    * hb: for monitoring the kernel's heartbeat.
    * stdin: for frontends to reply to raw_input calls in the kernel.
    * control: for kernel management calls to the kernel.

    The messages that can be sent on these channels are exposed as methods of the
    client (KernelClient.execute, complete, history, etc.). These methods only
    send the message, they don't wait for a reply. To get results, use e.g.
    :meth:`get_shell_msg` to fetch messages from the shell channel.
    """

    # flag for whether execute requests should be allowed to call raw_input:
    allow_stdin = False
    _channels_stopped: bool
    _channel_queues: Optional[dict[str, ChannelQueue]]
    _control_channel: Optional[ChannelQueue]
    _hb_channel: Optional[ChannelQueue]
    _stdin_channel: Optional[ChannelQueue]
    _iopub_channel: Optional[ChannelQueue]
    _shell_channel: Optional[ChannelQueue]

    def __init__(self, kernel_id, **kwargs):
        """Initialize a gateway kernel client."""
        super().__init__(**kwargs)
        self.kernel_id = kernel_id
        self.channel_socket: Optional[websocket.WebSocket] = None
        self.response_router: Optional[Thread] = None
        self._channels_stopped = False
        self._channel_queues = {}

    # --------------------------------------------------------------------------
    # Channel management methods
    # --------------------------------------------------------------------------

    async def start_channels(self, shell=True, iopub=True, stdin=True, hb=True, control=True):
        """Starts the channels for this kernel.

        For this class, we establish a websocket connection to the destination
        and set up the channel-based queues on which applicable messages will
        be posted.
        """
        pass

    def stop_channels(self):
        """Stops all the running channels for this kernel.

        For this class, we close the websocket connection and destroy the
        channel-based queues.
        """
        pass

    # Channels are implemented via a ChannelQueue that is used to send and receive messages

    @property
    def shell_channel(self):
        """Get the shell channel object for this kernel."""
        pass

    @property
    def iopub_channel(self):
        """Get the iopub channel object for this kernel."""
        pass

    @property
    def stdin_channel(self):
        """Get the stdin channel object for this kernel."""
        pass

    @property
    def hb_channel(self):
        """Get the hb channel object for this kernel."""
        pass

    @property
    def control_channel(self):
        """Get the control channel object for this kernel."""
        pass

    def _route_responses(self):
        """
        Reads responses from the websocket and routes each to the appropriate channel queue based
        on the message's channel.  It does this for the duration of the class's lifetime until the
        channels are stopped, at which time the socket is closed (unblocking the router) and
        the thread terminates.  If shutdown happens to occur while processing a response (unlikely),
        termination takes place via the loop control boolean.
        """
        pass


KernelClientABC.register(GatewayKernelClient)
