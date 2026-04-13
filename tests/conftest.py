import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Stub atproto and its sub-packages so bluesky.py can be imported in
# environments where the native cryptography extensions are unavailable.
for _mod in ["atproto", "atproto_client", "atproto_client.models"]:
    sys.modules.setdefault(_mod, MagicMock())


@pytest.fixture
def example_config_path():
    return Path(__file__).parent.parent / "config.example.toml"
