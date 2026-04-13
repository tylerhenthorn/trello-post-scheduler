from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from trello_post_scheduler.config import AppConfig
from trello_post_scheduler.poster import post_to_all_platforms
from trello_post_scheduler.trello import TrelloClient

log = logging.getLogger(__name__)


def post_job(trello: TrelloClient, posters: list) -> None:
    """Fetch one card from Trello and post to all platforms."""
    try:
        cards = trello.get_cards(limit=1)
    except Exception:
        log.exception("failed to fetch cards from trello")
        return

    if not cards:
        log.info("no cards available to post")
        return

    card = cards[0]
    post = trello.card_to_post(card)
    log.info("posting card: %s", card.name)

    results = post_to_all_platforms(post, posters)

    failed = [r.platform for r in results if not r.success]
    if failed:
        log.warning("card %s failed on: %s", card.name, ", ".join(failed))

    if any(r.success for r in results):
        try:
            trello.delete_card(card)
        except Exception:
            log.exception("failed to delete card")


def build_scheduler(cfg: AppConfig, posters: list) -> BlockingScheduler:
    scheduler = BlockingScheduler()
    trello = TrelloClient(cfg.trello)

    r = cfg.schedule.post_time_randomization

    for time_str in cfg.schedule.post_times:
        hour, minute = time_str.split(":")
        base = datetime(2000, 1, 1, int(hour), int(minute))
        shifted = base - timedelta(seconds=r)

        trigger_kwargs = dict(
            hour=shifted.hour, minute=shifted.minute, second=shifted.second,
        )
        if r > 0:
            trigger_kwargs["jitter"] = r * 2

        scheduler.add_job(
            func=post_job,
            trigger=CronTrigger(**trigger_kwargs),
            args=[trello, posters],
            id=f"post_{time_str}",
            max_instances=1,
            coalesce=True,
        )
        log.info("scheduled post job at %s (randomization ±%ds)", time_str, r)

    return scheduler
