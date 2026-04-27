"""Notebook related utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import errno
import importlib.util
import os
import socket
import sys
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, NewType
from urllib.parse import (
    SplitResult,
    quote,
    unquote,
    urlparse,
    urlsplit,
    urlunsplit,
)
from urllib.parse import (
    urljoin as _urljoin,
)
from urllib.request import pathname2url as _pathname2url

from jupyter_core.utils import ensure_async as _ensure_async
from packaging.version import Version
from tornado.httpclient import AsyncHTTPClient, HTTPClient, HTTPRequest, HTTPResponse
from tornado.netutil import Resolver

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

ApiPath = NewType("ApiPath", str)

# Re-export
urljoin = _urljoin
pathname2url = _pathname2url
ensure_async = _ensure_async


def url_path_join(*pieces: str) -> str:
    """Join components of url into a relative url

    Use to prevent double slash when joining subpath. This will leave the
    initial and final / in place
    """
    pass


def url_is_absolute(url: str) -> bool:
    """Determine whether a given URL is absolute"""
    pass


def path2url(path: str) -> str:
    """Convert a local file path to a URL"""
    pass


def url2path(url: str) -> str:
    """Convert a URL to a local file path"""
    pass


def url_escape(path: str) -> str:
    """Escape special characters in a URL path

    Turns '/foo bar/' into '/foo%20bar/'
    """
    pass


def url_unescape(path: str) -> str:
    """Unescape special characters in a URL path

    Turns '/foo%20bar/' into '/foo bar/'
    """
    pass


def samefile_simple(path: str, other_path: str) -> bool:
    """
    Fill in for os.path.samefile when it is unavailable (Windows+py2).

    Do a case-insensitive string comparison in this case
    plus comparing the full stat result (including times)
    because Windows + py2 doesn't support the stat fields
    needed for identifying if it's the same file (st_ino, st_dev).

    Only to be used if os.path.samefile is not available.

    Parameters
    ----------
    path : str
        representing a path to a file
    other_path : str
        representing a path to another file

    Returns
    -------
    same:   Boolean that is True if both path and other path are the same
    """
    pass


def to_os_path(path: ApiPath, root: str = "") -> str:
    """Convert an API path to a filesystem path

    If given, root will be prepended to the path.
    root must be a filesystem path already.
    """
    pass


def to_api_path(os_path: str, root: str = "") -> ApiPath:
    """Convert a filesystem path to an API path

    If given, root will be removed from the path.
    root must be a filesystem path already.
    """
    pass


def check_version(v: str, check: str) -> bool:
    """check version string v >= check

    If dev/prerelease tags result in TypeError for string-number comparison,
    it is assumed that the dependency is satisfied.
    Users on dev branches are responsible for keeping their own packages up to date.
    """
    pass


# Copy of IPython.utils.process.check_pid:


def _check_pid_win32(pid: int) -> bool:
    pass


def _check_pid_posix(pid: int) -> bool:
    """Copy of IPython.utils.process.check_pid"""
    pass


if sys.platform == "win32":
    check_pid = _check_pid_win32
else:
    check_pid = _check_pid_posix


async def run_sync_in_loop(maybe_async):
    """**DEPRECATED**: Use ``ensure_async`` from jupyter_core instead."""
    pass


def urlencode_unix_socket_path(socket_path: str) -> str:
    """Encodes a UNIX socket path string from a socket path for the `http+unix` URI form."""
    pass


def urldecode_unix_socket_path(socket_path: str) -> str:
    """Decodes a UNIX sock path string from an encoded sock path for the `http+unix` URI form."""
    pass


def urlencode_unix_socket(socket_path: str) -> str:
    """Encodes a UNIX socket URL from a socket path for the `http+unix` URI form."""
    pass


def unix_socket_in_use(socket_path: str) -> bool:
    """Checks whether a UNIX socket path on disk is in use by attempting to connect to it."""
    pass


@contextmanager
def _request_for_tornado_client(
    urlstring: str, method: str = "GET", body: Any = None, headers: Any = None
) -> Generator[HTTPRequest, None, None]:
    """A utility that provides a context that handles
    HTTP, HTTPS, and HTTP+UNIX request.
    Creates a tornado HTTPRequest object with a URL
    that tornado's HTTPClients can accept.
    If the request is made to a unix socket, temporarily
    configure the AsyncHTTPClient to resolve the URL
    and connect to the proper socket.
    """
    pass


def fetch(
    urlstring: str, method: str = "GET", body: Any = None, headers: Any = None
) -> HTTPResponse:
    """
    Send a HTTP, HTTPS, or HTTP+UNIX request
    to a Tornado Web Server. Returns a tornado HTTPResponse.
    """
    pass


async def async_fetch(
    urlstring: str, method: str = "GET", body: Any = None, headers: Any = None, io_loop: Any = None
) -> HTTPResponse:
    """
    Send an asynchronous HTTP, HTTPS, or HTTP+UNIX request
    to a Tornado Web Server. Returns a tornado HTTPResponse.
    """
    pass


def is_namespace_package(namespace: str) -> bool | None:
    """Is the provided namespace a Python Namespace Package (PEP420).

    https://www.python.org/dev/peps/pep-0420/#specification

    Returns `None` if module is not importable.

    """
    pass


def filefind(filename: str, path_dirs: Sequence[str]) -> str:
    """Find a file by looking through a sequence of paths.

    For use in FileFindHandler.

    Iterates through a sequence of paths looking for a file and returns
    the full, absolute path of the first occurrence of the file.

    Absolute paths are not accepted for inputs.

    This function does not automatically try any paths,
    such as the cwd or the user's home directory.

    Parameters
    ----------
    filename : str
        The filename to look for. Must be a relative path.
    path_dirs : sequence of str
        The sequence of paths to look in for the file.
        Walk through each element and join with ``filename``.
        Only after ensuring the path resolves within the directory is it checked for existence.

    Returns
    -------
    Raises :exc:`OSError` or returns absolute path to file.
    """
    pass


def import_item(name: str) -> Any:
    """Import and return ``bar`` given the string ``foo.bar``.
    Calling ``bar = import_item("foo.bar")`` is the functional equivalent of
    executing the code ``from foo import bar``.
    Parameters
    ----------
    name : str
      The fully qualified name of the module/package being imported.
    Returns
    -------
    mod : module object
       The module that was imported.
    """
    pass


class JupyterServerAuthWarning(RuntimeWarning):
    """Emitted when authentication configuration issue is detected.

    Intended for filtering out expected warnings in tests, including
    downstream tests, rather than for users to silence this warning.
    """
