"""The extension manager."""

from __future__ import annotations

import importlib
import logging
from itertools import starmap

from tornado.gen import multi
from traitlets import Any, Bool, Dict, HasTraits, Instance, List, Unicode, default, observe
from traitlets import validate as validate_trait
from traitlets.config import LoggingConfigurable

from .config import ExtensionConfigManager
from .utils import ExtensionMetadataError, ExtensionModuleNotFound, get_loader, get_metadata


class ExtensionPoint(HasTraits):
    """A simple API for connecting to a Jupyter Server extension
    point defined by metadata and importable from a Python package.
    """

    _linked = Bool(False)
    _app = Any(None, allow_none=True)

    metadata = Dict()

    log = Instance(logging.Logger)

    @default("log")
    def _default_log(self):
        pass

    @validate_trait("metadata")
    def _valid_metadata(self, proposed):
        """Validate metadata."""
        pass

    @property
    def linked(self):
        """Has this extension point been linked to the server.

        Will pull from ExtensionApp's trait, if this point
        is an instance of ExtensionApp.
        """
        pass

    @property
    def app(self):
        """If the metadata includes an `app` field"""
        pass

    @property
    def config(self):
        """Return any configuration provided by this extension point."""
        pass

    @property
    def module_name(self):
        """Name of the Python package module where the extension's
        _load_jupyter_server_extension can be found.
        """
        pass

    @property
    def name(self):
        """Name of the extension.

        If it's not provided in the metadata, `name` is set
        to the extensions' module name.
        """
        pass

    @property
    def module(self):
        """The imported module (using importlib.import_module)"""
        pass

    def _get_linker(self):
        """Get a linker."""
        pass

    def _get_loader(self):
        """Get a loader."""
        pass

    def _get_starter(self):
        """Get a starter function."""
        pass

    def validate(self):
        """Check that both a linker and loader exists."""
        pass

    def link(self, serverapp):
        """Link the extension to a Jupyter ServerApp object.

        This looks for a `_link_jupyter_server_extension` function
        in the extension's module or ExtensionApp class.
        """
        pass

    def load(self, serverapp):
        """Load the extension in a Jupyter ServerApp object.

        This looks for a `_load_jupyter_server_extension` function
        in the extension's module or ExtensionApp class.
        """
        pass

    async def start(self, serverapp):
        """Call's the extensions 'start' hook where it can
        start (possibly async) tasks _after_ the event loop is running.
        """
        pass


class ExtensionPackage(LoggingConfigurable):
    """An API for interfacing with a Jupyter Server extension package.

    Usage:

    ext_name = "my_extensions"
    extpkg = ExtensionPackage(name=ext_name)
    """

    name = Unicode(help="Name of the an importable Python package.")
    enabled = Bool(False, help="Whether the extension package is enabled.")

    _linked_points = Dict()
    extension_points = Dict()
    module = Any(allow_none=True, help="The module for this extension package. None if not enabled")
    metadata = List(Dict(), help="Extension metadata loaded from the extension package.")
    version = Unicode(
        help="""
            The version of this extension package, if it can be found.
            Otherwise, an empty string.
            """,
    )

    @default("version")
    def _load_version(self):
        pass

    def __init__(self, **kwargs):
        """Initialize an extension package."""
        super().__init__(**kwargs)
        if self.enabled:
            self._load_metadata()

    def _load_metadata(self):
        """Import package and load metadata

        Only used if extension package is enabled
        """
        pass

    def validate(self):
        """Validate all extension points in this package."""
        pass

    def link_point(self, point_name, serverapp):
        """Link an extension point."""
        pass

    def load_point(self, point_name, serverapp):
        """Load an extension point."""
        pass

    async def start_point(self, point_name, serverapp):
        """Load an extension point."""
        pass

    def link_all_points(self, serverapp):
        """Link all extension points."""
        pass

    def load_all_points(self, serverapp):
        """Load all extension points."""
        pass

    async def start_all_points(self, serverapp):
        """Load all extension points."""
        pass


class ExtensionManager(LoggingConfigurable):
    """High level interface for finding, validating,
    linking, loading, and managing Jupyter Server extensions.

    Usage:
    m = ExtensionManager(config_manager=...)
    """

    config_manager = Instance(ExtensionConfigManager, allow_none=True)

    serverapp = Any()  # Use Any to avoid circular import of Instance(ServerApp)

    @default("config_manager")
    def _load_default_config_manager(self):
        pass

    @observe("config_manager")
    def _config_manager_changed(self, change):
        pass

    # The `extensions` attribute provides a dictionary
    # with extension (package) names mapped to their ExtensionPackage interface
    # (see above). This manager simplifies the interaction between the
    # ServerApp and the extensions being appended.
    extensions = Dict(
        help="""
        Dictionary with extension package names as keys
        and ExtensionPackage objects as values.
        """
    )

    @property
    def sorted_extensions(self):
        """Returns an extensions dictionary, sorted alphabetically."""
        pass

    # The `_linked_extensions` attribute tracks when each extension
    # has been successfully linked to a ServerApp. This helps prevent
    # extensions from being re-linked recursively unintentionally if another
    # extension attempts to link extensions again.
    linked_extensions = Dict(
        help="""
        Dictionary with extension names as keys

        values are True if the extension is linked, False if not.
        """
    )

    @property
    def extension_apps(self):
        """Return mapping of extension names and sets of ExtensionApp objects."""
        pass

    @property
    def extension_points(self):
        """Return mapping of extension point names and ExtensionPoint objects."""
        pass

    def from_config_manager(self, config_manager):
        """Add extensions found by an ExtensionConfigManager"""
        pass

    def _load_config_manager(self, config_manager):
        """Actually load our config manager"""
        pass

    def from_jpserver_extensions(self, jpserver_extensions):
        """Add extensions from 'jpserver_extensions'-like dictionary."""
        pass

    def add_extension(self, extension_name, enabled=False):
        """Try to add extension to manager, return True if successful.
        Otherwise, return False.
        """
        pass

    def link_extension(self, name):
        """Link an extension by name."""
        pass

    def load_extension(self, name):
        """Load an extension by name."""
        pass

    async def start_extension(self, name):
        """Start an extension by name."""
        pass

    async def stop_extension(self, name, apps):
        """Call the shutdown hooks in the specified apps."""
        pass

    def link_all_extensions(self):
        """Link all enabled extensions
        to an instance of ServerApp
        """
        pass

    def load_all_extensions(self):
        """Load all enabled extensions and append them to
        the parent ServerApp.
        """
        pass

    async def start_all_extensions(self):
        """Start all enabled extensions."""
        pass

    async def stop_all_extensions(self):
        """Call the shutdown hooks in all extensions."""
        pass

    def any_activity(self):
        """Check for any activity currently happening across all extension applications."""
        pass
