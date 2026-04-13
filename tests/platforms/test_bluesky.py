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


@patch("trello_post_scheduler.platforms.bluesky.Image")
@patch("trello_post_scheduler.platforms.bluesky.models")
@patch("trello_post_scheduler.platforms.bluesky.Client")
def test_post_with_image(mock_client_cls, mock_models, mock_image_cls):
    mock_client = mock_client_cls.return_value
    mock_blob = MagicMock()
    mock_client.upload_blob.return_value = MagicMock(blob=mock_blob)
    mock_client.send_post.return_value = MagicMock(uri="at://did:plc:xxx/app.bsky.feed.post/img1")

    mock_img = MagicMock()
    mock_img.size = (800, 1200)
    mock_image_cls.open.return_value = mock_img

    poster = BlueskyPoster(_cfg())
    post = CardPost(text="hi", image_bytes=b"img", image_mime="image/png", alt_text="alt desc")
    result = poster.post(post)

    assert result.success is True
    mock_client.upload_blob.assert_called_once_with(b"img")
    mock_client.send_image.assert_not_called()

    # Aspect ratio must carry the actual image dimensions
    mock_models.AppBskyEmbedImages.AspectRatio.assert_called_once_with(width=800, height=1200)

    # send_post must be called with text and an embed (not send_image)
    mock_client.send_post.assert_called_once()
    call_kwargs = mock_client.send_post.call_args[1]
    assert call_kwargs["text"] == "hi"
    assert "embed" in call_kwargs
