"""A MultiKernelManager for use in the Jupyter server

- raises HTTPErrors
- creates REST API models
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import os
import pathlib  # noqa: TC003
import sys
import time
import typing as t
import warnings
from collections import defaultdict
from datetime import datetime, timedelta
from functools import partial, wraps

from jupyter_client.ioloop.manager import AsyncIOLoopKernelManager
from jupyter_client.multikernelmanager import AsyncMultiKernelManager, MultiKernelManager
from jupyter_client.session import Session
from jupyter_core.paths import exists
from jupyter_core.utils import ensure_async
from jupyter_events import EventLogger
from jupyter_events.schema_registry import SchemaRegistryException

if sys.version_info >= (3, 12):
    from typing import override
else:
    from overrides import overrides as override
from tornado import web
from tornado.concurrent import Future
from tornado.ioloop import IOLoop, PeriodicCallback
from traitlets import (
    Any,
    Bool,
    Dict,
    Float,
    Instance,
    Integer,
    List,
    TraitError,
    Unicode,
    default,
    validate,
)

from jupyter_server import DEFAULT_EVENTS_SCHEMA_PATH
from jupyter_server._tz import isoformat, utcnow
from jupyter_server.prometheus.metrics import KERNEL_CURRENTLY_RUNNING_TOTAL
from jupyter_server.utils import ApiPath, import_item, to_os_path


class MappingKernelManager(MultiKernelManager):
    """A KernelManager that handles
    - File mapping
    - HTTP error handling
    - Kernel message filtering
    """

    @default("kernel_manager_class")
    def _default_kernel_manager_class(self):
        pass

    kernel_argv = List(Unicode())

    root_dir = Unicode(config=True)

    _kernel_connections = Dict()

    _kernel_ports: dict[str, list[int]] = Dict()  # type: ignore[assignment]

    _culler_callback = None

    _initialized_culler = False

    @default("root_dir")
    def _default_root_dir(self):
        pass

    @validate("root_dir")
    def _update_root_dir(self, proposal):
        """Do a bit of validation of the root dir."""
        pass

    cull_idle_timeout = Integer(
        0,
        config=True,
        help="""Timeout (in seconds) after which a kernel is considered idle and ready to be culled.
        Values of 0 or lower disable culling. Very short timeouts may result in kernels being culled
        for users with poor network connections.""",
    )

    cull_interval_default = 300  # 5 minutes
    cull_interval = Integer(
        cull_interval_default,
        config=True,
        help="""The interval (in seconds) on which to check for idle kernels exceeding the cull timeout value.""",
    )

    cull_connected = Bool(
        False,
        config=True,
        help="""Whether to consider culling kernels which have one or more connections.
        Only effective if cull_idle_timeout > 0.""",
    )

    cull_busy = Bool(
        False,
        config=True,
        help="""Whether to consider culling kernels which are busy.
        Only effective if cull_idle_timeout > 0.""",
    )

    buffer_offline_messages = Bool(
        True,
        config=True,
        help="""Whether messages from kernels whose frontends have disconnected should be buffered in-memory.

        When True (default), messages are buffered and replayed on reconnect,
        avoiding lost messages due to interrupted connectivity.

        Disable if long-running kernels will produce too much output while
        no frontends are connected.
        """,
    )

    kernel_info_timeout = Float(
        60,
        config=True,
        help="""Timeout for giving up on a kernel (in seconds).

        On starting and restarting kernels, we check whether the
        kernel is running and responsive by sending kernel_info_requests.
        This sets the timeout in seconds for how long the kernel can take
        before being presumed dead.
        This affects the MappingKernelManager (which handles kernel restarts)
        and the ZMQChannelsHandler (which handles the startup).
        """,
    )

    _kernel_buffers = Any()

    @default("_kernel_buffers")
    def _default_kernel_buffers(self):
        pass

    last_kernel_activity = Instance(
        datetime,
        help="The last activity on any kernel, including shutting down a kernel",
    )

    def __init__(self, **kwargs):
        """Initialize a kernel manager."""
        self.pinned_superclass = MultiKernelManager
        self._pending_kernel_tasks = {}
        self.pinned_superclass.__init__(self, **kwargs)
        self.last_kernel_activity = utcnow()

    allowed_message_types = List(
        trait=Unicode(),
        config=True,
        help="""White list of allowed kernel message types.
        When the list is empty, all message types are allowed.
        """,
    )

    allow_tracebacks = Bool(
        True, config=True, help=("Whether to send tracebacks to clients on exceptions.")
    )

    traceback_replacement_message = Unicode(
        "An exception occurred at runtime, which is not shown due to security reasons.",
        config=True,
        help=("Message to print when allow_tracebacks is False, and an exception occurs"),
    )

    # -------------------------------------------------------------------------
    # Methods for managing kernels and sessions
    # -------------------------------------------------------------------------

    def _handle_kernel_died(self, kernel_id):
        """notice that a kernel died"""
        pass

    def cwd_for_path(self, path, **kwargs):
        """Turn API path into absolute OS path."""
        os_path = to_os_path(path, self.root_dir)
        # in the case of documents and kernels not being on the same filesystem,
        # walk up to root_dir if the paths don't exist
        while not os.path.isdir(os_path) and os_path != self.root_dir:
            os_path = os.path.dirname(os_path)
        return os_path

    async def _remove_kernel_when_ready(self, kernel_id, kernel_awaitable):
        """Remove a kernel when it is ready."""
        pass

    # TODO: DEC 2022: Revise the type-ignore once the signatures have been changed upstream
    # https://github.com/jupyter/jupyter_client/pull/905
    async def _async_start_kernel(  # type:ignore[override]
        self, *, kernel_id: str | None = None, path: ApiPath | None = None, **kwargs: str
    ) -> str:
        """Start a kernel for a session and return its kernel_id.

        Parameters
        ----------
        kernel_id : uuid (str)
            The uuid to associate the new kernel with. If this
            is not None, this kernel will be persistent whenever it is
            requested.
        path : API path
            The API path (unicode, '/' delimited) for the cwd.
            Will be transformed to an OS path relative to root_dir.
        kernel_name : str
            The name identifying which kernel spec to launch. This is ignored if
            an existing kernel is returned, but it may be checked in the future.
        """
        pass

    # see https://github.com/jupyter-server/jupyter_server/issues/1165
    # this assignment is technically incorrect, but might need a change of API
    # in jupyter_client.
    start_kernel = _async_start_kernel  # type:ignore[assignment]

    async def _finish_kernel_start(self, kernel_id):
        """Handle a kernel that finishes starting."""
        pass

    def ports_changed(self, kernel_id):
        """Used by ZMQChannelsHandler to determine how to coordinate nudge and replays.

        Ports are captured when starting a kernel (via MappingKernelManager).  Ports
        are considered changed (following restarts) if the referenced KernelManager
        is using a set of ports different from those captured at startup.  If changes
        are detected, the captured set is updated and a value of True is returned.

        NOTE: Use is exclusive to ZMQChannelsHandler because this object is a singleton
        instance while ZMQChannelsHandler instances are per WebSocket connection that
        can vary per kernel lifetime.
        """
        changed_ports = self._get_changed_ports(kernel_id)
        if changed_ports:
            # If changed, update captured ports and return True, else return False.
            self.log.debug("Port change detected for kernel: %s", kernel_id)
            self._kernel_ports[kernel_id] = changed_ports
            return True
        return False

    def _get_changed_ports(self, kernel_id):
        """Internal method to test if a kernel's ports have changed and, if so, return their values.

        This method does NOT update the captured ports for the kernel as that can only be done
        by ZMQChannelsHandler, but instead returns the new list of ports if they are different
        than those captured at startup.  This enables the ability to conditionally restart
        activity monitoring immediately following a kernel's restart (if ports have changed).
        """
        # Get current ports and return comparison with ports captured at startup.
        km = self.get_kernel(kernel_id)
        assert isinstance(km.ports, list)
        assert isinstance(self._kernel_ports[kernel_id], list)
        if km.ports != self._kernel_ports[kernel_id]:
            return km.ports
        return None

    def start_buffering(self, kernel_id, session_key, channels):
        """Start buffering messages for a kernel

        Parameters
        ----------
        kernel_id : str
            The id of the kernel to stop buffering.
        session_key : str
            The session_key, if any, that should get the buffer.
            If the session_key matches the current buffered session_key,
            the buffer will be returned.
        channels : dict({'channel': ZMQStream})
            The zmq channels whose messages should be buffered.
        """

        if not self.buffer_offline_messages:
            for stream in channels.values():
                stream.close()
            return

        self.log.info("Starting buffering for %s", session_key)
        self._check_kernel_id(kernel_id)
        # clear previous buffering state
        self.stop_buffering(kernel_id)
        buffer_info = self._kernel_buffers[kernel_id]
        # record the session key because only one session can buffer
        buffer_info["session_key"] = session_key
        # TODO: the buffer should likely be a memory bounded queue, we're starting with a list to keep it simple
        buffer_info["buffer"] = []
        buffer_info["channels"] = channels

        # forward any future messages to the internal buffer
        def buffer_msg(channel, msg_parts):
            pass

        for channel, stream in channels.items():
            stream.on_recv(partial(buffer_msg, channel))

    def get_buffer(self, kernel_id, session_key):
        """Get the buffer for a given kernel

        Parameters
        ----------
        kernel_id : str
            The id of the kernel to stop buffering.
        session_key : str, optional
            The session_key, if any, that should get the buffer.
            If the session_key matches the current buffered session_key,
            the buffer will be returned.
        """
        self.log.debug("Getting buffer for %s", kernel_id)
        if kernel_id not in self._kernel_buffers:
            return None

        buffer_info = self._kernel_buffers[kernel_id]
        if buffer_info["session_key"] == session_key:
            # remove buffer
            self._kernel_buffers.pop(kernel_id)
            # only return buffer_info if it's a match
            return buffer_info
        else:
            self.stop_buffering(kernel_id)

    def stop_buffering(self, kernel_id):
        """Stop buffering kernel messages

        Parameters
        ----------
        kernel_id : str
            The id of the kernel to stop buffering.
        """
        self.log.debug("Clearing buffer for %s", kernel_id)
        self._check_kernel_id(kernel_id)

        if kernel_id not in self._kernel_buffers:
            return
        buffer_info = self._kernel_buffers.pop(kernel_id)
        # close buffering streams
        for stream in buffer_info["channels"].values():
            if not stream.socket.closed:
                stream.on_recv(None)
                stream.close()

        msg_buffer = buffer_info["buffer"]
        if msg_buffer:
            self.log.info(
                "Discarding %s buffered messages for %s",
                len(msg_buffer),
                buffer_info["session_key"],
            )

    async def _async_shutdown_kernel(self, kernel_id, now=False, restart=False):
        """Shutdown a kernel by kernel_id"""
        pass

    shutdown_kernel = _async_shutdown_kernel

    async def _async_restart_kernel(self, kernel_id, now=False):
        """Restart a kernel by kernel_id"""
        pass

    restart_kernel = _async_restart_kernel

    def notify_connect(self, kernel_id):
        """Notice a new connection to a kernel"""
        if kernel_id in self._kernel_connections:
            self._kernel_connections[kernel_id] += 1

    def notify_disconnect(self, kernel_id):
        """Notice a disconnection from a kernel"""
        if kernel_id in self._kernel_connections:
            self._kernel_connections[kernel_id] -= 1

    def kernel_model(self, kernel_id):
        """Return a JSON-safe dict representing a kernel

        For use in representing kernels in the JSON APIs.
        """
        self._check_kernel_id(kernel_id)
        kernel = self._kernels[kernel_id]

        model = {
            "id": kernel_id,
            "name": kernel.kernel_name,
            "last_activity": isoformat(kernel.last_activity),
            "execution_state": kernel.execution_state,
            "connections": self._kernel_connections.get(kernel_id, 0),
        }
        if getattr(kernel, "reason", None):
            model["reason"] = kernel.reason
        return model

    def list_kernels(self):
        """Returns a list of kernel_id's of kernels running."""
        kernels = []
        kernel_ids = self.pinned_superclass.list_kernel_ids(self)
        for kernel_id in kernel_ids:
            try:
                model = self.kernel_model(kernel_id)
                kernels.append(model)
            except (web.HTTPError, KeyError):
                # Probably due to a (now) non-existent kernel, continue building the list
                pass
        return kernels

    # override _check_kernel_id to raise 404 instead of KeyError
    def _check_kernel_id(self, kernel_id):
        """Check a that a kernel_id exists and raise 404 if not."""
        if kernel_id not in self:
            raise web.HTTPError(404, "Kernel does not exist: %s" % kernel_id)

    # monitoring activity:
    untracked_message_types = List(
        trait=Unicode(),
        config=True,
        default_value=[
            "comm_info_request",
            "comm_info_reply",
            "kernel_info_request",
            "kernel_info_reply",
            "shutdown_request",
            "shutdown_reply",
            "interrupt_request",
            "interrupt_reply",
            "debug_request",
            "debug_reply",
            "stream",
            "display_data",
            "update_display_data",
            "execute_input",
            "execute_result",
            "error",
            "status",
            "clear_output",
            "debug_event",
            "input_request",
            "input_reply",
        ],
        help="""List of kernel message types excluded from user activity tracking.

        This should be a superset of the message types sent on any channel other
        than the shell channel.""",
    )

    def track_message_type(self, message_type):
        pass

    def start_watching_activity(self, kernel_id):
        """Start watching IOPub messages on a kernel for activity.

        - update last_activity on every message
        - record execution_state from status messages
        """
        pass

    def stop_watching_activity(self, kernel_id):
        """Stop watching IOPub messages on a kernel for activity."""
        pass

    def initialize_culler(self):
        """Start idle culler if 'cull_idle_timeout' is greater than zero.

        Regardless of that value, set flag that we've been here.
        """
        if (
            not self._initialized_culler
            and self.cull_idle_timeout > 0
            and self._culler_callback is None
        ):
            _ = IOLoop.current()
            if self.cull_interval <= 0:  # handle case where user set invalid value
                self.log.warning(
                    "Invalid value for 'cull_interval' detected (%s) - using default value (%s).",
                    self.cull_interval,
                    self.cull_interval_default,
                )
                self.cull_interval = self.cull_interval_default
            self._culler_callback = PeriodicCallback(self.cull_kernels, 1000 * self.cull_interval)
            self.log.info(
                "Culling kernels with idle durations > %s seconds at %s second intervals ...",
                self.cull_idle_timeout,
                self.cull_interval,
            )
            if self.cull_busy:
                self.log.info("Culling kernels even if busy")
            if self.cull_connected:
                self.log.info("Culling kernels even with connected clients")
            self._culler_callback.start()

        self._initialized_culler = True

    async def cull_kernels(self):
        """Handle culling kernels."""
        pass

    async def cull_kernel_if_idle(self, kernel_id):
        """Cull a kernel if it is idle."""
        pass


