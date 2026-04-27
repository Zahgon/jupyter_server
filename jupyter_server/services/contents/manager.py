"""A base class for contents managers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import itertools
import json
import os
import re
import typing as t
import warnings
from fnmatch import fnmatch

from jupyter_core.utils import ensure_async, run_sync
from jupyter_events import EventLogger
from nbformat import ValidationError, sign
from nbformat import validate as validate_nb
from nbformat.v4 import new_notebook
from tornado.web import HTTPError, RequestHandler
from traitlets import (
    Any,
    Bool,
    Dict,
    Instance,
    List,
    TraitError,
    Type,
    Unicode,
    default,
    validate,
)
from traitlets.config.configurable import LoggingConfigurable

from jupyter_server import DEFAULT_EVENTS_SCHEMA_PATH, JUPYTER_SERVER_EVENTS_URI
from jupyter_server.transutils import _i18n
from jupyter_server.utils import import_item

from ...files.handlers import FilesHandler
from .checkpoints import AsyncCheckpoints, Checkpoints

copy_pat = re.compile(r"\-Copy\d*\.")


class ContentsManager(LoggingConfigurable):
    """Base class for serving files and directories.

    This serves any text or binary file,
    as well as directories,
    with special handling for JSON notebook documents.

    Most APIs take a path argument,
    which is always an API-style unicode path,
    and always refers to a directory.

    - unicode, not url-escaped
    - '/'-separated
    - leading and trailing '/' will be stripped
    - if unspecified, path defaults to '',
      indicating the root path.

    """

    event_schema_id = JUPYTER_SERVER_EVENTS_URI + "/contents_service/v1"
    event_logger = Instance(EventLogger).tag(config=True)

    @default("event_logger")
    def _default_event_logger(self):
        pass

    def emit(self, data):
        """Emit event using the core event schema from Jupyter Server's Contents Manager."""
        pass

    root_dir = Unicode("/", config=True)

    preferred_dir = Unicode(
        "",
        config=True,
        help=_i18n(
            "Preferred starting directory to use for notebooks. This is an API path (`/` separated, relative to root dir)"
        ),
    )

    @validate("preferred_dir")
    def _validate_preferred_dir(self, proposal):
        pass

    allow_hidden = Bool(False, config=True, help="Allow access to hidden files")

    notary = Instance(sign.NotebookNotary)

    @default("notary")
    def _notary_default(self):
        pass

    hide_globs = List(
        Unicode(),
        [
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".DS_Store",
            "*~",
        ],
        config=True,
        help="""
        Glob patterns to hide in file and directory listings.
    """,
    )

    untitled_notebook = Unicode(
        _i18n("Untitled"),
        config=True,
        help="The base name used when creating untitled notebooks.",
    )

    untitled_file = Unicode(
        "untitled", config=True, help="The base name used when creating untitled files."
    )

    untitled_directory = Unicode(
        "Untitled Folder",
        config=True,
        help="The base name used when creating untitled directories.",
    )

    pre_save_hook = Any(
        None,
        config=True,
        allow_none=True,
        help="""Python callable or importstring thereof

        To be called on a contents model prior to save.

        This can be used to process the structure,
        such as removing notebook outputs or other side effects that
        should not be saved.

        It will be called as (all arguments passed by keyword)::

            hook(path=path, model=model, contents_manager=self)

        - model: the model to be saved. Includes file contents.
          Modifying this dict will affect the file that is stored.
        - path: the API path of the save destination
        - contents_manager: this ContentsManager instance
        """,
    )

    @validate("pre_save_hook")
    def _validate_pre_save_hook(self, proposal):
        pass

    post_save_hook = Any(
        None,
        config=True,
        allow_none=True,
        help="""Python callable or importstring thereof

        to be called on the path of a file just saved.

        This can be used to process the file on disk,
        such as converting the notebook to a script or HTML via nbconvert.

        It will be called as (all arguments passed by keyword)::

            hook(os_path=os_path, model=model, contents_manager=instance)

        - path: the filesystem path to the file just written
        - model: the model representing the file
        - contents_manager: this ContentsManager instance
        """,
    )

    @validate("post_save_hook")
    def _validate_post_save_hook(self, proposal):
        pass

    def run_pre_save_hook(self, model, path, **kwargs):
        """Run the pre-save hook if defined, and log errors"""
        pass

    def run_post_save_hook(self, model, os_path):
        """Run the post-save hook if defined, and log errors"""
        pass

    _pre_save_hooks: List[t.Any] = List()
    _post_save_hooks: List[t.Any] = List()

    def register_pre_save_hook(self, hook):
        """Register a pre save hook."""
        pass

    def register_post_save_hook(self, hook):
        """Register a post save hook."""
        pass

    def run_pre_save_hooks(self, model, path, **kwargs):
        """Run the pre-save hooks if any, and log errors"""
        pass

    def run_post_save_hooks(self, model, os_path):
        """Run the post-save hooks if any, and log errors"""
        pass

    checkpoints_class = Type(Checkpoints, config=True)
    checkpoints = Instance(Checkpoints, config=True)
    checkpoints_kwargs = Dict(config=True)

    @default("checkpoints")
    def _default_checkpoints(self):
        pass

    @default("checkpoints_kwargs")
    def _default_checkpoints_kwargs(self):
        pass

    files_handler_class = Type(
        FilesHandler,
        klass=RequestHandler,
        allow_none=True,
        config=True,
        help="""handler class to use when serving raw file requests.

        Default is a fallback that talks to the ContentsManager API,
        which may be inefficient, especially for large files.

        Local files-based ContentsManagers can use a StaticFileHandler subclass,
        which will be much more efficient.

        Access to these files should be Authenticated.
        """,
    )

    files_handler_params = Dict(
        config=True,
        help="""Extra parameters to pass to files_handler_class.

        For example, StaticFileHandlers generally expect a `path` argument
        specifying the root directory from which to serve files.
        """,
    )

    def get_extra_handlers(self):
        """Return additional handlers

        Default: self.files_handler_class on /files/.*
        """
        pass

    # ContentsManager API part 1: methods that must be
    # implemented in subclasses.

    def dir_exists(self, path):
        """Does a directory exist at the given path?

        Like os.path.isdir

        Override this method in subclasses.

        Parameters
        ----------
        path : str
            The path to check

        Returns
        -------
        exists : bool
            Whether the path does indeed exist.
        """
        pass

    def is_hidden(self, path):
        """Is path a hidden directory or file?

        Parameters
        ----------
        path : str
            The path to check. This is an API path (`/` separated,
            relative to root dir).

        Returns
        -------
        hidden : bool
            Whether the path is hidden.

        """
        pass

    def file_exists(self, path):
        """Does a file exist at the given path?

        Like os.path.isfile

        Override this method in subclasses.

        Parameters
        ----------
        path : str
            The API path of a file to check for.

        Returns
        -------
        exists : bool
            Whether the file exists.
        """
        pass

    def exists(self, path):
        """Does a file or directory exist at the given path?

        Like os.path.exists

        Parameters
        ----------
        path : str
            The API path of a file or directory to check for.

        Returns
        -------
        exists : bool
            Whether the target exists.
        """
        pass

    def get(self, path, content=True, type=None, format=None, require_hash=False):
        """Get a file or directory model.

        Parameters
        ----------
        require_hash : bool
            Whether the file hash must be returned or not.

        *Changed in version 2.11*: The *require_hash* parameter was added.
        """
        pass

    def save(self, model, path):
        """
        Save a file or directory model to path.

        Should return the saved model with no content.  Save implementations
        should call self.run_pre_save_hook(model=model, path=path) prior to
        writing any data.
        """
        pass

    def delete_file(self, path):
        """Delete the file or directory at path."""
        pass

    def rename_file(self, old_path, new_path):
        """Rename a file or directory."""
        pass

    # ContentsManager API part 2: methods that have usable default
    # implementations, but can be overridden in subclasses.

    def delete(self, path):
        """Delete a file/directory and any associated checkpoints."""
        pass

    def rename(self, old_path, new_path):
        """Rename a file and any checkpoints associated with that file."""
        pass

    def update(self, model, path):
        """Update the file's path

        For use in PATCH requests, to enable renaming a file without
        re-uploading its contents. Only used for renaming at the moment.
        """
        pass

    def info_string(self):
        """The information string for the manager."""
        pass

    def get_kernel_path(self, path, model=None):
        """Return the API path for the kernel

        KernelManagers can turn this value into a filesystem path,
        or ignore it altogether.

        The default value here will start kernels in the directory of the
        notebook server. FileContentsManager overrides this to use the
        directory containing the notebook.
        """
        pass

    def increment_filename(self, filename, path="", insert=""):
        """Increment a filename until it is unique.

        Parameters
        ----------
        filename : unicode
            The name of a file, including extension
        path : unicode
            The API path of the target's directory
        insert : unicode
            The characters to insert after the base filename

        Returns
        -------
        name : unicode
            A filename that is unique, based on the input filename.
        """
        pass

    def validate_notebook_model(self, model, validation_error=None):
        """Add failed-validation message to model"""
        pass

    def new_untitled(self, path="", type="", ext=""):
        """Create a new untitled file or directory in path

        path must be a directory

        File extension can be specified.

        Use `new` to create files with a fully specified path (including filename).
        """
        pass

    def new(self, model=None, path=""):
        """Create a new file or directory and return its model with no content.

        To create a new untitled entity in a directory, use `new_untitled`.
        """
        pass

    def copy(self, from_path, to_path=None):
        """Copy an existing file and return its new model.

        If to_path not specified, it will be the parent directory of from_path.
        If to_path is a directory, filename will increment `from_path-Copy#.ext`.
        Considering multi-part extensions, the Copy# part will be placed before the first dot for all the extensions except `ipynb`.
        For easier manual searching in case of notebooks, the Copy# part will be placed before the last dot.

        from_path must be a full path to a file.
        """
        pass

    def log_info(self):
        """Log the information string for the manager."""
        pass

    def trust_notebook(self, path):
        """Explicitly trust a notebook

        Parameters
        ----------
        path : str
            The path of a notebook
        """
        pass

    def check_and_sign(self, nb, path=""):
        """Check for trusted cells, and sign the notebook.

        Called as a part of saving notebooks.

        Parameters
        ----------
        nb : dict
            The notebook dict
        path : str
            The notebook's path (for logging)
        """
        pass

    def mark_trusted_cells(self, nb, path=""):
        """Mark cells as trusted if the notebook signature matches.

        Called as a part of loading notebooks.

        Parameters
        ----------
        nb : dict
            The notebook object (in current nbformat)
        path : str
            The notebook's path (for logging)
        """
        pass

    def should_list(self, name):
        """Should this file/directory name be displayed in a listing?"""
        pass

    # Part 3: Checkpoints API
    def create_checkpoint(self, path):
        """Create a checkpoint."""
        pass

    def restore_checkpoint(self, checkpoint_id, path):
        """
        Restore a checkpoint.
        """
        pass

    def list_checkpoints(self, path):
        pass

    def delete_checkpoint(self, checkpoint_id, path):
        pass


