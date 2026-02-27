from unittest.mock import MagicMock

from trello_post_scheduler.poster import PostResult, post_to_all_platforms
from trello_post_scheduler.trello import CardPost


def _mock_poster(platform: str, success: bool = True):
    poster = MagicMock()
    poster.platform = platform
    poster.post.return_value = PostResult(
        platform=platform,
        success=success,
        post_id="123" if success else None,
        error=None if success else "fail",
    )
    return poster


def test_post_to_all_success():
    posters = [_mock_poster("twitter"), _mock_poster("bluesky")]
    post = CardPost(text="hello")
    results = post_to_all_platforms(post, posters)
    assert len(results) == 2
    assert all(r.success for r in results)


def test_post_partial_failure():
    posters = [_mock_poster("twitter", True), _mock_poster("bluesky", False)]
    post = CardPost(text="hello")
    results = post_to_all_platforms(post, posters)
    assert results[0].success is True
    assert results[1].success is False


def test_post_empty_posters():
    post = CardPost(text="hello")
    results = post_to_all_platforms(post, [])
    assert results == []