# AsyncMappingKernelManager inherits as much as possible from MappingKernelManager,
# overriding only what is different.
class AsyncMappingKernelManager(MappingKernelManager, AsyncMultiKernelManager):
    """An asynchronous mapping kernel manager."""

    @default("kernel_manager_class")
    def _default_kernel_manager_class(self):
        pass

    @validate("kernel_manager_class")
    def _validate_kernel_manager_class(self, proposal):
        """A validator for the kernel manager class."""
        pass

    def __init__(self, **kwargs):
        """Initialize an async mapping kernel manager."""
        self.pinned_superclass = MultiKernelManager
        self._pending_kernel_tasks = {}
        self.pinned_superclass.__init__(self, **kwargs)
        self.last_kernel_activity = utcnow()


def emit_kernel_action_event(success_msg: str = "") -> t.Callable[..., t.Any]:
    """Decorate kernel action methods to
    begin emitting jupyter kernel action events.

    Parameters
    ----------
    success_msg: str
        A formattable string that's passed to the message field of
        the emitted event when the action succeeds. You can include
        the kernel_id, kernel_name, or action in the message using
        a formatted string argument,
        e.g. "{kernel_id} succeeded to {action}."

    error_msg: str
        A formattable string that's passed to the message field of
        the emitted event when the action fails. You can include
        the kernel_id, kernel_name, or action in the message using
        a formatted string argument,
        e.g. "{kernel_id} failed to {action}."
    """

    def wrap_method(method):
        @wraps(method)
        pass

    return wrap_method


