from unittest.mock import MagicMock, patch

from trello_post_scheduler.config import BlueskyConfig
from trello_post_scheduler.platforms.bluesky import BlueskyPoster, MAX_CHARS
from trello_post_scheduler.trello import CardPost


def _cfg():
    return BlueskyConfig(handle="test.bsky.social", password="pass")


@patch("trello_post_scheduler.platforms.bluesky.Client")
def test_post_success(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.send_post.return_value = MagicMock(uri="at://did:plc:xxx/app.bsky.feed.post/abc")

    poster = BlueskyPoster(_cfg())
    result = poster.post(CardPost(text="hello bluesky"))

    assert result.success is True
    assert "at://" in result.post_id
    mock_client.send_post.assert_called_once_with(text="hello bluesky")


@patch("trello_post_scheduler.platforms.bluesky.Client")
def test_post_truncates(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.send_post.return_value = MagicMock(uri="at://x")

    poster = BlueskyPoster(_cfg())
    poster.post(CardPost(text="x" * 500))

    call_text = mock_client.send_post.call_args[1]["text"]
    assert len(call_text) == MAX_CHARS


@patch("trello_post_scheduler.platforms.bluesky.Client")
def test_post_failure(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.send_post.side_effect = Exception("auth failed")

    poster = BlueskyPoster(_cfg())
    result = poster.post(CardPost(text="hello"))

    assert result.success is False
    assert "auth failed" in result.error


@patch("trello_post_scheduler.platforms.bluesky.Client")
def test_post_with_image(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.send_image.return_value = MagicMock(uri="at://did:plc:xxx/app.bsky.feed.post/img1")

    poster = BlueskyPoster(_cfg())
    post = CardPost(text="hi", image_bytes=b"img", image_mime="image/png", alt_text="alt desc")
    result = poster.post(post)

    assert result.success is True
    mock_client.send_image.assert_called_once_with(text="hi", image=b"img", image_alt="alt desc")
    mock_client.send_post.assert_not_called()
