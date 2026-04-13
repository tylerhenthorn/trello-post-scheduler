from unittest.mock import MagicMock, patch

from trello_post_scheduler.config import AppConfig, TrelloConfig, ScheduleConfig, PlatformsConfig, LoggingConfig
from trello_post_scheduler.poster import PostResult
from trello_post_scheduler.scheduler import build_scheduler, post_job
from trello_post_scheduler.trello import CardPost


def _mock_trello(cards=None, post=None):
    trello = MagicMock()
    trello.get_cards.return_value = cards or []
    trello.card_to_post.return_value = post or CardPost(text="hello")
    return trello


def _mock_poster(platform, success=True):
    poster = MagicMock()
    poster.post.return_value = PostResult(
        platform=platform, success=success,
        post_id="123" if success else None,
        error=None if success else "fail",
    )
    return poster


@patch("trello_post_scheduler.scheduler.post_to_all_platforms")
def test_all_succeed_deletes_card(mock_post_all):
    card = MagicMock()
    card.name = "Test"
    trello = _mock_trello(cards=[card])
    posters = [_mock_poster("twitter"), _mock_poster("bluesky")]
    mock_post_all.return_value = [r.post.return_value for r in posters]

    post_job(trello, posters)

    trello.delete_card.assert_called_once_with(card)


@patch("trello_post_scheduler.scheduler.post_to_all_platforms")
def test_partial_success_deletes_card(mock_post_all):
    card = MagicMock()
    card.name = "Test"
    trello = _mock_trello(cards=[card])
    ok = _mock_poster("twitter", success=True)
    fail = _mock_poster("bluesky", success=False)
    mock_post_all.return_value = [ok.post.return_value, fail.post.return_value]

    post_job(trello, [ok, fail])

    trello.delete_card.assert_called_once_with(card)


@patch("trello_post_scheduler.scheduler.post_to_all_platforms")
def test_all_fail_keeps_card(mock_post_all):
    card = MagicMock()
    card.name = "Test"
    trello = _mock_trello(cards=[card])
    fail1 = _mock_poster("twitter", success=False)
    fail2 = _mock_poster("bluesky", success=False)
    mock_post_all.return_value = [fail1.post.return_value, fail2.post.return_value]

    post_job(trello, [fail1, fail2])

    trello.delete_card.assert_not_called()


def test_no_cards_is_noop():
    trello = _mock_trello(cards=[])
    posters = [_mock_poster("twitter")]

    post_job(trello, posters)

    trello.card_to_post.assert_not_called()
    trello.delete_card.assert_not_called()


@patch("trello_post_scheduler.scheduler.TrelloClient")
def test_build_scheduler_sets_jitter_on_trigger(mock_trello_cls):
    cfg = AppConfig(
        trello=TrelloConfig(api_key="k", api_token="t", board_id="b"),
        schedule=ScheduleConfig(post_times=["12:00"], post_time_randomization=300),
        platforms=PlatformsConfig(),
        logging=LoggingConfig(),
    )
    scheduler = build_scheduler(cfg, [])
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].trigger.jitter == 600


@patch("trello_post_scheduler.scheduler.TrelloClient")
def test_build_scheduler_no_jitter_when_zero(mock_trello_cls):
    cfg = AppConfig(
        trello=TrelloConfig(api_key="k", api_token="t", board_id="b"),
        schedule=ScheduleConfig(post_times=["12:00"], post_time_randomization=0),
        platforms=PlatformsConfig(),
        logging=LoggingConfig(),
    )
    scheduler = build_scheduler(cfg, [])
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].trigger.jitter is None