class ServerKernelManager(AsyncIOLoopKernelManager):
    """A server-specific kernel manager."""

    # Define activity-related attributes:
    execution_state = Unicode(
        None, allow_none=True, help="The current execution state of the kernel"
    )
    reason = Unicode("", help="The reason for the last failure against the kernel")

    last_activity = Instance(datetime, help="The last activity on the kernel")

    # A list of pathlib objects, each pointing at an event
    # schema to register with this kernel manager's eventlogger.
    # This trait should not be overridden.
    @property
    def core_event_schema_paths(self) -> list[pathlib.Path]:
        pass

    # This trait is intended for subclasses to override and define
    # custom event schemas.
    extra_event_schema_paths: List[str] = List(
        default_value=[],
        help="""
        A list of pathlib.Path objects pointing at to register with
        the kernel manager's eventlogger.
        """,
    ).tag(config=True)

    event_logger = Instance(EventLogger)

    @default("event_logger")
    def _default_event_logger(self):
        """Initialize the logger and ensure all required events are present."""
        pass

    def emit(self, schema_id, data):
        """Emit an event from the kernel manager."""
        self.event_logger.emit(schema_id=schema_id, data=data)

    @override
    @emit_kernel_action_event(
        success_msg="Kernel {kernel_id} was started.",
    )
    async def start_kernel(self, *args, **kwargs):
        return await super().start_kernel(*args, **kwargs)

    @override
    @emit_kernel_action_event(
        success_msg="Kernel {kernel_id} was shutdown.",
    )
    async def shutdown_kernel(self, *args, **kwargs):
        return await super().shutdown_kernel(*args, **kwargs)

    @override
    @emit_kernel_action_event(
        success_msg="Kernel {kernel_id} was restarted.",
    )
    async def restart_kernel(self, *args, **kwargs):
        pass

    @override
    @emit_kernel_action_event(
        success_msg="Kernel {kernel_id} was interrupted.",
    )
    async def interrupt_kernel(self, *args, **kwargs):
        pass
