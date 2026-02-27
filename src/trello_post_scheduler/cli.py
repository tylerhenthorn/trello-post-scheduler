from __future__ import annotations

import argparse
import logging
import sys
from importlib.metadata import version
from pathlib import Path

from trello_post_scheduler.config import load_config
from trello_post_scheduler.exceptions import ConfigError
from trello_post_scheduler.poster import build_platforms, enabled_platform_names
from trello_post_scheduler.scheduler import build_scheduler, post_job
from trello_post_scheduler.trello import TrelloClient


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="trello-post-scheduler",
        description="Post Trello cards to Twitter/X, Bluesky, and Mastodon on a schedule",
    )
    parser.add_argument(
        "--config",
        default=Path.home() / ".config" / "trello-post-scheduler" / "config.toml",
        type=Path,
        help="path to config.toml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch cards and log what would be posted without actually posting",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="post one card immediately then exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('trello-post-scheduler')}",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    setup_logging(args.log_level or cfg.logging.level)
    log = logging.getLogger(__name__)

    if args.dry_run and args.once:
        # Dry run: fetch one card and show what would be posted
        trello = TrelloClient(cfg.trello)
        cards = trello.get_cards(limit=1)
        if not cards:
            log.info("no cards available")
            return
        card = cards[0]
        post = trello.card_to_post(card)
        log.info("[dry-run] would post card: %s", card.name)
        log.info("[dry-run] text: %s", post.text)
        if post.image_bytes:
            log.info("[dry-run] image: %s (%d bytes)", post.image_mime, len(post.image_bytes))
            log.info("[dry-run] alt text: %s", post.alt_text)
        log.info("[dry-run] platforms: %s", ", ".join(enabled_platform_names(cfg)))
        return

    posters = build_platforms(cfg)
    if not posters:
        log.error("no platforms enabled")
        sys.exit(1)

    log.info("enabled platforms: %s", ", ".join(p.platform for p in posters))

    if args.once:
        trello = TrelloClient(cfg.trello)
        post_job(trello, posters)
        return

    # Run scheduler daemon
    log.info("starting scheduler")
    scheduler = build_scheduler(cfg, posters)
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("shutting down")
