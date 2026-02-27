from __future__ import annotations

import logging

from mastodon import Mastodon, MastodonError

from trello_post_scheduler.config import MastodonConfig
from trello_post_scheduler.poster import PostResult
from trello_post_scheduler.trello import CardPost

log = logging.getLogger(__name__)

MAX_CHARS = 500


class MastodonPoster:
    platform = "mastodon"

    def __init__(self, cfg: MastodonConfig):
        self.client = Mastodon(
            access_token=cfg.access_token,
            api_base_url=cfg.instance_url,
        )

    def post(self, post: CardPost) -> PostResult:
        trimmed = post.text[:MAX_CHARS]
        try:
            media_ids = None
            if post.image_bytes is not None:
                media = self.client.media_post(
                    media_file=post.image_bytes,
                    mime_type=post.image_mime,
                    description=post.alt_text or "",
                )
                media_ids = [media["id"]]

            resp = self.client.status_post(trimmed, media_ids=media_ids)
            post_id = str(resp["id"])
            log.info("posted to mastodon: %s", post_id)
            return PostResult(platform="mastodon", success=True, post_id=post_id)
        except MastodonError as e:
            log.error("mastodon post failed: %s", e)
            return PostResult(platform="mastodon", success=False, error=str(e))
