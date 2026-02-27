from unittest.mock import MagicMock, patch

from trello_post_scheduler.config import MastodonConfig
from trello_post_scheduler.platforms.mastodon import MastodonPoster, MAX_CHARS
from trello_post_scheduler.trello import CardPost


def _cfg():
    return MastodonConfig(instance_url="https://mastodon.social", access_token="tok")


@patch("trello_post_scheduler.platforms.mastodon.Mastodon")
def test_post_success(mock_masto_cls):
    mock_client = mock_masto_cls.return_value
    mock_client.status_post.return_value = {"id": "masto123"}

    poster = MastodonPoster(_cfg())
    result = poster.post(CardPost(text="hello mastodon"))

    assert result.success is True
    assert result.post_id == "masto123"
    mock_client.status_post.assert_called_once_with("hello mastodon", media_ids=None)


@patch("trello_post_scheduler.platforms.mastodon.Mastodon")
def test_post_truncates(mock_masto_cls):
    mock_client = mock_masto_cls.return_value
    mock_client.status_post.return_value = {"id": "m1"}

    poster = MastodonPoster(_cfg())
    poster.post(CardPost(text="x" * 600))

    call_text = mock_client.status_post.call_args[0][0]
    assert len(call_text) == MAX_CHARS


@patch("trello_post_scheduler.platforms.mastodon.Mastodon")
def test_post_failure(mock_masto_cls):
    from mastodon import MastodonError
    mock_client = mock_masto_cls.return_value
    mock_client.status_post.side_effect = MastodonError("server error")

    poster = MastodonPoster(_cfg())
    result = poster.post(CardPost(text="hello"))

    assert result.success is False
    assert "server error" in result.error


@patch("trello_post_scheduler.platforms.mastodon.Mastodon")
def test_post_with_image(mock_masto_cls):
    mock_client = mock_masto_cls.return_value
    mock_client.media_post.return_value = {"id": "media1"}
    mock_client.status_post.return_value = {"id": "masto456"}

    poster = MastodonPoster(_cfg())
    post = CardPost(text="hi", image_bytes=b"img", image_mime="image/jpeg", alt_text="alt desc")
    result = poster.post(post)

    assert result.success is True
    mock_client.media_post.assert_called_once_with(
        media_file=b"img", mime_type="image/jpeg", description="alt desc",
    )
    mock_client.status_post.assert_called_once_with("hi", media_ids=["media1"])
