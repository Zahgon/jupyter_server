import base64
import os

from anyio.to_thread import run_sync
from tornado import web

from jupyter_server.services.contents.filemanager import (
    AsyncFileContentsManager,
    FileContentsManager,
)


class LargeFileManager(FileContentsManager):
    """Handle large file upload."""

    def save(self, model, path=""):
        """Save the file model and return the model with no content."""
        pass

    def _save_large_file(self, os_path, content, format):
        """Save content of a generic file."""
        pass


class AsyncLargeFileManager(AsyncFileContentsManager):
    """Handle large file upload asynchronously"""

    async def save(self, model, path=""):
        """Save the file model and return the model with no content."""
        pass

    async def _save_large_file(self, os_path, content, format):
        """Save content of a generic file."""
        pass
