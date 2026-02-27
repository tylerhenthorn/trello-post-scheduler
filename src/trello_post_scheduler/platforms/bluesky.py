from __future__ import annotations

import logging

from atproto import Client

from trello_post_scheduler.config import BlueskyConfig
from trello_post_scheduler.poster import PostResult
from trello_post_scheduler.trello import CardPost

log = logging.getLogger(__name__)

MAX_CHARS = 300


class BlueskyPoster:
    platform = "bluesky"

    def __init__(self, cfg: BlueskyConfig):
        self.client = Client()
        self.client.login(cfg.handle, cfg.password)

    def post(self, post: CardPost) -> PostResult:
        trimmed = post.text[:MAX_CHARS]
        try:
            if post.image_bytes is not None:
                resp = self.client.send_image(
                    text=trimmed,
                    image=post.image_bytes,
                    image_alt=post.alt_text or "",
                )
            else:
                resp = self.client.send_post(text=trimmed)
            log.info("posted to bluesky: %s", resp.uri)
            return PostResult(platform="bluesky", success=True, post_id=resp.uri)
        except Exception as e:
            log.error("bluesky post failed: %s", e)
            return PostResult(platform="bluesky", success=False, error=str(e))
