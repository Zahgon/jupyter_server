"""A contents manager that uses the local file system for storage."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import errno
import math
import mimetypes
import os
import platform
import shutil
import stat
import subprocess
import sys
import typing as t
import warnings
from datetime import datetime
from pathlib import Path

import nbformat
from anyio.to_thread import run_sync
from jupyter_core.paths import exists, is_file_hidden, is_hidden
from send2trash import send2trash
from tornado import web
from traitlets import Bool, Int, TraitError, Unicode, default, validate

from jupyter_server import _tz as tz
from jupyter_server.base.handlers import AuthenticatedFileHandler
from jupyter_server.transutils import _i18n
from jupyter_server.utils import to_api_path

from .filecheckpoints import AsyncFileCheckpoints, FileCheckpoints
from .fileio import AsyncFileManagerMixin, FileManagerMixin
from .manager import AsyncContentsManager, ContentsManager, copy_pat

try:
    from os.path import samefile
except ImportError:
    # windows
    from jupyter_server.utils import samefile_simple as samefile  # type:ignore[assignment]

_script_exporter = None


def _get_created_timestamp(info: os.stat_result) -> float:
    """Get best-effort file creation timestamp from stat result.

    Uses st_birthtime (actual creation time) when available (macOS, BSD,
    and Linux with kernel 4.11+ via statx on supported filesystems).
    On Windows, st_ctime is the creation time.
    On Linux/other, falls back to st_ctime (note: this is inode change time,
    not creation time, so operations like chmod may update 'created').

    Falls back to st_ctime if st_birthtime is unavailable, non-numeric,
    negative, or non-finite. Returns st_ctime as final fallback, which
    is validated in _base_model() during datetime conversion.
    """
    pass


class FileContentsManager(FileManagerMixin, ContentsManager):
    """A file contents manager."""

    root_dir = Unicode(config=True)

    max_copy_folder_size_mb = Int(500, config=True, help="The max folder size that can be copied")

    @default("root_dir")
    def _default_root_dir(self):
        pass

    @validate("root_dir")
    def _validate_root_dir(self, proposal):
        pass

    @default("preferred_dir")
    def _default_preferred_dir(self):
        pass

    @validate("preferred_dir")
    def _validate_preferred_dir(self, proposal):
        # It should be safe to pass an API path through this method:
        pass

    @default("checkpoints_class")
    def _checkpoints_class_default(self):
        pass

    delete_to_trash = Bool(
        True,
        config=True,
        help="""If True (default), deleting files will send them to the
        platform's trash/recycle bin, where they can be recovered. If False,
        deleting files really deletes them.""",
    )

    always_delete_dir = Bool(
        False,
        config=True,
        help="""If True, deleting a non-empty directory will always be allowed.
        WARNING this may result in files being permanently removed; e.g. on Windows,
        if the data size is too big for the trash/recycle bin the directory will be permanently
        deleted. If False (default), the non-empty directory will be sent to the trash only
        if safe. And if ``delete_to_trash`` is True, the directory won't be deleted.""",
    )

    @default("files_handler_class")
    def _files_handler_class_default(self):
        pass

    @default("files_handler_params")
    def _files_handler_params_default(self):
        pass

    def is_hidden(self, path):
        """Does the API style path correspond to a hidden directory or file?

        Parameters
        ----------
        path : str
            The path to check. This is an API path (`/` separated,
            relative to root_dir).

        Returns
        -------
        hidden : bool
            Whether the path exists and is hidden.
        """
        pass

    def is_writable(self, path):
        """Does the API style path correspond to a writable directory or file?

        Parameters
        ----------
        path : str
            The path to check. This is an API path (`/` separated,
            relative to root_dir).

        Returns
        -------
        hidden : bool
            Whether the path exists and is writable.
        """
        pass

    def file_exists(self, path: str) -> bool | t.Awaitable[bool]:
        """Returns True if the file exists, else returns False.

        API-style wrapper for os.path.isfile

        Parameters
        ----------
        path : str
            The relative path to the file (with '/' as separator)

        Returns
        -------
        exists : bool
            Whether the file exists.
        """
        pass

    def dir_exists(self, path):
        """Does the API-style path refer to an extant directory?

        API-style wrapper for os.path.isdir

        Parameters
        ----------
        path : str
            The path to check. This is an API path (`/` separated,
            relative to root_dir).

        Returns
        -------
        exists : bool
            Whether the path is indeed a directory.
        """
        pass

    def exists(self, path):
        """Returns True if the path exists, else returns False.

        API-style wrapper for os.path.exists

        Parameters
        ----------
        path : str
            The API path to the file (with '/' as separator)

        Returns
        -------
        exists : bool
            Whether the target exists.
        """
        pass

    def _base_model(self, path):
        """Build the common base of a contents model"""
        pass

    def _dir_model(self, path, content=True):
        """Build a model for a directory

        if content is requested, will include a listing of the directory
        """
        pass

    def _file_model(self, path, content=True, format=None, require_hash=False):
        """Build a model for a file

        if content is requested, include the file contents.

        format:
          If 'text', the contents will be decoded as UTF-8.
          If 'base64', the raw bytes contents will be encoded as base64.
          If not specified, try to decode as UTF-8, and fall back to base64

        if require_hash is true, the model will include 'hash'
        """
        pass

    def _notebook_model(self, path, content=True, require_hash=False):
        """Build a notebook model

        if content is requested, the notebook content will be populated
        as a JSON structure (not double-serialized)

        if require_hash is true, the model will include 'hash'
        """
        pass

    def get(self, path, content=True, type=None, format=None, require_hash=False):
        """Takes a path for an entity and returns its model

        Parameters
        ----------
        path : str
            the API path that describes the relative path for the target
        content : bool
            Whether to include the contents in the reply
        type : str, optional
            The requested type - 'file', 'notebook', or 'directory'.
            Will raise HTTPError 400 if the content doesn't match.
        format : str, optional
            The requested format for file contents. 'text' or 'base64'.
            Ignored if this returns a notebook or directory model.
        require_hash: bool, optional
            Whether to include the hash of the file contents.

        Returns
        -------
        model : dict
            the contents model. If content=True, returns the contents
            of the file or directory as well.
        """
        pass

    def _save_directory(self, os_path, model, path=""):
        """create a directory"""
        pass

    def save(self, model, path=""):
        """Save the file model and return the model with no content."""
        pass

    def delete_file(self, path):
        """Delete file at path."""
        pass

    def rename_file(self, old_path, new_path):
        """Rename a file."""
        pass

    def info_string(self):
        """Get the information string for the manager."""
        pass

    def get_kernel_path(self, path, model=None):
        """Return the initial API path of  a kernel associated with a given notebook"""
        pass

    def copy(self, from_path, to_path=None):
        """
        Copy an existing file or directory and return its new model.
        If to_path not specified, it will be the parent directory of from_path.
        If copying a file and to_path is a directory, filename/directoryname will increment `from_path-Copy#.ext`.
        Considering multi-part extensions, the Copy# part will be placed before the first dot for all the extensions except `ipynb`.
        For easier manual searching in case of notebooks, the Copy# part will be placed before the last dot.
        from_path must be a full path to a file or directory.
        """
        pass

    def _copy_dir(self, from_path, to_path_original, to_name, to_path):
        """
        handles copying directories
        returns the model for the copied directory
        """
        pass

    def check_folder_size(self, path):
        """
        limit the size of folders being copied to be no more than the
        trait max_copy_folder_size_mb to prevent a timeout error
        """
        pass

    def _get_dir_size(self, path="."):
        """
        calls the command line program du to get the directory size
        """
        pass

    def _human_readable_size(self, size):
        """
        returns folder size in a human readable format
        """
        pass