class AsyncContentsManager(ContentsManager):
    """Base class for serving files and directories asynchronously."""

    checkpoints_class = Type(AsyncCheckpoints, config=True)
    checkpoints = Instance(AsyncCheckpoints, config=True)
    checkpoints_kwargs = Dict(config=True)

    @default("checkpoints")
    def _default_checkpoints(self):
        pass

    @default("checkpoints_kwargs")
    def _default_checkpoints_kwargs(self):
        pass

    # ContentsManager API part 1: methods that must be
    # implemented in subclasses.

    async def dir_exists(self, path):
        """Does a directory exist at the given path?

        Like os.path.isdir

        Override this method in subclasses.

        Parameters
        ----------
        path : str
            The path to check

        Returns
        -------
        exists : bool
            Whether the path does indeed exist.
        """
        pass

    async def is_hidden(self, path):
        """Is path a hidden directory or file?

        Parameters
        ----------
        path : str
            The path to check. This is an API path (`/` separated,
            relative to root dir).

        Returns
        -------
        hidden : bool
            Whether the path is hidden.

        """
        pass

    async def file_exists(self, path):
        """Does a file exist at the given path?

        Like os.path.isfile

        Override this method in subclasses.

        Parameters
        ----------
        path : str
            The API path of a file to check for.

        Returns
        -------
        exists : bool
            Whether the file exists.
        """
        pass

    async def exists(self, path):
        """Does a file or directory exist at the given path?

        Like os.path.exists

        Parameters
        ----------
        path : str
            The API path of a file or directory to check for.

        Returns
        -------
        exists : bool
            Whether the target exists.
        """
        pass

    async def get(self, path, content=True, type=None, format=None, require_hash=False):
        """Get a file or directory model.

        Parameters
        ----------
        require_hash : bool
            Whether the file hash must be returned or not.

        *Changed in version 2.11*: The *require_hash* parameter was added.
        """
        pass

    async def save(self, model, path):
        """
        Save a file or directory model to path.

        Should return the saved model with no content.  Save implementations
        should call self.run_pre_save_hook(model=model, path=path) prior to
        writing any data.
        """
        pass

    async def delete_file(self, path):
        """Delete the file or directory at path."""
        pass

    async def rename_file(self, old_path, new_path):
        """Rename a file or directory."""
        pass

    # ContentsManager API part 2: methods that have usable default
    # implementations, but can be overridden in subclasses.

    async def delete(self, path):
        """Delete a file/directory and any associated checkpoints."""
        pass

    async def rename(self, old_path, new_path):
        """Rename a file and any checkpoints associated with that file."""
        pass

    async def update(self, model, path):
        """Update the file's path

        For use in PATCH requests, to enable renaming a file without
        re-uploading its contents. Only used for renaming at the moment.
        """
        pass

    async def increment_filename(self, filename, path="", insert=""):
        """Increment a filename until it is unique.

        Parameters
        ----------
        filename : unicode
            The name of a file, including extension
        path : unicode
            The API path of the target's directory
        insert : unicode
            The characters to insert after the base filename

        Returns
        -------
        name : unicode
            A filename that is unique, based on the input filename.
        """
        pass

    async def new_untitled(self, path="", type="", ext=""):
        """Create a new untitled file or directory in path

        path must be a directory

        File extension can be specified.

        Use `new` to create files with a fully specified path (including filename).
        """
        pass

    async def new(self, model=None, path=""):
        """Create a new file or directory and return its model with no content.

        To create a new untitled entity in a directory, use `new_untitled`.
        """
        pass

    async def copy(self, from_path, to_path=None):
        """Copy an existing file and return its new model.

        If to_path not specified, it will be the parent directory of from_path.
        If to_path is a directory, filename will increment `from_path-Copy#.ext`.
        Considering multi-part extensions, the Copy# part will be placed before the first dot for all the extensions except `ipynb`.
        For easier manual searching in case of notebooks, the Copy# part will be placed before the last dot.

        from_path must be a full path to a file.
        """
        pass

    async def trust_notebook(self, path):
        """Explicitly trust a notebook

        Parameters
        ----------
        path : str
            The path of a notebook
        """
        pass

    # Part 3: Checkpoints API
    async def create_checkpoint(self, path):
        """Create a checkpoint."""
        pass

    async def restore_checkpoint(self, checkpoint_id, path):
        """
        Restore a checkpoint.
        """
        pass

    async def list_checkpoints(self, path):
        """List the checkpoints for a path."""
        pass

    async def delete_checkpoint(self, checkpoint_id, path):
        """Delete a checkpoint for a path by id."""
        pass
