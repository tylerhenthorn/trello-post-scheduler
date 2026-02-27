from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from trello_post_scheduler.exceptions import ConfigError


@dataclass
class TrelloConfig:
    api_key: str
    api_token: str
    board_id: str
    source_list: str = "Post Queue"


@dataclass
class ScheduleConfig:
    post_times: list[str] = field(default_factory=lambda: ["09:00", "13:00", "18:30"])
    post_time_randomization: int = 600


@dataclass
class TwitterConfig:
    enabled: bool = False
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    access_secret: str = ""
    bearer_token: str = ""


@dataclass
class BlueskyConfig:
    enabled: bool = False
    handle: str = ""
    password: str = ""


@dataclass
class MastodonConfig:
    enabled: bool = False
    instance_url: str = "https://mastodon.social"
    access_token: str = ""


@dataclass
class PlatformsConfig:
    twitter: TwitterConfig | None = None
    bluesky: BlueskyConfig | None = None
    mastodon: MastodonConfig | None = None


@dataclass
class LoggingConfig:
    level: str = "INFO"


@dataclass
class AppConfig:
    trello: TrelloConfig
    schedule: ScheduleConfig
    platforms: PlatformsConfig
    logging: LoggingConfig


def _build_dataclass(cls, data: dict):
    """Build a dataclass from a dict, ignoring unknown keys."""
    valid = {f.name for f in cls.__dataclass_fields__.values()}
    return cls(**{k: v for k, v in data.items() if k in valid})


def load_config(path: Path) -> AppConfig:
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"invalid TOML: {e}")

    if "trello" not in raw:
        raise ConfigError("missing [trello] section")

    trello = _build_dataclass(TrelloConfig, raw["trello"])
    if not trello.api_key or not trello.api_token or not trello.board_id:
        raise ConfigError("trello.api_key, trello.api_token, and trello.board_id are required")

    schedule = _build_dataclass(ScheduleConfig, raw.get("schedule", {}))

    platforms_raw = raw.get("platforms", {})
    platforms = PlatformsConfig(
        twitter=_build_dataclass(TwitterConfig, platforms_raw["twitter"]) if "twitter" in platforms_raw else None,
        bluesky=_build_dataclass(BlueskyConfig, platforms_raw["bluesky"]) if "bluesky" in platforms_raw else None,
        mastodon=_build_dataclass(MastodonConfig, platforms_raw["mastodon"]) if "mastodon" in platforms_raw else None,
    )

    logging_cfg = _build_dataclass(LoggingConfig, raw.get("logging", {}))

    return AppConfig(trello=trello, schedule=schedule, platforms=platforms, logging=logging_cfg)
