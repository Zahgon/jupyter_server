"""An extension application."""

from __future__ import annotations

import logging
import re
import sys
import typing as t

from jinja2 import Environment, FileSystemLoader
from jupyter_core.application import JupyterApp, NoStart
from tornado.log import LogFormatter
from tornado.web import RedirectHandler
from traitlets import Any, Bool, Dict, HasTraits, List, Unicode, default
from traitlets.config import Config

from jupyter_server.serverapp import ServerApp
from jupyter_server.transutils import _i18n
from jupyter_server.utils import is_namespace_package, url_path_join

from .handler import ExtensionHandlerMixin

# -----------------------------------------------------------------------------
# Util functions and classes.
# -----------------------------------------------------------------------------


def _preparse_for_subcommand(application_klass, argv):
    """Preparse command line to look for subcommands."""
    pass


def _preparse_for_stopping_flags(application_klass, argv):
    """Looks for 'help', 'version', and 'generate-config; commands
    in command line. If found, raises the help and version of
    current Application.

    This is useful for traitlets applications that have to parse
    the command line multiple times, but want to control when
    when 'help' and 'version' is raised.
    """
    pass


class ExtensionAppJinjaMixin(HasTraits):
    """Use Jinja templates for HTML templates on top of an ExtensionApp."""

    jinja2_options = Dict(
        help=_i18n(
            """Options to pass to the jinja2 environment for this
        """
        )
    ).tag(config=True)

    @t.no_type_check
    def _prepare_templates(self):
        """Get templates defined in a subclass."""
        pass


# -----------------------------------------------------------------------------
# ExtensionApp
# -----------------------------------------------------------------------------


class JupyterServerExtensionException(Exception):
    """Exception class for raising for Server extensions errors."""


# -----------------------------------------------------------------------------
# ExtensionApp
# -----------------------------------------------------------------------------


