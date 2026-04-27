"""
File-based Checkpoints implementations.
"""

import os
import shutil
import tempfile

from anyio.to_thread import run_sync
from jupyter_core.utils import ensure_dir_exists
from tornado.web import HTTPError
from traitlets import Unicode

from jupyter_server import _tz as tz

from .checkpoints import (
    AsyncCheckpoints,
    AsyncGenericCheckpointsMixin,
    Checkpoints,
    GenericCheckpointsMixin,
)
from .fileio import AsyncFileManagerMixin, FileManagerMixin


class FileCheckpoints(FileManagerMixin, Checkpoints):
    """
    A Checkpoints that caches checkpoints for files in adjacent
    directories.

    Only works with FileContentsManager.  Use GenericFileCheckpoints if
    you want file-based checkpoints with another ContentsManager.
    """

    checkpoint_dir = Unicode(
        ".ipynb_checkpoints",
        config=True,
        help="""The directory name in which to keep file checkpoints

        This is a path relative to the file's own directory.

        By default, it is .ipynb_checkpoints
        """,
    )

    root_dir = Unicode(config=True)

    def _root_dir_default(self):
        pass

    # ContentsManager-dependent checkpoint API
    def create_checkpoint(self, contents_mgr, path):
        """Create a checkpoint."""
        pass

    def restore_checkpoint(self, contents_mgr, checkpoint_id, path):
        """Restore a checkpoint."""
        pass

    # ContentsManager-independent checkpoint API
    def rename_checkpoint(self, checkpoint_id, old_path, new_path):
        """Rename a checkpoint from old_path to new_path."""
        pass

    def delete_checkpoint(self, checkpoint_id, path):
        """delete a file's checkpoint"""
        pass

    def list_checkpoints(self, path):
        """list the checkpoints for a given file

        This contents manager currently only supports one checkpoint per file.
        """
        pass

    # Checkpoint-related utilities
    def checkpoint_path(self, checkpoint_id, path):
        """find the path to a checkpoint"""
        pass

    def checkpoint_model(self, checkpoint_id, os_path):
        """construct the info dict for a given checkpoint"""
        pass

    # Error Handling
    def no_such_checkpoint(self, path, checkpoint_id):
        pass


class AsyncFileCheckpoints(FileCheckpoints, AsyncFileManagerMixin, AsyncCheckpoints):
    async def create_checkpoint(self, contents_mgr, path):
        """Create a checkpoint."""
        pass

    async def restore_checkpoint(self, contents_mgr, checkpoint_id, path):
        """Restore a checkpoint."""
        pass

    async def checkpoint_model(self, checkpoint_id, os_path):
        """construct the info dict for a given checkpoint"""
        pass

    # ContentsManager-independent checkpoint API
    async def rename_checkpoint(self, checkpoint_id, old_path, new_path):
        """Rename a checkpoint from old_path to new_path."""
        pass

    async def delete_checkpoint(self, checkpoint_id, path):
        """delete a file's checkpoint"""
        pass

    async def list_checkpoints(self, path):
        """list the checkpoints for a given file

        This contents manager currently only supports one checkpoint per file.
        """
        pass


class GenericFileCheckpoints(GenericCheckpointsMixin, FileCheckpoints):
    """
    Local filesystem Checkpoints that works with any conforming
    ContentsManager.
    """

    def create_file_checkpoint(self, content, format, path):
        """Create a checkpoint from the current content of a file."""
        pass

    def create_notebook_checkpoint(self, nb, path):
        """Create a checkpoint from the current content of a notebook."""
        pass

    def get_notebook_checkpoint(self, checkpoint_id, path):
        """Get a checkpoint for a notebook."""
        pass

    def get_file_checkpoint(self, checkpoint_id, path):
        """Get a checkpoint for a file."""
        pass


class AsyncGenericFileCheckpoints(AsyncGenericCheckpointsMixin, AsyncFileCheckpoints):
    """
    Asynchronous Local filesystem Checkpoints that works with any conforming
    ContentsManager.
    """

    async def create_file_checkpoint(self, content, format, path):
        """Create a checkpoint from the current content of a file."""
        pass

    async def create_notebook_checkpoint(self, nb, path):
        """Create a checkpoint from the current content of a notebook."""
        pass

    async def get_notebook_checkpoint(self, checkpoint_id, path):
        """Get a checkpoint for a notebook."""
        pass

    async def get_file_checkpoint(self, checkpoint_id, path):
        """Get a checkpoint for a file."""
        pass
