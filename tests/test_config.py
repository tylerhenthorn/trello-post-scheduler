import tempfile
from pathlib import Path

import pytest

from trello_post_scheduler.config import load_config, AppConfig
from trello_post_scheduler.exceptions import ConfigError


VALID_CONFIG = """\
[trello]
api_key = "key123"
api_token = "token456"
board_id = "board789"
source_list = "Post Queue"

[schedule]
post_times = ["10:00", "16:00"]
post_time_randomization = 300

[platforms.twitter]
enabled = true
api_key = "tk"
api_secret = "ts"
access_token = "at"
access_secret = "as"
bearer_token = "bt"

[platforms.bluesky]
enabled = false
handle = "test.bsky.social"
password = "pass"

[logging]
level = "DEBUG"
"""


def _write_config(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def test_load_valid_config():
    path = _write_config(VALID_CONFIG)
    cfg = load_config(path)
    assert isinstance(cfg, AppConfig)
    assert cfg.trello.api_key == "key123"
    assert cfg.trello.board_id == "board789"
    assert cfg.schedule.post_times == ["10:00", "16:00"]
    assert cfg.schedule.post_time_randomization == 300
    assert cfg.platforms.twitter is not None
    assert cfg.platforms.twitter.enabled is True
    assert cfg.platforms.bluesky is not None
    assert cfg.platforms.bluesky.enabled is False
    assert cfg.platforms.mastodon is None
    assert cfg.logging.level == "DEBUG"


def test_missing_trello_section():
    path = _write_config("[schedule]\npost_time_randomization = 60\n")
    with pytest.raises(ConfigError, match="missing \\[trello\\]"):
        load_config(path)


def test_missing_required_trello_fields():
    path = _write_config('[trello]\napi_key = ""\napi_token = "t"\nboard_id = "b"\n')
    with pytest.raises(ConfigError, match="required"):
        load_config(path)


def test_file_not_found():
    with pytest.raises(ConfigError, match="not found"):
        load_config(Path("/nonexistent/config.toml"))


def test_defaults_applied():
    minimal = '[trello]\napi_key = "k"\napi_token = "t"\nboard_id = "b"\n'
    path = _write_config(minimal)
    cfg = load_config(path)
    assert cfg.schedule.post_time_randomization == 600
    assert cfg.platforms.twitter is None
    assert cfg.logging.level == "INFO"