class ExtensionApp(JupyterApp):
    """Base class for configurable Jupyter Server Extension Applications.

    ExtensionApp subclasses can be initialized two ways:

    - Extension is listed as a jpserver_extension, and ServerApp calls
      its load_jupyter_server_extension classmethod. This is the
      classic way of loading a server extension.

    - Extension is launched directly by calling its `launch_instance`
      class method. This method can be set as a entry_point in
      the extensions setup.py.
    """

    # Subclasses should override this trait. Tells the server if
    # this extension allows other other extensions to be loaded
    # side-by-side when launched directly.
    load_other_extensions = True

    # A useful class property that subclasses can override to
    # configure the underlying Jupyter Server when this extension
    # is launched directly (using its `launch_instance` method).
    serverapp_config: dict[str, t.Any] = {}

    # Some subclasses will likely override this trait to flip
    # the default value to False if they don't offer a browser
    # based frontend.
    open_browser = Bool(
        help="""Whether to open in a browser after starting.
        The specific browser used is platform dependent and
        determined by the python standard library `webbrowser`
        module, unless it is overridden using the --browser
        (ServerApp.browser) configuration option.
        """
    ).tag(config=True)

    @default("open_browser")
    def _default_open_browser(self):
        pass

    @property
    def config_file_paths(self):
        """Look on the same path as our parent for config files"""
        pass

    # The extension name used to name the jupyter config
    # file, jupyter_{name}_config.
    # This should also match the jupyter subcommand used to launch
    # this extension from the CLI, e.g. `jupyter {name}`.
    name: str | Unicode[str, str] = "ExtensionApp"

    @classmethod
    def get_extension_package(cls):
        """Get an extension package."""
        pass

    @classmethod
    def get_extension_point(cls):
        """Get an extension point."""
        pass

    # Extension URL sets the default landing page for this extension.
    extension_url = "/"

    default_url = Unicode().tag(config=True)

    @default("default_url")
    def _default_url(self):
        pass

    file_url_prefix = Unicode("notebooks")

    # Is this linked to a serverapp yet?
    _linked = Bool(False)

    # Extension can configure the ServerApp from the command-line
    classes = [
        ServerApp,
    ]

    # A ServerApp is not defined yet, but will be initialized below.
    serverapp: ServerApp | None = Any()  # type:ignore[assignment]

    @default("serverapp")
    def _default_serverapp(self):
        # load the current global instance, if any
        pass

    _log_formatter_cls = LogFormatter  # type:ignore[assignment]

    @default("log_level")
    def _default_log_level(self):
        pass

    @default("log_format")
    def _default_log_format(self):
        """override default log format to include date & time"""
        pass

    static_url_prefix = Unicode(
        help="""Url where the static assets for the extension are served."""
    ).tag(config=True)

    @default("static_url_prefix")
    def _default_static_url_prefix(self):
        pass

    static_paths = List(
        Unicode(),
        help="""paths to search for serving static files.

        This allows adding javascript/css to be available from the notebook server machine,
        or overriding individual files in the IPython
        """,
    ).tag(config=True)

    template_paths = List(
        Unicode(),
        help=_i18n(
            """Paths to search for serving jinja templates.

        Can be used to override templates from notebook.templates."""
        ),
    ).tag(config=True)

    settings = Dict(help=_i18n("""Settings that will passed to the server.""")).tag(config=True)

    handlers: List[tuple[t.Any, ...]] = List(
        help=_i18n("""Handlers appended to the server.""")
    ).tag(config=True)

    def _config_file_name_default(self):
        """The default config file name."""
        pass

    def initialize_settings(self):
        """Override this method to add handling of settings."""

    def initialize_handlers(self):
        """Override this method to append handlers to a Jupyter Server."""

    def initialize_templates(self):
        """Override this method to add handling of template files."""

    def _prepare_config(self):
        """Builds a Config object from the extension's traits and passes
        the object to the webapp's settings as `<name>_config`.
        """
        pass

    def _prepare_settings(self):
        """Prepare the settings."""
        pass

    def _prepare_handlers(self):
        """Prepare the handlers."""
        pass

    def _prepare_templates(self):
        """Add templates to web app settings if extension has templates."""
        pass

    def _jupyter_server_config(self):
        """The jupyter server config."""
        pass

    def _link_jupyter_server_extension(self, serverapp: ServerApp) -> None:
        """Link the ExtensionApp to an initialized ServerApp.

        The ServerApp is stored as an attribute and config
        is exchanged between ServerApp and `self` in case
        the command line contains traits for the ExtensionApp
        or the ExtensionApp's config files have server
        settings.

        Note, the ServerApp has not initialized the Tornado
        Web Application yet, so do not try to affect the
        `web_app` attribute.
        """
        pass

    def initialize(self):  # type: ignore[override]
        """Initialize the extension app. The
        corresponding server app and webapp should already
        be initialized by this step.

        - Appends Handlers to the ServerApp,
        - Passes config and settings from ExtensionApp
          to the Tornado web application
        - Points Tornado Webapp to templates and static assets.
        """
        pass

    def start(self):
        """Start the underlying Jupyter server.

        Server should be started after extension is initialized.
        """
        pass

    def current_activity(self):
        """Return a list of activity happening in this extension."""
        pass

    async def stop_extension(self):
        """Cleanup any resources managed by this extension."""

    def stop(self):
        """Stop the underlying Jupyter server."""
        pass

    @classmethod
    def _load_jupyter_server_extension(cls, serverapp):
        """Initialize and configure this extension, then add the extension's
        settings and handlers to the server's web application.
        """
        pass

    async def _start_jupyter_server_extension(self, serverapp):
        """
        An async hook to start e.g. tasks from the extension after
        the server's event loop is running.

        Override this method (no need to call `super()`) to
        start (async) tasks from an extension.

        This is useful for starting e.g. background tasks from
        an extension.
        """

    @classmethod
    def load_classic_server_extension(cls, serverapp):
        """Enables extension to be loaded as classic Notebook (jupyter/notebook) extension."""
        pass

    serverapp_class = ServerApp

    @classmethod
    def make_serverapp(cls, **kwargs: t.Any) -> ServerApp:
        """Instantiate the ServerApp

        Override to customize the ServerApp before it loads any configuration
        """
        pass

    @classmethod
    def initialize_server(cls, argv=None, load_other_extensions=True, **kwargs):
        """Creates an instance of ServerApp and explicitly sets
        this extension to enabled=True (i.e. superseding disabling
        found in other config from files).

        The `launch_instance` method uses this method to initialize
        and start a server.
        """
        pass

    @classmethod
    def launch_instance(cls, argv=None, **kwargs):
        """Launch the extension like an application. Initializes+configs a stock server
        and appends the extension to the server. Then starts the server and routes to
        extension's landing page.
        """
        pass
