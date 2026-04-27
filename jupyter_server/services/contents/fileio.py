"""
Utilities for file-based Contents/Checkpoints managers.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import errno
import hashlib
import os
import shutil
from base64 import decodebytes, encodebytes
from contextlib import contextmanager
from functools import partial

import nbformat
from anyio.to_thread import run_sync
from tornado.web import HTTPError
from traitlets import Bool, Enum
from traitlets.config import Configurable
from traitlets.config.configurable import LoggingConfigurable

from jupyter_server.utils import ApiPath, to_api_path, to_os_path


def replace_file(src, dst):
    """replace dst with src"""
    pass


async def async_replace_file(src, dst):
    """replace dst with src asynchronously"""
    pass


def copy2_safe(src, dst, log=None):
    """copy src to dst

    like shutil.copy2, but log errors in copystat instead of raising
    """
    pass


async def async_copy2_safe(src, dst, log=None):
    """copy src to dst asynchronously

    like shutil.copy2, but log errors in copystat instead of raising
    """
    pass


def path_to_intermediate(path):
    """Name of the intermediate file used in atomic writes.

    The .~ prefix will make Dropbox ignore the temporary file."""
    pass


def path_to_invalid(path):
    """Name of invalid file after a failed atomic write and subsequent read."""
    pass


@contextmanager
def atomic_writing(path, text=True, encoding="utf-8", log=None, **kwargs):
    """Context manager to write to a file only if the entire write is successful.

    This works by copying the previous file contents to a temporary file in the
    same directory, and renaming that file back to the target if the context
    exits with an error. If the context is successful, the new data is synced to
    disk and the temporary file is removed.

    Parameters
    ----------
    path : str
        The target file to write to.
    text : bool, optional
        Whether to open the file in text mode (i.e. to write unicode). Default is
        True.
    encoding : str, optional
        The encoding to use for files opened in text mode. Default is UTF-8.
    **kwargs
        Passed to :func:`io.open`.
    """
    pass


@contextmanager
def _simple_writing(path, text=True, encoding="utf-8", log=None, **kwargs):
    """Context manager to write file without doing atomic writing
    (for weird filesystem eg: nfs).

    Parameters
    ----------
    path : str
        The target file to write to.
    text : bool, optional
        Whether to open the file in text mode (i.e. to write unicode). Default is
        True.
    encoding : str, optional
        The encoding to use for files opened in text mode. Default is UTF-8.
    **kwargs
        Passed to :func:`io.open`.
    """
    pass


class FileManagerMixin(LoggingConfigurable, Configurable):
    """
    Mixin for ContentsAPI classes that interact with the filesystem.

    Provides facilities for reading, writing, and copying files.

    Shared by FileContentsManager and FileCheckpoints.

    Note
    ----
    Classes using this mixin must provide the following attributes:

    root_dir : unicode
        A directory against against which API-style paths are to be resolved.

    log : logging.Logger
    """

    use_atomic_writing = Bool(
        True,
        config=True,
        help="""By default notebooks are saved on disk on a temporary file and then if successfully written, it replaces the old ones.
      This procedure, namely 'atomic_writing', causes some bugs on file system without operation order enforcement (like some networked fs).
      If set to False, the new notebook is written directly on the old one which could fail (eg: full filesystem or quota )""",
    )

    hash_algorithm = Enum(  # type: ignore[call-overload]
        hashlib.algorithms_available,
        default_value="sha256",
        config=True,
        help="Hash algorithm to use for file content, support by hashlib",
    )

    @contextmanager
    def open(self, os_path, *args, **kwargs):
        """wrapper around io.open that turns permission errors into 403"""
        pass

    @contextmanager
    def atomic_writing(self, os_path, *args, **kwargs):
        """wrapper around atomic_writing that turns permission errors to 403.
        Depending on flag 'use_atomic_writing', the wrapper perform an actual atomic writing or
        simply writes the file (whatever an old exists or not)"""
        pass

    @contextmanager
    def perm_to_403(self, os_path=""):
        """context manager for turning permission errors into 403."""
        pass

    def _copy(self, src, dest):
        """copy src to dest

        like shutil.copy2, but log errors in copystat
        """
        pass

    def _get_os_path(self, path):
        """Given an API path, return its file system path.

        Parameters
        ----------
        path : str
            The relative API path to the named file.

        Returns
        -------
        path : str
            Native, absolute OS path to for a file.

        Raises
        ------
        404: if path is outside root
        """
        pass

    def _read_notebook(
        self, os_path, as_version=4, capture_validation_error=None, raw: bool = False
    ):
        """Read a notebook from an os path."""
        pass

    def _save_notebook(self, os_path, nb, capture_validation_error=None):
        """Save a notebook to an os_path."""
        pass

    def _get_hash(self, byte_content: bytes) -> dict[str, str]:
        """Compute the hash hexdigest for the provided bytes.

        The hash algorithm is provided by the `hash_algorithm` attribute.

        Parameters
        ----------
        byte_content : bytes
            The bytes to hash

        Returns
        -------
        A dictionary to be appended to a model {"hash": str, "hash_algorithm": str}.
        """
        pass

    def _read_file(
        self, os_path: str, format: str | None, raw: bool = False
    ) -> tuple[str | bytes, str] | tuple[str | bytes, str, bytes]:
        """Read a non-notebook file.

        Parameters
        ----------
        os_path: str
            The path to be read.
        format: str
            If 'text', the contents will be decoded as UTF-8.
            If 'base64', the raw bytes contents will be encoded as base64.
            If 'byte', the raw bytes contents will be returned.
            If not specified, try to decode as UTF-8, and fall back to base64
        raw: bool
            [Optional] If True, will return as third argument the raw bytes content

        Returns
        -------
        (content, format, byte_content) It returns the content in the given format
        as well as the raw byte content.
        """
        pass

    def _save_file(self, os_path, content, format):
        """Save content of a generic file."""
        pass


class AsyncFileManagerMixin(FileManagerMixin):
    """
    Mixin for ContentsAPI classes that interact with the filesystem asynchronously.
    """

    async def _copy(self, src, dest):
        """copy src to dest

        like shutil.copy2, but log errors in copystat
        """
        pass

    async def _read_notebook(
        self, os_path, as_version=4, capture_validation_error=None, raw: bool = False
    ):
        """Read a notebook from an os path."""
        pass

    async def _save_notebook(self, os_path, nb, capture_validation_error=None):
        """Save a notebook to an os_path."""
        pass

    async def _read_file(  # type: ignore[override]
        self, os_path: str, format: str | None, raw: bool = False
    ) -> tuple[str | bytes, str] | tuple[str | bytes, str, bytes]:
        """Read a non-notebook file.

        Parameters
        ----------
        os_path: str
            The path to be read.
        format: str
            If 'text', the contents will be decoded as UTF-8.
            If 'base64', the raw bytes contents will be encoded as base64.
            If 'byte', the raw bytes contents will be returned.
            If not specified, try to decode as UTF-8, and fall back to base64
        raw: bool
            [Optional] If True, will return as third argument the raw bytes content

        Returns
        -------
        (content, format, byte_content) It returns the content in the given format
        as well as the raw byte content.
        """
        pass

    async def _save_file(self, os_path, content, format):
        """Save content of a generic file."""
        pass