class AsyncFileContentsManager(FileContentsManager, AsyncFileManagerMixin, AsyncContentsManager):
    """An async file contents manager."""

    @default("checkpoints_class")
    def _checkpoints_class_default(self):
        pass

    async def _dir_model(self, path, content=True):
        """Build a model for a directory

        if content is requested, will include a listing of the directory
        """
        pass

    async def _file_model(self, path, content=True, format=None, require_hash=False):
        """Build a model for a file

        if content is requested, include the file contents.

        format:
          If 'text', the contents will be decoded as UTF-8.
          If 'base64', the raw bytes contents will be encoded as base64.
          If not specified, try to decode as UTF-8, and fall back to base64

        if require_hash is true, the model will include 'hash'
        """
        pass

    async def _notebook_model(self, path, content=True, require_hash=False):
        """Build a notebook model

        if content is requested, the notebook content will be populated
        as a JSON structure (not double-serialized)
        """
        pass

    async def get(self, path, content=True, type=None, format=None, require_hash=False):
        """Takes a path for an entity and returns its model

        Parameters
        ----------
        path : str
            the API path that describes the relative path for the target
        content : bool
            Whether to include the contents in the reply
        type : str, optional
            The requested type - 'file', 'notebook', or 'directory'.
            Will raise HTTPError 400 if the content doesn't match.
        format : str, optional
            The requested format for file contents. 'text' or 'base64'.
            Ignored if this returns a notebook or directory model.
        require_hash: bool, optional
            Whether to include the hash of the file contents.

        Returns
        -------
        model : dict
            the contents model. If content=True, returns the contents
            of the file or directory as well.
        """
        pass

    async def _save_directory(self, os_path, model, path=""):
        """create a directory"""
        pass

    async def save(self, model, path=""):
        """Save the file model and return the model with no content."""
        pass

    async def delete_file(self, path):
        """Delete file at path."""
        pass

    async def rename_file(self, old_path, new_path):
        """Rename a file."""
        pass

    async def dir_exists(self, path):
        """Does a directory exist at the given path"""
        pass

    async def file_exists(self, path: str) -> bool:
        """Does a file exist at the given path"""
        pass

    async def is_hidden(self, path):
        """Is path a hidden directory or file"""
        pass

    async def get_kernel_path(self, path, model=None):
        """Return the initial API path of a kernel associated with a given notebook"""
        pass

    async def copy(self, from_path, to_path=None):
        """
        Copy an existing file or directory and return its new model.
        If to_path not specified, it will be the parent directory of from_path.
        If copying a file and to_path is a directory, filename/directoryname will increment `from_path-Copy#.ext`.
        Considering multi-part extensions, the Copy# part will be placed before the first dot for all the extensions except `ipynb`.
        For easier manual searching in case of notebooks, the Copy# part will be placed before the last dot.
        from_path must be a full path to a file or directory.
        """
        pass

    async def _copy_dir(
        self, from_path: str, to_path_original: str, to_name: str, to_path: str
    ) -> dict[str, t.Any]:
        """
        handles copying directories
        returns the model for the copied directory
        """
        pass

    async def check_folder_size(self, path: str) -> None:
        """
        limit the size of folders being copied to be no more than the
        trait max_copy_folder_size_mb to prevent a timeout error
        """
        pass

    async def _get_dir_size(self, path: str = ".") -> str:
        """
        calls the command line program du to get the directory size
        """
        pass

    async def _human_readable_size(self, size: int) -> str:
        """
        returns folder size in a human readable format
        """
        pass
