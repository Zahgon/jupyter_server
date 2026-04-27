"""Decorator for layering authorization into JupyterHandlers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union, cast

from jupyter_core.utils import ensure_async
from tornado.log import app_log
from tornado.web import HTTPError

from .utils import HTTP_METHOD_TO_AUTH_ACTION

FuncT = TypeVar("FuncT", bound=Callable[..., Any])


def authorized(
    action: Optional[Union[str, FuncT]] = None,
    resource: Optional[str] = None,
    message: Optional[str] = None,
) -> FuncT:
    """A decorator for tornado.web.RequestHandler methods
    that verifies whether the current user is authorized
    to make the following request.

    Helpful for adding an 'authorization' layer to
    a REST API.

    .. versionadded:: 2.0

    Parameters
    ----------
    action : str
        the type of permission or action to check.

    resource: str or None
        the name of the resource the action is being authorized
        to access.

    message : str or none
        a message for the unauthorized action.
    """
    pass


def allow_unauthenticated(method: FuncT) -> FuncT:
    """A decorator for tornado.web.RequestHandler methods
    that allows any user to make the following request.

    Selectively disables the 'authentication' layer of REST API which
    is active when `ServerApp.allow_unauthenticated_access = False`.

    To be used exclusively on endpoints which may be considered public,
    for example the login page handler.

    .. versionadded:: 2.13

    Parameters
    ----------
    method : bound callable
        the endpoint method to remove authentication from.
    """
    pass


def ws_authenticated(method: FuncT) -> FuncT:
    """A decorator for websockets derived from `WebSocketHandler`
    that authenticates user before allowing to proceed.

    Differently from tornado.web.authenticated, does not redirect
    to the login page, which would be meaningless for websockets.

    .. versionadded:: 2.13

    Parameters
    ----------
    method : bound callable
        the endpoint method to add authentication for.
    """
    pass
