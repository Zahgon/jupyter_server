"""An extension handler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from jinja2.exceptions import TemplateNotFound

from jupyter_server.base.handlers import FileFindHandler

if TYPE_CHECKING:
    from logging import Logger

    from jinja2 import Template
    from traitlets.config import Config

    from jupyter_server.extension.application import ExtensionApp
    from jupyter_server.serverapp import ServerApp


class ExtensionHandlerJinjaMixin:
    """Mixin class for ExtensionApp handlers that use jinja templating for
    template rendering.
    """

    def get_template(self, name: str) -> Template:
        """Return the jinja template object for a given name"""
        pass


class ExtensionHandlerMixin:
    """Base class for Jupyter server extension handlers.

    Subclasses can serve static files behind a namespaced
    endpoint: "<base_url>/static/<name>/"

    This allows multiple extensions to serve static files under
    their own namespace and avoid intercepting requests for
    other extensions.
    """

    settings: dict[str, Any]

    def initialize(self, name: str, *args: Any, **kwargs: Any) -> None:
        pass

    @property
    def extensionapp(self) -> ExtensionApp:
        pass

    @property
    def serverapp(self) -> ServerApp:
        pass

    @property
    def log(self) -> Logger:
        if not hasattr(self, "name"):
            return cast("Logger", super().log)  # type:ignore[misc]
        # Attempt to pull the ExtensionApp's log, otherwise fall back to ServerApp.
        try:
            return cast("Logger", self.extensionapp.log)
        except AttributeError:
            return cast("Logger", self.serverapp.log)

    @property
    def config(self) -> Config:
        pass

    @property
    def server_config(self) -> Config:
        pass

    @property
    def base_url(self) -> str:
        pass

    def render_template(self, name: str, **ns) -> str:
        """Override render template to handle static_paths

        If render_template is called with a template from the base environment
        (e.g. default error pages)
        make sure our extension-specific static_url is _not_ used.
        """
        pass

    @property
    def static_url_prefix(self) -> str:
        pass

    @property
    def static_path(self) -> str:
        pass

    def static_url(self, path: str, include_host: bool | None = None, **kwargs: Any) -> str:
        """Returns a static URL for the given relative static file path.
        This method requires you set the ``{name}_static_path``
        setting in your extension (which specifies the root directory
        of your static files).
        This method returns a versioned url (by default appending
        ``?v=<signature>``), which allows the static files to be
        cached indefinitely.  This can be disabled by passing
        ``include_version=False`` (in the default implementation;
        other static file implementations are not required to support
        this, but they may support other options).
        By default this method returns URLs relative to the current
        host, but if ``include_host`` is true the URL returned will be
        absolute.  If this handler has an ``include_host`` attribute,
        that value will be used as the default for all `static_url`
        calls that do not pass ``include_host`` as a keyword argument.
        """
        pass
