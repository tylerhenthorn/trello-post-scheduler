import pytest
from pathlib import Path


@pytest.fixture
def example_config_path():
    return Path(__file__).parent.parent / "config.example.toml"
