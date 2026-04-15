from __future__ import annotations

import io
import logging

from PIL import Image
from atproto import Client, models

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
                img = Image.open(io.BytesIO(post.image_bytes))
                width, height = img.size
                upload = self.client.upload_blob(post.image_bytes)
                embed = models.AppBskyEmbedImages.Main(
                    images=[
                        models.AppBskyEmbedImages.Image(
                            alt=post.alt_text or "",
                            image=upload.blob,
                            aspect_ratio=models.AppBskyEmbedDefs.AspectRatio(
                                width=width,
                                height=height,
                            ),
                        )
                    ]
                )
                resp = self.client.send_post(text=trimmed, embed=embed)
            else:
                resp = self.client.send_post(text=trimmed)
            log.info("posted to bluesky: %s", resp.uri)
            return PostResult(platform="bluesky", success=True, post_id=resp.uri)
        except Exception as e:
            log.error("bluesky post failed: %s", e)
            return PostResult(platform="bluesky", success=False, error=str(e))
