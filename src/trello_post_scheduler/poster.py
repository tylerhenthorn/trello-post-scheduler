from __future__ import annotations

import logging
from dataclasses import dataclass

from trello_post_scheduler.config import AppConfig
from trello_post_scheduler.trello import CardPost

log = logging.getLogger(__name__)


@dataclass
class PostResult:
    platform: str
    success: bool
    post_id: str | None = None
    error: str | None = None


_PLATFORM_ATTRS = ("twitter", "bluesky", "mastodon")


def enabled_platform_names(cfg: AppConfig) -> list[str]:
    """Return names of enabled platforms without instantiating clients."""
    return [
        name for name in _PLATFORM_ATTRS
        if (p := getattr(cfg.platforms, name)) and p.enabled
    ]


def build_platforms(cfg: AppConfig) -> list:
    """Instantiate enabled platform poster clients."""
    from trello_post_scheduler.platforms.twitter import TwitterPoster
    from trello_post_scheduler.platforms.bluesky import BlueskyPoster
    from trello_post_scheduler.platforms.mastodon import MastodonPoster

    posters = []
    if cfg.platforms.twitter and cfg.platforms.twitter.enabled:
        posters.append(TwitterPoster(cfg.platforms.twitter))
    if cfg.platforms.bluesky and cfg.platforms.bluesky.enabled:
        posters.append(BlueskyPoster(cfg.platforms.bluesky))
    if cfg.platforms.mastodon and cfg.platforms.mastodon.enabled:
        posters.append(MastodonPoster(cfg.platforms.mastodon))
    return posters


def post_to_all_platforms(post: CardPost, posters: list) -> list[PostResult]:
    """Post to all enabled platforms. Failures on one don't block others."""
    results = []
    for poster in posters:
        result = poster.post(post)
        results.append(result)
    return results
