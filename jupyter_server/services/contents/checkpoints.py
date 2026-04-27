"""
Classes for managing Checkpoints.
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from tornado.web import HTTPError
from traitlets.config.configurable import LoggingConfigurable


class Checkpoints(LoggingConfigurable):
    """
    Base class for managing checkpoints for a ContentsManager.

    Subclasses are required to implement:

    create_checkpoint(self, contents_mgr, path)
    restore_checkpoint(self, contents_mgr, checkpoint_id, path)
    rename_checkpoint(self, checkpoint_id, old_path, new_path)
    delete_checkpoint(self, checkpoint_id, path)
    list_checkpoints(self, path)
    """

    def create_checkpoint(self, contents_mgr, path):
        """Create a checkpoint."""
        pass

    def restore_checkpoint(self, contents_mgr, checkpoint_id, path):
        """Restore a checkpoint"""
        pass

    def rename_checkpoint(self, checkpoint_id, old_path, new_path):
        """Rename a single checkpoint from old_path to new_path."""
        pass

    def delete_checkpoint(self, checkpoint_id, path):
        """delete a checkpoint for a file"""
        pass

    def list_checkpoints(self, path):
        """Return a list of checkpoints for a given file"""
        pass

    def rename_all_checkpoints(self, old_path, new_path):
        """Rename all checkpoints for old_path to new_path."""
        pass

    def delete_all_checkpoints(self, path):
        """Delete all checkpoints for the given path."""
        pass


class GenericCheckpointsMixin:
    """
    Helper for creating Checkpoints subclasses that can be used with any
    ContentsManager.

    Provides a ContentsManager-agnostic implementation of `create_checkpoint`
    and `restore_checkpoint` in terms of the following operations:

    - create_file_checkpoint(self, content, format, path)
    - create_notebook_checkpoint(self, nb, path)
    - get_file_checkpoint(self, checkpoint_id, path)
    - get_notebook_checkpoint(self, checkpoint_id, path)

    To create a generic CheckpointManager, add this mixin to a class that
    implement the above four methods plus the remaining Checkpoints API
    methods:

    - delete_checkpoint(self, checkpoint_id, path)
    - list_checkpoints(self, path)
    - rename_checkpoint(self, checkpoint_id, old_path, new_path)
    """

    def create_checkpoint(self, contents_mgr, path):
        pass

    def restore_checkpoint(self, contents_mgr, checkpoint_id, path):
        """Restore a checkpoint."""
        pass

    # Required Methods
    def create_file_checkpoint(self, content, format, path):
        """Create a checkpoint of the current state of a file

        Returns a checkpoint model for the new checkpoint.
        """
        pass

    def create_notebook_checkpoint(self, nb, path):
        """Create a checkpoint of the current state of a file

        Returns a checkpoint model for the new checkpoint.
        """
        pass

    def get_file_checkpoint(self, checkpoint_id, path):
        """Get the content of a checkpoint for a non-notebook file.

        Returns a dict of the form::

            {
                'type': 'file',
                'content': <str>,
                'format': {'text','base64'},
            }
        """
        pass

    def get_notebook_checkpoint(self, checkpoint_id, path):
        """Get the content of a checkpoint for a notebook.

        Returns a dict of the form::

            {
                'type': 'notebook',
                'content': <output of nbformat.read>,
            }
        """
        pass


class AsyncCheckpoints(Checkpoints):
    """
    Base class for managing checkpoints for a ContentsManager asynchronously.
    """

    async def create_checkpoint(self, contents_mgr, path):
        """Create a checkpoint."""
        pass

    async def restore_checkpoint(self, contents_mgr, checkpoint_id, path):
        """Restore a checkpoint"""
        pass

    async def rename_checkpoint(self, checkpoint_id, old_path, new_path):
        """Rename a single checkpoint from old_path to new_path."""
        pass

    async def delete_checkpoint(self, checkpoint_id, path):
        """delete a checkpoint for a file"""
        pass

    async def list_checkpoints(self, path):
        """Return a list of checkpoints for a given file"""
        pass

    async def rename_all_checkpoints(self, old_path, new_path):
        """Rename all checkpoints for old_path to new_path."""
        pass

    async def delete_all_checkpoints(self, path):
        """Delete all checkpoints for the given path."""
        pass


class AsyncGenericCheckpointsMixin(GenericCheckpointsMixin):
    """
    Helper for creating Asynchronous Checkpoints subclasses that can be used with any
    ContentsManager.
    """

    async def create_checkpoint(self, contents_mgr, path):
        pass

    async def restore_checkpoint(self, contents_mgr, checkpoint_id, path):
        """Restore a checkpoint."""
        pass

    # Required Methods
    async def create_file_checkpoint(self, content, format, path):
        """Create a checkpoint of the current state of a file

        Returns a checkpoint model for the new checkpoint.
        """
        pass

    async def create_notebook_checkpoint(self, nb, path):
        """Create a checkpoint of the current state of a file

        Returns a checkpoint model for the new checkpoint.
        """
        pass

    async def get_file_checkpoint(self, checkpoint_id, path):
        """Get the content of a checkpoint for a non-notebook file.

        Returns a dict of the form::

            {
                'type': 'file',
                'content': <str>,
                'format': {'text','base64'},
            }
        """
        pass

    async def get_notebook_checkpoint(self, checkpoint_id, path):
        """Get the content of a checkpoint for a notebook.

        Returns a dict of the form::

            {
                'type': 'notebook',
                'content': <output of nbformat.read>,
            }
        """
        pass
