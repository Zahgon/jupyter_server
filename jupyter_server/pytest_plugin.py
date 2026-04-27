"""Pytest Fixtures exported by Jupyter Server."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from pathlib import Path

import pytest

from jupyter_server.services.contents.filemanager import AsyncFileContentsManager
from jupyter_server.services.contents.largefilemanager import AsyncLargeFileManager

pytest_plugins = ["pytest_jupyter.jupyter_server"]

some_resource = "The very model of a modern major general"
sample_kernel_json = {
    "argv": ["cat", "{connection_file}"],
    "display_name": "Test kernel",
}


@pytest.fixture  # type: ignore[untyped-decorator]
def jp_kernelspecs(jp_data_dir: Path) -> None:
    """Configures some sample kernelspecs in the Jupyter data directory."""
    pass


@pytest.fixture(params=[True, False])
def jp_contents_manager(request, tmp_path):
    """Returns an AsyncFileContentsManager instance based on the use_atomic_writing parameter value."""
    pass


@pytest.fixture
def jp_large_contents_manager(tmp_path):
    """Returns an AsyncLargeFileManager instance."""
    pass
