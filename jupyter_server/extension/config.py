"""Extension config."""

from jupyter_server.services.config.manager import ConfigManager

DEFAULT_SECTION_NAME = "jupyter_server_config"


class ExtensionConfigManager(ConfigManager):
    """A manager class to interface with Jupyter Server Extension config
    found in a `config.d` folder. It is assumed that all configuration
    files in this directory are JSON files.
    """

    def get_jpserver_extensions(self, section_name=DEFAULT_SECTION_NAME):
        """Return the jpserver_extensions field from all
        config files found."""
        pass

    def enabled(self, name, section_name=DEFAULT_SECTION_NAME, include_root=True):
        """Is the extension enabled?"""
        pass

    def enable(self, name):
        """Enable an extension by name."""
        pass

    def disable(self, name):
        """Disable an extension by name."""
        pass
