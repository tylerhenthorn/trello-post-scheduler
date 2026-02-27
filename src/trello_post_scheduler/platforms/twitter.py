from __future__ import annotations

import logging
import mimetypes
import tempfile
from pathlib import Path

import tweepy

from trello_post_scheduler.config import TwitterConfig
from trello_post_scheduler.poster import PostResult
from trello_post_scheduler.trello import CardPost

log = logging.getLogger(__name__)

MAX_CHARS = 280


class TwitterPoster:
    platform = "twitter"

    def __init__(self, cfg: TwitterConfig):
        self.client = tweepy.Client(
            bearer_token=cfg.bearer_token,
            consumer_key=cfg.api_key,
            consumer_secret=cfg.api_secret,
            access_token=cfg.access_token,
            access_token_secret=cfg.access_secret,
        )
        self.api = tweepy.API(tweepy.OAuth1UserHandler(
            cfg.api_key, cfg.api_secret,
            cfg.access_token, cfg.access_secret,
        ))

    def post(self, post: CardPost) -> PostResult:
        trimmed = post.text[:MAX_CHARS]
        tmp_path = None
        try:
            media_ids = None
            if post.image_bytes is not None:
                ext = mimetypes.guess_extension(post.image_mime) or ".jpg"
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                    f.write(post.image_bytes)
                    tmp_path = f.name
                media = self.api.media_upload(tmp_path)
                media_ids = [media.media_id]

            resp = self.client.create_tweet(text=trimmed, media_ids=media_ids)
            post_id = str(resp.data["id"])
            log.info("posted to twitter: %s", post_id)
            return PostResult(platform="twitter", success=True, post_id=post_id)
        except tweepy.TweepyException as e:
            log.error("twitter post failed: %s", e)
            return PostResult(platform="twitter", success=False, error=str(e))
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
